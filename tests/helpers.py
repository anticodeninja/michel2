#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import locale
import michel

class TestAdapter:
    pass

class TestMergeConf:
    def __init__(self, renames = None):
        self.__renames = renames

    def is_needed(self, task):
        return task.todo and not task.completed

    def select_org_task(self, unmapped_task, tasklist):
        if self.__renames:
            for old, new, _ in self.__renames:
                if unmapped_task.title == new:
                    if old:
                        return michel.utils.get_index(
                            tasklist,
                            lambda item: item.title == old)
                    else:
                        return 'new'

        raise Exception("Unconfigured select for {0} => {1}".format(
            unmapped_task.title,
            ','.join(x.title for x in tasklist)))

    def merge_title(self, mapping):
        if self.__renames:
            for _, new, sel in self.__renames:
                if mapping.remote.title == new:
                    return sel

        raise Exception("Undefined behavior")

    def merge_completed(self, mapping):
        return mapping.org.completed or mapping.remote.completed

    def merge_closed_time(self, mapping):
        return self.__select_from([mapping.org.closed_time, mapping.remote.closed_time])

    def merge_schedule_time(self, mapping):
        return self.__select_from([mapping.org.schedule_time, mapping.remote.schedule_time])

    def __select_from(self, items):
        items = [x for x in items if x is not None]
        if len(items) == 1:
            return items[0]

        raise Exception("Unconfigured choose for {0}".format(', '.join(str(x) for x in items)))

    def merge_notes(self, mapping):
        items = [x for x in [mapping.org.notes, mapping.remote.notes] if len(x) > 0]
        if len(items) == 1:
            return items[0]

        raise Exception("Undefined behavior")

    def merge_links(self, mapping):
        return michel.BaseMergeConf.merge_links(mapping)


def createTestTree(nodes):
    result = michel.TasksTree(None)

    indexes = []
    leefs = [result]
    for node in nodes:
        if isinstance(node, str):
            pad = len(node) - len(node.lstrip())
            leefs = leefs[:pad+1]
            newTask = leefs[-1].add_subtask(node.strip())
            leefs.append(newTask)
            indexes.append(newTask)
        else:
            leefs[-1].update(**node)

    return result, indexes

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
