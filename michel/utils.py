#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import os
import locale
import re
import sys

from importlib.machinery import SourceFileLoader

import michel as m

_url_regex = re.compile("(\w+)://([\w/]+)(?:\?([\w=&]+))?")

def parse_provider_url(url):
    matches = _url_regex.findall(url)
    
    protocol = matches[0][0]
    path = matches[0][1].split("/")
    params = dict(x.split("=") for x in matches[0][2].split("&")) if len(matches[0][2]) > 0 else None
    
    return protocol, path, params

def get_provider(url):
    protocol, path, params = m.parse_provider_url(url)
    dirname = os.path.dirname(__file__)
    provider_name = (protocol + "provider").lower()

    for filename in os.listdir(dirname):
        name, ext = os.path.splitext(os.path.basename(filename))
        if name == "__init__" or name == "__main__" or ext != ".py":
            continue

        temp = SourceFileLoader(name, os.path.join(dirname, filename)).load_module()
        for entryname in dir(temp):
            if entryname.lower() != provider_name:
                continue

            return getattr(temp, entryname)(path, params)

    raise Exception("Provider does not found")

def save_data_path(file_name):
    data_path = os.path.join(os.path.expanduser('~'), ".michel")
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    return os.path.join(data_path, file_name)

def get_index(items, pred):
    for i, v in enumerate(items):
        if pred(v):
            return i
    return None

def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)
