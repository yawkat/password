#!/usr/bin/env python3

from storage import *
import storage_server

def build_storage_pipeline(password):
    remote = storage_server.RemoteStorageProvider("http://pw.yawk.at")
    local = FileStorageProvider("db")

    pipe = LocalCopyStorageProvider(remote, local)
    pipe = ScryptAESStorageTransformer(pipe, password)
    pipe = storage_server.KeyExchange(pipe, remote)
    pipe = GzipTransformer(pipe)
    pipe = StringEncoder(pipe)
    pipe = JsonStorageTransformer(pipe)
    return pipe
