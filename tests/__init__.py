#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""

import os
import locale

def getLocaleAlias(lang_code):
    result = None
    if os.name == 'nt':
        if lang_code == 'ru':
            result = 'Russian_Russia.1251'
        elif lang_code == 'us':
            result = 'English_United States.1252'
        elif lang_code == 'de':
            result = 'German_Germany.1252'
    else:
        if lang_code == 'ru':
            result = 'ru_RU.utf-8'
        elif lang_code == 'us':
            result = 'en_US.utf-8'
        elif lang_code == 'de':
            result = 'de_DE.utf-8'

    if result is None:
        return None

    try:
        old_locale = locale.setlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, result)
    except:
        return None
    finally:
        locale.setlocale(locale.LC_TIME, old_locale)

    return result
