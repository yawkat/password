#!/usr/bin/env python3

import config
import uuid

class Session:
    def __init__(self):
        self.pipeline = None
        self.data = None

    def init_empty(self):
        self.data = { 
            "version": 0,
            "passwords": {} 
        }

    @property
    def logged_in(self):
        return self.data is not None

    def log_in(self, password, load=True):
        self.pipeline = config.build_storage_pipeline(password)
        if load:
            self.data = self.pipeline.load()

    def save(self):
        self.pipeline.store(self.data)

    def list_password_names(self):
        return tuple(self.data["passwords"].keys())

    def add_password(self, name, password, save=True):
        self.data["passwords"][name] = { "password": password }
        if save:
            self.save()

    def get_password(self, name):
        return self.data["passwords"][name]["password"]
