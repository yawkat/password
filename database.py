#!/usr/bin/env python3

from storage import *

import threading

class Login:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    @property
    def password(self):
        return self.data.split("\n")[0]

class Database:
    def __init__(self, storage_provider):
        self._data = { "logins": [] }
        self._dirty = True
        self._storage_provider = storage_provider
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            self.data = self._storage_provider.load()
            self._dirty = False

    def save(self):
        if not self._dirty:
            return
        with self._lock:
            if not self._dirty:
                return
            self._storage_provider.store(self.data)
            self._dirty = False

    @property
    def logins(self):
        for e in self._data["logins"]:
            yield Login(e["name"], e["data"])

    def add_login(self, login):
        with self._lock:
            self._data["logins"].append({ "name": login.name, "data": login.data })
