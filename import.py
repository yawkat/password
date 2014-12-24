#!/usr/bin/env python3

import session
import getpass
import json
import sys

password = getpass.getpass("Password: ")

sess = session.Session()
sess.log_in(password, load=False)
with open(sys.argv[1]) as f:
    sess.data = json.load(f)
sess.save()
