#!/usr/bin/env python3

import storage
import http.server
import struct
import Crypto.PublicKey.RSA
import rsa
import os
import scrypt
import random
import io
import urllib.request
import traceback

HASH = "SHA-512"

def _readi(stream):
    return struct.unpack(">I", stream.read(4))[0]

def _readblock(stream):
    block_length = _readi(stream)
    return stream.read(block_length)

def _writei(stream, value):
    stream.write(struct.pack(">I", value))

def _writeblock(stream, block):
    _writei(stream, len(block))
    stream.write(block)

class KeyExchange(storage.StorageTransformer):
    def __init__(self, nxt, storage_provider):
        super(KeyExchange, self).__init__(bytes, bytes, nxt)
        self.storage_provider = storage_provider

    def load(self):
        data = super(KeyExchange, self).load()
        f = io.BytesIO(data)
        self.storage_provider.private_key = rsa.PrivateKey.load_pkcs1(_readblock(f), format="DER")
        self.storage_provider.public_key = rsa.PublicKey.load_pkcs1(_readblock(f), format="DER")
        return _readblock(f)

    def store(self, obj):
        if self.storage_provider.private_key is None:
            self.storage_provider.public_key, self.storage_provider.private_key = rsa.newkeys(2048)

        f = io.BytesIO()
        _writeblock(f, self.storage_provider.private_key.save_pkcs1(format="DER"))
        _writeblock(f, self.storage_provider.public_key.save_pkcs1(format="DER"))
        _writeblock(f, obj)
        super(KeyExchange, self).store(f.getvalue())

class RemoteStorageProvider(storage.StorageProvider):
    def __init__(self, address):
        super(RemoteStorageProvider, self).__init__(bytes)
        self.address = address
        self.private_key = None
        self.public_key = None

    def load(self):
        return urllib.request.urlopen(self.address).read()

    def store(self, obj):
        f = io.BytesIO()
        _writeblock(f, self.public_key.save_pkcs1(format="DER"))
        _writeblock(f, rsa.sign(obj, self.private_key, HASH))
        _writeblock(f, obj)
        request = urllib.request.Request(self.address, data=f.getvalue(), method="PUT")
        urllib.request.urlopen(request)

def start_server(address, port, data_file):
    if os.path.isfile(data_file):
        with open(data_file) as f:
            public_key = rsa.PublicKey.load_pkcs1(_readblock(f.buffer))
            data = _readblock(f.buffer)
    else:
        public_key = None
        data = None

    def _save():
        with open(data_file, "w") as f:
            _writeblock(f.buffer, public_key.save_pkcs1())
            _writeblock(f.buffer, data)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_PUT(self):
            try:
                nonlocal public_key, data

                r_public_key = rsa.PublicKey.load_pkcs1(_readblock(self.rfile), format="DER")
                r_signature = _readblock(self.rfile)
                r_message = _readblock(self.rfile)

                if public_key is not None and public_key != r_public_key:
                    self.send_error(403)
                    return

                try:
                    rsa.verify(r_message, r_signature, r_public_key)
                except rsa.pkcs1.VerificationError:
                    self.send_error(403)
                    return

                public_key = r_public_key
                data = r_message
                _save()

                self.send_response(200)
                self.end_headers()
            except:
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()

        def do_GET(self):
            if data is None:
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()

            self.wfile.write(data)
    server = http.server.HTTPServer((address, port), Handler)
    server.serve_forever()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    default_data_file = os.path.join(os.path.dirname(__file__), "db")
    parser.add_argument("-p", "--port", type=int, dest="port", required=True)
    parser.add_argument("-f", "--file", default=default_data_file, dest="data_file")
    parser.add_argument("--address", default="0.0.0.0", dest="address")
    args = parser.parse_args()

    start_server(args.address, args.port, args.data_file)
