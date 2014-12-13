#!/usr/bin/env python3

from storage import *
import storage_server

def build_storage_pipeline(password):
    remote = storage_server.RemoteStorageProvider("http://pw.yawk.at", password)
    local = FileStorageProvider("db")

    pipe = LocalCopyStorageProvider(remote, local)
    pipe = ScryptStorageTransformer(pipe, password)
    pipe = GzipTransformer(pipe)
    pipe = StringEncoder(pipe)
    pipe = JsonStorageTransformer(pipe)
    return pipe
