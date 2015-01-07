#!/usr/bin/env python3

import os
import json
from Crypto.Cipher import AES
import scrypt
import gzip
import traceback
import struct

class StorageProvider(object):
    def __init__(self, input_type):
        self.input_type = input_type

    def load(self):
        return None

    def store(self, obj):
        pass

    @property
    def persistent(self):
        return True

class StorageTransformer(StorageProvider):
    def __init__(self, input_type, output_type, nxt):
        super(StorageTransformer, self).__init__(input_type)
        self.output_type = output_type
        self._nxt = nxt

        if self.output_type != nxt.input_type:
            raise ValueError("Output type %s is incompatible with following input type %s" % (self.output_type, nxt.input_type))

    def load(self):
        return self._nxt.load()

    def store(self, obj):
        return self._nxt.store(obj)

    @property
    def persistent(self):
        return self._nxt.persistent

class StringEncoder(StorageTransformer):
    def __init__(self, nxt):
        super(StringEncoder, self).__init__(str, bytes, nxt)

    def load(self):
        return super(StringEncoder, self).load().decode("utf-8")

    def store(self, obj):
        super(StringEncoder, self).store(obj.encode("utf-8"))

class JsonStorageTransformer(StorageTransformer):
    def __init__(self, nxt):
        super(JsonStorageTransformer, self).__init__(dict, str, nxt)

    def load(self):
        return json.loads(super(JsonStorageTransformer, self).load())

    def store(self, obj):
        super(JsonStorageTransformer, self).store(json.dumps(obj))

class ScryptAESStorageTransformer(StorageTransformer):
    """
    All integers are big-endian.

    Blob format:
    00-16: salt
    16-20: exponent of N scrypt parameter
    20-24: r scrypt parameter
    24-28: p scrypt parameter
    28-44: iv
    44-..: encrypted data block

    encrypted block format:
    00-04: data length (uint32)
    04-..: data
    encrypted block is padded with arbitrary bytes to multiples of 16
    """

    def __init__(self, nxt, password):
        super(ScryptAESStorageTransformer, self).__init__(bytes, bytes, nxt)
        self.password = password.encode("utf-8")

        self.keylen = 32
        self.Np = 14
        self.r = 8
        self.p = 1

    def load(self):
        data = super(ScryptAESStorageTransformer, self).load()
        salt = data[0:16]
        Np = struct.unpack(">I", data[16:20])[0]
        r = struct.unpack(">I", data[20:24])[0]
        p = struct.unpack(">I", data[24:28])[0]
        iv = data[28:44]
        enc = data[44:]
        key = scrypt.hash(self.password, salt, 1 << Np, r, p, buflen=self.keylen)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = cipher.decrypt(enc)
        block_len = struct.unpack(">I", dec[:4])[0]
        return dec[4:4 + block_len]

    def store(self, obj):
        salt = os.urandom(16)
        iv = os.urandom(16)
        Np = struct.pack(">I", self.Np)
        r = struct.pack(">I", self.r)
        p = struct.pack(">I", self.p)
        key = scrypt.hash(self.password, salt, 1 << self.Np, self.r, self.p, buflen=self.keylen)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        obj = struct.pack(">I", len(obj)) + obj
        if (len(obj) % 16) != 0:
            obj += (16 - (len(obj) % 16)) * b"\000"
        enc = cipher.encrypt(obj)
        data = salt + Np + r + p + iv + enc
        return super(ScryptAESStorageTransformer, self).store(data)

class FileStorageProvider(StorageProvider):
    def __init__(self, filename):
        super(FileStorageProvider, self).__init__(bytes)
        self.filename = os.path.join(os.path.dirname(__file__), filename)

    def load(self):
        with open(self.filename, "r") as f:
            return f.buffer.read()

    def store(self, obj):
        with open(self.filename, "w") as f:
            f.buffer.write(obj)

class GzipTransformer(StorageTransformer):
    def __init__(self, nxt):
        super(GzipTransformer, self).__init__(bytes, bytes, nxt)

    def load(self):
        return gzip.decompress(super(GzipTransformer, self).load())

    def store(self, obj):
        super(GzipTransformer, self).store(gzip.compress(obj))

class LocalCopyStorageProvider(StorageProvider):
    def __init__(self, upstream, local):
        cl = upstream.input_type
        if local.input_type != cl:
            raise ValueError("Incompatible provider types %s vs %s" % (cl, local.input_type))
        super(LocalCopyStorageProvider, self).__init__(cl)
        self.upstream = upstream
        self.local = local
        self.remote_success = True

    def load(self):
        try:
            val = self.upstream.load()
            self.local.store(val)
            self.remote_success = True
            return val
        except:
            traceback.print_exc()
            self.remote_success = False
            return self.local.load()

    def store(self, obj):
        if not self.remote_success:
            raise Exception("Remote load was not successful, not saving!")
        self.local.store(obj)
        self.upstream.store(obj)

    @property
    def persistent(self):
        return self.remote_success and self.upstream.persistent
