#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import time
import os
import locale
import sys

from importlib.machinery import SourceFileLoader

import michel as m


def parse_provider_url(url):
    protocol, extra = url.split('://')
    extra = extra.split('?')

    path = extra[0]
    path = path.split("/")

    params = dict(x.split("=") for x in extra[1].split("&")) if len(extra) > 1 else {}

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
        print(*objects, sep=sep, end=end, file=file, flush=True)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file, flush=True)
