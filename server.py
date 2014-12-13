#!/usr/bin/env python3

import socket
import os
import rencode
import threading
import stat
import multiprocessing
import time
import struct
import session
import traceback
import subprocess

_here = os.path.dirname(__file__)
SOCKET_NAME = os.path.join(_here, ".socket")
PID_FILE = os.path.join(_here, "local_server.pid")

def _read_socket(socket):
    length, = struct.unpack("I", socket.recv(4))
    return rencode.loads(socket.recv(length), decode_utf8=True)

def _write_socket(socket, data):
    encoded = rencode.dumps(data)
    socket.sendall(struct.pack("I", len(encoded)))
    socket.sendall(encoded)

class _Server():
    def __init__(self):
        self.session = session.Session()

    def start(self):
        oldmask = os.umask(0o77)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(SOCKET_NAME)
        self._sock.listen(1)
        os.umask(oldmask)

        while True:
            con, addr = self._sock.accept()
            thread = threading.Thread(target=self._handle_connection, args=(con, addr))
            thread.daemon = True
            thread.start()

    def _handle_connection(self, connection, address):
        try:
            while True:
                channel, args, kwargs = _read_socket(connection)
                try:
                    ret = getattr(self, channel)(*args, **kwargs)
                    result = True, ret
                except Exception as e:
                    result = False, str(e)
                    traceback.print_exc()
                _write_socket(connection, result)
        finally:
            connection.close()

    def is_logged_in(self):
        return self.session.logged_in

    def log_in(self, password):
        return self.session.log_in(password)

    def list_password_names(self):
        return self.session.list_password_names()

    def add_password(self, name, password):
        self.session.add_password(name, password)

    def get_password(self, name):
        return self.session.get_password(name)

    def stop_server(self):
        # clean shutdown, just stop accepting connections and exit when done
        self._sock.shutdown(socket.SHUT_RDWR)

def _run():
    our_pid = os.getpid()
    tmp_file = PID_FILE + "."
    with open(tmp_file, "w") as f:
        f.write(str(our_pid))
    new_pid = _get_pid()
    if new_pid != our_pid and new_pid is not None:
        try:
            os.kill(new_pid, 0)
            os.remove(tmp_file)
            return
        except OSError:
            pass
    os.rename(tmp_file, PID_FILE)
    _Server().start()

def _start_if_missing():
    if _is_running():
        return

    try:
        os.remove(SOCKET_NAME)
    except OSError:
        pass
    #proc = multiprocessing.Process(target=_intern)
    #proc.start()
    subprocess.Popen(os.path.abspath(__file__))

def _is_running():
    pid = _get_pid()
    if pid is not None:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    else:
        return False

def _get_pid():
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read())
    except IOError:
        return None

if __name__ == '__main__':
    _run()
