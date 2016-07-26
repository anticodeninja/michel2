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
    def __init__(self, adapter):
        self.adapter = adapter
        
                
    def is_needed(self, task_org):
        if hasattr(self.adapter, 'is_needed'):
            return self.adapter.is_needed(self.__is_needed, task_org)
        return self.__is_needed(task_org)

    def select_org_task(self, task_remote, tasks_org):
        if hasattr(self.adapter, 'select_org_task'):
            return self.adapter.select_org_task(self.__select_org_task, task_remote, tasks_org)
        return self.__select_org_task(task_remote, tasks_org)

    def merge_title(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_title'):
            return self.adapter.merge_title(self.__merge_title, task_remote, task_org)
        return self.__merge_title(task_remote, task_org)

    def merge_completed(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_completed'):
            return self.adapter.merge_completed(self.__merge_completed, task_remote, task_org)
        return self.__merge_completed(task_remote, task_org)

    def merge_closed_time(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_closed_time'):
            return self.adapter.merge_closed_time(self.__merge_closed_time, task_remote, task_org)
        return self.__merge_closed_time(task_remote, task_org)

    def merge_scheduled_start_time(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_scheduled_start_time'):
            return self.adapter.merge_scheduled_start_time(self.__merge_scheduled_start_time, task_remote, task_org)
        return self.__merge_scheduled_start_time(task_remote, task_org)

    def merge_scheduled_end_time(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_scheduled_end_time'):
            return self.adapter.merge_scheduled_end_time(self.__merge_scheduled_end_time, task_remote, task_org)
        return self.__merge_scheduled_end_time(task_remote, task_org)

    def merge_notes(self, task_remote, task_org):
        if hasattr(self.adapter, 'merge_notes'):
            return self.adapter.merge_notes(self.__merge_notes, task_remote, task_org)
        return self.__merge_notes(task_remote, task_org)
    

    def __is_needed(self, task_org):
        return True

    def __select_org_task(self, task_remote, tasks_org):        
        uprint("\"{0}\" has not exact mapping in your local org-tree.".format(task_remote.title))
        uprint("Please manualy choose necessary item:")
        count = 2

        items = [[i, v, difflib.SequenceMatcher(a=task_remote.title, b=v.title).ratio()]
                 for i, v in enumerate(tasks_org)]
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

    def __merge_title(self, task_remote, task_org):
        return self.__select_from([
            "Tasks has different titles",
            "Please manualy choose necessary value:"
        ], [
            task_remote.title,
            task_org.title
        ])

    def __merge_completed(self, task_remote, task_org):
        return task_remote.completed or task_org.completed

    def __merge_closed_time(self, task_remote, task_org):
        if task_remote.completed:
            if task_remote.closed_time and task_org.closed_time:
                return min(task_remote.closed_time,  task_org.closed_time)
            elif task_remote.closed_time or task_org.closed_time:
                return task_remote.closed_time or task_org.closed_time
            else:
                return datetime.datetime.now()
        else:
            return None

    def __merge_scheduled_start_time(self, task_remote, task_org):
        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"scheduled_start_time\"".format(task_remote.title),
            "Please manualy choose necessary value:"
        ], [
            task_remote.scheduled_start_time,
            task_org.scheduled_start_time
        ])

    def __merge_scheduled_end_time(self, task_remote, task_org):
        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"scheduled_end_time\"".format(task_remote.title),
            "Please manualy choose necessary value:"
        ], [
            task_remote.scheduled_end_time,
            task_org.scheduled_end_time
        ])

    def __merge_notes(self, task_remote, task_org):
        uprint("Task \"{0}\" has different values for attribute \"notes\"".format(task_remote.title))
        uprint("Please manualy choose necessary:")
        count = 2

        items = [task_remote.notes, task_org.notes]
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
