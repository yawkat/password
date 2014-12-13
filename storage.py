#!/usr/bin/env python3

import os
import json
from Crypto.Cipher import AES
import scrypt
import gzip
import traceback

class StorageProvider(object):
    def __init__(self, input_type):
        self.input_type = input_type

    def load(self):
        return None

    def store(self, obj):
        pass

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

class ScryptStorageTransformer(StorageTransformer):
    def __init__(self, nxt, password):
        super(ScryptStorageTransformer, self).__init__(bytes, bytes, nxt)
        self.password = password

    def load(self):
        enc = super(ScryptStorageTransformer, self).load()
        return scrypt.decrypt(enc, self.password, encoding=None)

    def store(self, obj):
        enc = scrypt.encrypt(obj, self.password, maxtime=0.2)
        return super(ScryptStorageTransformer, self).store(enc)

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
