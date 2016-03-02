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
        return (item.todo or not self.todo_only) and not item.completed

    def select_best(self, item, items):
        print("\"{0}\" has not exact mapping in your local org-tree.".format(item.title))
        print("Please manualy choose necessary item:")
        
        while True:
            for i, v in enumerate(items):
                print("[{0}] {1}".format(i, v.title))
            print("[-] -- Not existed")

            result = input()
            try:
                if result == '-':
                    return None

                result = int(result)
                if result >= 0 and result <= i:
                    return result
            except:
                pass

            print("Incorrect input!")


    def select_from(self, name, items):
        print("Attribute \"{0}\" has different values for different items.".format(name))
        print("Please manualy choose necessary value:")
        
        while True:
            for i, v in enumerate(items):
                print("[{0}] {1}".format(i, v))

            result = input()
            try:
                result = int(result)
                if result >= 0 and result <= i:
                    return items[result]
            except Exception as e:
                print(e)

            print("Incorrect input!")

    def merge_notes(self, items):
        print("Notes are different values for different items.")
        print("Please manualy choose necessary:")
        
        while True:
            for i, v in enumerate(items):
                print("[{0}] Use this block:".format(i))
                for line in v:
                    print(line)
                print("-------------------------------------")
                print()

            print("[e] Edit in external editor")
            
            result = input()
            try:
                if result == 'e':
                    break
                
                result = int(result)
                if result >= 0 and result <= i:
                    return items[result]
            except Exception as e:
                print(e)

            print("Incorrect input!")

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
            print(e)
            
        os.close(temp_fid)
        os.remove(temp_name)
        return result
        
