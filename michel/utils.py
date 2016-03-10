#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import os
import locale
import re
import sys

default_locale = locale.setlocale(locale.LC_TIME, '')
locale.setlocale(locale.LC_TIME, 'C')

google_time_regex = re.compile("(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+).+")
emacs_time_regex = re.compile("(\d+)-(\d+)-(\d+) \S+(?: (\d+):(\d+)(?:-(\d+):(\d+))?)?")

class LocalTzInfo(datetime.tzinfo):
    _offset = datetime.timedelta(seconds = time.timezone)
    _dst = datetime.timedelta(seconds = time.daylight)
    _name = time.tzname
    def utcoffset(self, dt):
        return self.__class__._offset
    def dst(self, dt):
        return self.__class__._dst
    def tzname(self, dt):
        return self.__class__._name

def from_google_date_format(value):
    time = [int(x) for x in google_time_regex.findall(value)[0] if len(x) > 0]
    
    first_time = datetime.datetime(time[0], time[1], time[2],
                                   time[3], time[4],
                                   tzinfo = LocalTzInfo())

    return first_time
    
def to_google_date_format(value):
    return value.strftime("%Y-%m-%dT00:00:00Z")

def from_emacs_date_format(value):
    time = [int(x) for x in emacs_time_regex.findall(value)[0] if len(x) > 0]

    has_time = False
    first_time = None
    second_time = None

    if len(time) == 3:
        first_time = datetime.datetime(time[0], time[1], time[2],
                                       tzinfo = LocalTzInfo())

    if len(time) > 3:
        has_time = True
        first_time = datetime.datetime(time[0], time[1], time[2],
                                       time[3], time[4],
                                       tzinfo = LocalTzInfo())
        
    if len(time) > 5:
        second_time = datetime.datetime(time[0], time[1], time[2],
                                     time[5], time[6],
                                     tzinfo = LocalTzInfo())

    return has_time, first_time, second_time

def to_emacs_date_format(has_duration, value, end_value = None):
    try:
        old_locale = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, default_locale)
        res = value.strftime("%Y-%m-%d %a")

        if has_duration:
            res += value.strftime(" %H:%M")
            if end_value:
                res += end_value.strftime("-%H:%M")

        if os.name == 'nt':
            # It's hell...
            res = res.encode('latin-1').decode(locale.getpreferredencoding())
                                           
        return res
    finally:
        locale.setlocale(locale.LC_TIME, old_locale)    

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
