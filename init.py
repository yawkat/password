#!/usr/bin/env python3

import session
import sys
import argparse
import getpass
import xmltodict
import collections

parser = argparse.ArgumentParser()

parser.add_argument("-p", "--password", default="-", dest="password")
parser.add_argument("--keepass2", default=[], nargs="*")

args = parser.parse_args()

if args.password == "-":
    password = getpass.getpass("Password: ")
else:
    password = args.password

sess = session.Session()
sess.log_in(password, load=False)
sess.init_empty()

def add(name, password):
    print("Adding %s..." % name)
    if name in sess.list_password_names():
        print("Duplicate name %s, merging" % name)
        password = sess.get_password(name) + "\n###\n" + password
    sess.add_password(name, password, save=False)

for keepass2file in args.keepass2:
    with open(keepass2file) as f:
        doc = xmltodict.parse(f.read())
    root = doc["KeePassFile"]["Root"]

    def get_list(element, k):
        if k not in element:
            return tuple()
        v = element[k]
        if type(v) == list or type(v) == tuple:
            return v
        else:
            return (v,)

    def enter_group(path, element, first=True):
        for entry in get_list(element, "Entry"):
            for st in get_list(entry, "String"):
                v = st["Value"]
                if type(v) == collections.OrderedDict:
                    v = v.get("#text", None)
                if st["Key"] == "Title":
                    if v is None:
                        k = None
                    else:
                        k = path + (v,)
                elif st["Key"] == "Password":
                    print(v)
                    password = v
                elif st["Key"] == "Notes":
                    notes = v
                elif st["Key"] == "URL":
                    url = v
                elif st["Key"] == "UserName":
                    username = v
            if k is None:
                if url is not None:
                    print("Nameless entry, using URL")
                    k = path + (url,)
                elif username is not None:
                    print("Nameless entry, using Username")
                    k = path + (url,)
                else:
                    print("Skipping nameless entry")
                    continue
            name = "/".join(k)
            value = "\n".join(filter(lambda e: type(e) == str, (password, username, url, notes)))
            add(name, value)
        for group in get_list(element, "Group"):
            k = group["Name"]
            if k == "Recycle Bin":
                print("Skipping recycle bin")
                continue
            if first:
                sub = tuple()
            else:
                sub = path + (k,)
            enter_group(sub, group, False)
    enter_group(tuple(), root)

sess.save()
