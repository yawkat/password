#!/usr/bin/env python3

import server
import threading
import os
import socket
import time

class Client():
    def __init__(self):
        self._lock = threading.Lock()
        self._socket = None

    def __getattr__(self, name):
        if name in dir(server._Server):
            def fun(*args, **kwargs):
                return self._query(name, *args, **kwargs)
            return fun

    def _query(self, channel, *args, **kwargs):
        with self._lock:
            if self._socket is None:
                server._start_if_missing()
                while not os.path.exists(server.SOCKET_NAME):
                    time.sleep(0.1)
                self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._socket.connect(server.SOCKET_NAME)
            server._write_socket(self._socket, (channel, args, kwargs))
            success, result = server._read_socket(self._socket)
            if success:
                return result
            else:
                raise OSError(result)
