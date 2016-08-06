#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import re
import io
import datetime
import subprocess
import tempfile
import difflib

from michel.utils import *
import michel.console as console

class InteractiveMergeConf:
    def __init__(self, adapter, only_todo = True):
        self.__adapter = adapter
        self.__only_todo = only_todo
                
    def is_needed(self, task):
        if hasattr(self.__adapter, 'is_needed'):
            return self.__adapter.is_needed(self.__is_needed, task)
        return self.__is_needed(task)

    def select_org_task(self, unmapped_task, tasklist):
        if hasattr(self.__adapter, 'select_org_task'):
            return self.__adapter.select_org_task(self.__select_org_task, unmapped_task, tasklist)
        return self.__select_org_task(unmapped_task, tasklist)

    def merge_title(self, mapping):
        if hasattr(self.__adapter, 'merge_title'):
            return self.__adapter.merge_title(self.__merge_title, mapping)
        return self.__merge_title(mapping)

    def merge_completed(self, mapping):
        if hasattr(self.__adapter, 'merge_completed'):
            return self.__adapter.merge_completed(self.__merge_completed, mapping)
        return self.__merge_completed(mapping)

    def merge_closed_time(self, mapping):
        if hasattr(self.__adapter, 'merge_closed_time'):
            return self.__adapter.merge_closed_time(self.__merge_closed_time, mapping)
        return self.__merge_closed_time(mapping)

    def merge_schedule_time(self, mapping):
        if hasattr(self.__adapter, 'merge_schedule_time'):
            return self.__adapter.merge_schedule_time(self.__merge_schedule_time, mapping)
        return self.__merge_schedule_time(mapping)

    def merge_notes(self, mapping):
        if hasattr(self.__adapter, 'merge_notes'):
            return self.__adapter.merge_notes(self.__merge_notes, mapping)
        return self.__merge_notes(mapping)
    

    def __is_needed(self, task):
        if task.completed:
            return False

        if self.__only_todo:
            return task.todo

        return True

    def __select_org_task(self, unmapped_task, tasklist):        
        uprint("\"{0}\" has not exact mapping in your local org-tree.".format(unmapped_task.title))
        uprint("Please manualy choose necessary item:")
        count = 2

        items = [[i, v, difflib.SequenceMatcher(a=unmapped_task.title, b=v.title).ratio()]
                 for i, v in enumerate(tasklist)]
        items.sort(key=lambda v: v[2], reverse=True)
        items_count = len(items)
        items_count_for_showing = 10
        
        while True:
            for i in range(min(items_count, items_count_for_showing)):
                uprint("[{0}] {1}".format(i, items[i][1].title))
                count += 1 
                
            if items_count > items_count_for_showing:
                uprint("[m] ...")
                count += 1
            
            uprint("[n] -- create new")
            uprint("[d] -- discard new")
            count += 2

            result = input()
            count += 1
            
            try:
                if result == 'm':
                    items_count_for_showing = items_count
                    continue
                elif result == 'n':
                    result = 'new'
                    break
                elif result == 'd':
                    result = 'discard'
                    break

                result = int(result)
                if result >= 0 and result <= items_count:
                    result = items[result][0]
                    break
            except:
                pass

            uprint("Incorrect input!")
            count += 1

        console.cleanLastRows(count)
        return result

    def __merge_title(self, mapping):
        detected_change = self.__extract_from_base(mapping, 'title')
        if detected_change is not None:
            return detected_change
        
        return self.__select_from([
            "Tasks has different titles",
            "Please manualy choose necessary value:"
        ], [
            mapping.org.title,
            mapping.remote.title
        ])

    def __merge_completed(self, mapping):
        detected_change = self.__extract_from_base(mapping, 'completed')
        if detected_change is not None:
            return detected_change

        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"completed\"".format(mapping.org.title),
            "Please manualy choose necessary value:"
        ], [
            mapping.org.completed,
            mapping.remote.completed
        ])

    def __merge_closed_time(self, mapping):
        if mapping.org.completed:
            if mapping.remote.closed_time and mapping.org.closed_time:
                return min(mapping.org.closed_time,  mapping.remote.closed_time)
            elif mapping.org.closed_time or mapping.remote.closed_time:
                return mapping.org.closed_time or mapping.remote.closed_time
            else:
                return m.OrgDate.now()
        else:
            return None

    def __merge_schedule_time(self, mapping):
        detected_change = self.__extract_from_base(mapping, 'schedule_time')
        if detected_change is not None:
            return detected_change
        
        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"schedule_time\"".format(mapping.org.title),
            "Please manualy choose necessary value:"
        ], [
            mapping.org.schedule_time,
            mapping.remote.schedule_time
        ])

    def __merge_notes(self, mapping):
        detected_change = self.__extract_from_base(mapping, 'notes')
        if detected_change is not None:
            return detected_change
        
        uprint("Task \"{0}\" has different values for attribute \"notes\"".format(mapping.org.title))
        uprint("Please manualy choose necessary:")
        count = 2

        items = [mapping.org.notes, mapping.remote.notes]
        while True:
            for i, v in enumerate(items):
                uprint("[{0}] Use this block:".format(i))
                count += 1
                
                for line in v:
                    uprint(line)
                    count += 1
                    
                uprint("-------------------------------------")
                count += 1
        
            uprint("[e] Edit in external editor")
            count += 1
            
            result = input()
            count += 1
            
            try:
                if result == 'e':
                    result = None
                    break
                
                result = int(result)
                if result >= 0 and result <= i:
                    result = items[result]
                    break
            except:
                pass

            uprint("Incorrect input!")
            count += 1

        console.cleanLastRows(count)
        if result is not None:
            return result

        # External editor
        temp_fid, temp_name = tempfile.mkstemp()
        try:
            with codecs.open(temp_name, "w", encoding="utf-8") as temp_file:
                for item in items:
                    for line in item:
                        temp_file.write(line)
                        temp_file.write('\n')
                    
            subprocess.call('vim -n {0}'.format(temp_name), shell=True)
            
            with codecs.open(temp_name, "r", encoding="utf-8") as temp_file:
                result = [x.strip() for x in temp_file.readlines()]
            
        except Exception as e:
            uprint(e)
            
        os.close(temp_fid)
        os.remove(temp_name)
        return result

    def __extract_from_base(self, mapping, name):
        if mapping.base is None:
            return None

        value_org = getattr(mapping.org, name)
        value_remote = getattr(mapping.remote, name)
        value_base = getattr(mapping.base, name)

        if value_base == value_org:
            return value_remote
        if value_base == value_remote:
            return value_org
        return None
                

    def __select_from(self, message, items):
        for l in message:
            uprint(l)
        count = len(message)
        
        while True:
            for i, v in enumerate(items):
                uprint("[{0}] {1}".format(i, v))
            count += len(items)

            result = input()
            count += 1
            
            try:
                result = int(result)
                if result >= 0 and result <= i:
                    result = items[result]
                    break
            except:
                pass

            uprint("Incorrect input!")
            count += 1

        console.cleanLastRows(count)
        return result
