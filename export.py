#!/usr/bin/env python3

import session
import getpass
import json

password = getpass.getpass("Password: ")

sess = session.Session()
sess.log_in(password)

print(json.dumps(sess.data))
