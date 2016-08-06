#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import os
import locale
import re
import sys

import michel as m

google_time_regex = re.compile("(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+).+")

class LocalTzInfo(datetime.tzinfo):
    _offset = datetime.timedelta(seconds = -time.timezone)
    _dst = datetime.timedelta(seconds = time.altzone - time.timezone if time.daylight else 0)
    _name = time.tzname
    def utcoffset(self, dt):
        return self.__class__._offset
    def dst(self, dt):
        return self.__class__._dst
    def tzname(self, dt):
        return self.__class__._name

def from_google_date_format(value):
    time = [int(x) for x in google_time_regex.findall(value)[0] if len(x) > 0]
    return m.OrgDate(datetime.date(time[0], time[1], time[2]))
    
def to_google_date_format(value):
    return value.get_date().strftime("%Y-%m-%dT00:00:00Z")

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
