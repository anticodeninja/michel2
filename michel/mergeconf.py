#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import codecs
import collections
import re
import io
import datetime
import subprocess
import tempfile
import difflib

from michel.utils import *
import michel.console as console

class BaseMergeConf:

    def __init__(self, adapter, only_todo = True):
        self._adapter = adapter
        self._only_todo = only_todo


    def is_needed(self, task):
        if hasattr(self._adapter, 'is_needed'):
            return self._adapter.is_needed(self._is_needed, task)
        return self._is_needed(task)


    def select_org_task(self, unmapped_task, tasklist):
        if hasattr(self._adapter, 'select_org_task'):
            return self._adapter.select_org_task(self._select_org_task, unmapped_task, tasklist)
        return self._select_org_task(unmapped_task, tasklist)


    def merge_title(self, mapping):
        if hasattr(self._adapter, 'merge_title'):
            return self._adapter.merge_title(self._merge_title, mapping)
        return self._merge_title(mapping)


    def merge_completed(self, mapping):
        if hasattr(self._adapter, 'merge_completed'):
            return self._adapter.merge_completed(self._merge_completed, mapping)
        return self._merge_completed(mapping)


    def merge_closed_time(self, mapping):
        if hasattr(self._adapter, 'merge_closed_time'):
            return self._adapter.merge_closed_time(self._merge_closed_time, mapping)
        return self._merge_closed_time(mapping)


    def merge_schedule_time(self, mapping):
        if hasattr(self._adapter, 'merge_schedule_time'):
            return self._adapter.merge_schedule_time(self._merge_schedule_time, mapping)
        return self._merge_schedule_time(mapping)


    def merge_notes(self, mapping):
        if hasattr(self._adapter, 'merge_notes'):
            return self._adapter.merge_notes(self._merge_notes, mapping)
        return self._merge_notes(mapping)


    def merge_links(self, mapping):
        if hasattr(self._adapter, 'merge_links'):
            return self._adapter.merge_links(self._merge_notes, mapping)
        return self._merge_links(mapping)


    def _is_needed(self, task):
        if task.completed:
            return False

        if self._only_todo:
            return task.todo

        return True


    def _merge_closed_time(self, mapping):
        if mapping.org.completed:
            if mapping.remote.closed_time and mapping.org.closed_time:
                return min(mapping.org.closed_time, mapping.remote.closed_time)
            elif mapping.org.closed_time or mapping.remote.closed_time:
                return mapping.org.closed_time or mapping.remote.closed_time
            else:
                return m.OrgDate.now()
        else:
            return None


    @classmethod
    def merge_links(cls, mapping):
        # TODO Make it interactive
        total = collections.OrderedDict()

        def update(links):
            for link in links:
                temp = total.setdefault(link.link, m.TaskLink(link.link))
                if link.title:
                    temp.title = link.title
                if len(link.tags) > 0:
                    temp.tags = link.tags

        update(mapping.org.links)
        update(mapping.remote.links)

        return [x for x in total.values()]



class InteractiveMergeConf(BaseMergeConf):

    def _select_org_task(self, unmapped_task, tasklist):
        uprint("\"{0}\" has no exact mapping in your local org-tree.".format(unmapped_task.title))
        uprint("Please manually choose the wanted item:")
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


    def _merge_title(self, mapping):
        return self.__select_from([
            "Tasks has different titles",
            "Please manualy choose necessary value:"
        ], [
            mapping.org.title,
            mapping.remote.title
        ])


    def _merge_completed(self, mapping):
        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"completed\"".format(mapping.org.title),
            "Please manualy choose necessary value:"
        ], [
            mapping.org.completed,
            mapping.remote.completed
        ])


    def _merge_schedule_time(self, mapping):
        return self.__select_from([
            "Task \"{0}\" has different values for attribute \"schedule_time\"".format(mapping.org.title),
            "Please manualy choose necessary value:"
        ], [
            mapping.org.schedule_time,
            mapping.remote.schedule_time
        ])


    def _merge_notes(self, mapping):
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


    def _merge_links(self, mapping):
        return BaseMergeConf.merge_links(mapping)


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



class PushMergeConf(BaseMergeConf):

    def _select_org_task(self, unmapped_task, tasklist):
        items = [[i, v, difflib.SequenceMatcher(a=unmapped_task.title, b=v.title).ratio()]
                 for i, v in enumerate(tasklist)]
        items.sort(key=lambda v: v[2], reverse=True)
        return items[0][0]


    def _merge_title(self, mapping):
        return mapping.org.title


    def _merge_completed(self, mapping):
        return mapping.org.completed


    def _merge_schedule_time(self, mapping):
        return mapping.org.schedule_time


    def _merge_notes(self, mapping):
        return mapping.org.notes


    def _merge_links(self, mapping):
        return mapping.org.links
