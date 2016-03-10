#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import re
import io
import datetime
import subprocess
import tempfile

from michel.utils import *

class InteractiveMergeConf:
    def __init__(self, todo_only):
        self.todo_only = todo_only
                
    def is_needed(self, item):
        if item.completed:
            return False

        if self.todo_only:
            return item.todo
        
        return True

    def select_best(self, item, items):
        uprint("\"{0}\" has not exact mapping in your local org-tree.".format(item.title))
        uprint("Please manualy choose necessary item:")
        
        while True:
            for i, v in enumerate(items):
                uprint("[{0}] {1}".format(i, v.title))
            uprint("[n] -- create new")
            uprint("[d] -- discard new")

            result = input()
            try:
                if result == 'n':
                    return 'new'
                if result == 'd':
                    return 'discard'

                result = int(result)
                if result >= 0 and result <= i:
                    return result
            except:
                pass

            uprint("Incorrect input!")


    def select_from(self, name, items):
        uprint("Attribute \"{0}\" has different values for different items.".format(name))
        uprint("Please manualy choose necessary value:")
        
        while True:
            for i, v in enumerate(items):
                uprint("[{0}] {1}".format(i, v))

            result = input()
            try:
                result = int(result)
                if result >= 0 and result <= i:
                    return items[result]
            except Exception as e:
                uprint(e)

            uprint("Incorrect input!")

    def merge_notes(self, items):
        uprint("Notes are different values for different items.")
        uprint("Please manualy choose necessary:")
        
        while True:
            for i, v in enumerate(items):
                uprint("[{0}] Use this block:".format(i))
                for line in v:
                    uprint(line)
                uprint("-------------------------------------")
                uprint()

            uprint("[e] Edit in external editor")
            
            result = input()
            try:
                if result == 'e':
                    break
                
                result = int(result)
                if result >= 0 and result <= i:
                    return items[result]
            except Exception as e:
                uprint(e)

            uprint("Incorrect input!")

        # External editor
        temp_fid, temp_name = tempfile.mkstemp()
        try:
            with codecs.open(temp_name, "w", encoding="utf-8") as temp_file:
                for item in items:
                    for line in item:
                        temp_file.write(line)
                        temp_file.write('\n')

            editor = os.getenv('EDITOR', 'vim')
            if editor == "vim":
                subprocess.call('vim -n {1}'.format(editor, temp_name), shell=True)
            
            with codecs.open(temp_name, "r", encoding="utf-8") as temp_file:
                result = [x.strip() for x in temp_file.readlines()]
        except Exception as e:
            uprint(e)
            
        os.close(temp_fid)
        os.remove(temp_name)
        return result
        
