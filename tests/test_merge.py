#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""
import unittest
import textwrap
import os
import sys
import tempfile
import datetime
import locale

import michel as m
from tests import getLocaleAlias

class TestMergeConf:
    def get_index(self, items, pred):
        for i, v in enumerate(items):
            if pred(v):
                return i
        return None
                
    def is_needed(self, item):
        return item.todo and not item.completed

    def select_best(self, item, items):
        if (item.task.title == "Headline A1.1") or\
           (item.task.title == "Headline G") or\
           (item.task.title == "Headline H"):
            return None
        
        if item.task.title == "Headline B2 modified":
            return self.get_index(items, lambda item: item.task.title == "Headline B2")
        if item.task.title == "Headline B3":
            return self.get_index(items, lambda item: item.task.title == "Headline B3 original")

        raise Exception("Undefined behavior")

    def select_from(self, name, items):
        if name == "title":
            if items[0] == "Headline B2 modified":
                return items[0]
            if items[0] == "Headline B3":
                return items[1]

        items = [x for x in items if x is not None]
        if len(items) == 1:
            return items[0]

        raise Exception(name, items)
        raise Exception("Undefined behavior")

    def merge_notes(self, name, items):
        if items[0] == ['New B2 body text.']:
            return items[0]

        raise Exception("Undefined behavior")


class TestMichel(unittest.TestCase):
        
    def test_safemerge(self):
    
        org_text = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
               Remote append B1.1 body text.
            * Headline B2
            """)
        org_tree = m.TasksTree.parse_text(org_text)

        remote_tree = m.TasksTree(None)
        remote_tree.add_subtask('Headline A1').\
            add_subtask('Headline A1.1')
        remote_tree.add_subtask('Headline B1').\
            add_subtask('Headline B1.1').update(notes=["Remote append B1.1 body text."])
        remote_tree.add_subtask('Headline A2').update(todo=True).\
            add_subtask('Headline A2.1')
        remote_tree.add_subtask('Headline B2 modified').update(notes=["New B2 body text."])
        
        m.treemerge(org_tree, remote_tree, TestMergeConf())

        result_text = textwrap.dedent("""\
            * Headline A1
            ** Headline A1.1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
               Remote append B1.1 body text.
            * Headline B2 modified
              New B2 body text.
            """)
        self.assertEqual(str(org_tree), result_text)

        
    def test_merge_sync_todo_only(self):
        org_text = textwrap.dedent("""\
            * Headline A
            * Headline B
            ** TODO Headline B1
            * TODO Headline C
            * TODO Headline D
            * Headline E
            ** DONE Headline E1
            * DONE Headline F
            ** Headline F1
            """)
        org_tree = m.TasksTree.parse_text(org_text)

        remote_tree = m.TasksTree(None)
        remote_tree.add_subtask('Headline B1').update(completed=True)
        remote_tree.add_subtask('Headline C').update(completed=True)
        remote_tree.add_subtask('Headline D').update(todo=True)
        remote_tree.add_subtask('Headline G').update(todo=True)

        m.treemerge(org_tree, remote_tree, TestMergeConf())
        
        result_text = textwrap.dedent("""\
            * Headline A
            * Headline B
            ** DONE Headline B1
               CLOSED: [{0}]
            * DONE Headline C
              CLOSED: [{0}]
            * TODO Headline D
            * Headline E
            ** DONE Headline E1
            * DONE Headline F
            ** Headline F1
            * TODO Headline G
            """.format(m.to_emacs_date_format(True, datetime.datetime.now())))
        self.assertEqual(str(org_tree), result_text)

        
    def test_fast_merge(self):
        org_text = textwrap.dedent("""\
            * Headline A
            * Headline B
            ** TODO Headline B1
            ** DONE Headline B2
               CLOSED: [{0}]
            ** TODO Headline B3 original
            * TODO Headline C
            * Headline D
            ** DONE Headline D1
               CLOSED: [{0}]
            * Headline E
            ** DONE Headline E1
            * TODO Headline F
            """.format(m.to_emacs_date_format(True, datetime.datetime.now())))
        org_tree = m.TasksTree.parse_text(org_text)

        remote_tree = m.TasksTree(None)
        remote_tasks = [
            remote_tree.add_subtask('Headline B1').update(completed=True),
            remote_tree.add_subtask('Headline B2 modified').update(todo=True),
            remote_tree.add_subtask('Headline B3').update(todo=True),
            remote_tree.add_subtask('Headline C').update(completed=True),
            remote_tree.add_subtask('Headline D1').update(todo=True),
            remote_tree.add_subtask('Headline G').update(todo=True),
            remote_tree.add_subtask('Headline H').update(completed=True)
        ]

        result_text = textwrap.dedent("""\
            * Headline A
            * Headline B
            ** DONE Headline B1
               CLOSED: [{0}]
            ** DONE Headline B2 modified
               CLOSED: [{0}]
            ** TODO Headline B3 original
            * DONE Headline C
              CLOSED: [{0}]
            * Headline D
            ** DONE Headline D1
               CLOSED: [{0}]
            * Headline E
            ** DONE Headline E1
            * TODO Headline F
            * TODO Headline G
            * DONE Headline H
              CLOSED: [{0}]
            """.format(m.to_emacs_date_format(True, datetime.datetime.now())))


        remote_sync_plan = m.treemerge(org_tree, remote_tree, TestMergeConf())

        self.assertEqual(str(org_tree), result_text)
        self.assertEqual(len(remote_sync_plan), 5)

        # Headline B2
        assertObj = next(x for x in remote_sync_plan if x['item'] == remote_tasks[1])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline B3
        assertObj = next(x for x in remote_sync_plan if x['item'] == remote_tasks[2])
        self.assertEqual(assertObj['action'], 'update')
        self.assertEqual(assertObj['changes'], ['title'])
        self.assertEqual(assertObj['item'].title, 'Headline B3 original')

        # Headline D1
        assertObj = next(x for x in remote_sync_plan if x['item'] == remote_tasks[4])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline F
        assertObj = next(x for x in remote_sync_plan if x['item'].title == "Headline F")
        self.assertEqual(assertObj['action'], 'append')
        self.assertEqual(assertObj['item'].title, 'Headline F')

        # Headline H
        assertObj = next(x for x in remote_sync_plan if x['item'] == remote_tasks[6])
        self.assertEqual(assertObj['action'], 'remove')
        

    def test_sync_time(self):
        import michel.utils as mu
        mu.default_locale = getLocaleAlias('us')
        
        org_text = textwrap.dedent("""\
            * TODO Headline A
            * TODO Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            """)
        org_tree = m.TasksTree.parse_text(org_text)

        remote_tree = m.TasksTree(None)
        remote_tree.add_subtask('Headline A').update(todo=True, scheduled_start_time=datetime.datetime(2015, 12, 9, tzinfo = m.LocalTzInfo()))
        remote_tree.add_subtask('Headline B').update(todo=True)
        remote_tree.add_subtask('Headline C').update(completed=True,
                                                     scheduled_has_time=True,
                                                     scheduled_start_time=datetime.datetime(2015, 12, 9, 20, 0, tzinfo = m.LocalTzInfo()),\
                                                     scheduled_end_time=datetime.datetime(2015, 12, 9, 21, 0, tzinfo = m.LocalTzInfo()))
        remote_tree.add_subtask('Headline D').update(todo=True, scheduled_start_time=datetime.datetime(2015, 12, 9, tzinfo = m.LocalTzInfo()))
        
        m.treemerge(org_tree, remote_tree, TestMergeConf())

        result_text = textwrap.dedent("""\
            * TODO Headline A
              SCHEDULED: <2015-12-09 Wed>
            * TODO Headline B
            * DONE Headline C
              CLOSED: [{0}] SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            * TODO Headline D
              SCHEDULED: <2015-12-09 Wed>
            """.format(m.to_emacs_date_format(True, datetime.datetime.now())))
        self.assertEqual(str(org_tree), result_text)

        
if __name__ == '__main__':
    unittest.main()
