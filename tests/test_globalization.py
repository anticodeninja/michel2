#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""

import unittest
import textwrap
import os
import tempfile
import datetime
import locale
import sys

import michel as m
from michel.utils import *
from tests import getLocaleAlias

class TestMichel(unittest.TestCase):
                         

    def test_format_emacs_dates(self):
        test_locale = getLocaleAlias('ru')
        if test_locale:
            m.OrgDate.default_locale = test_locale
            self.assertEqual(
                "2015-12-09 Ср",
                m.OrgDate(datetime.date(2015, 12, 9)).to_org_format())

        test_locale = getLocaleAlias('us')
        if test_locale:
            m.OrgDate.default_locale = test_locale
            self.assertEqual(
                "2015-11-18 Wed",
                m.OrgDate(datetime.date(2015, 11, 18)).to_org_format())

        test_locale = getLocaleAlias('de')
        if test_locale:
            m.OrgDate.default_locale = test_locale
            self.assertEqual(
                "2015-12-10 Do",
                m.OrgDate(datetime.date(2015, 12, 10)).to_org_format())

    def test_unicode_print(self):
        """
        Test ability to print unicode text
        """
        
        tasks_tree = m.TasksTree(None)
        task = tasks_tree.add_subtask('السلام عليكم')
        task.notes = ['viele Grüße']

        test_stdout = open(os.devnull, 'w')
        try:
            uprint(tasks_tree, file=test_stdout)
        except UnicodeDecodeError:
            self.fail("TasksTree._print() raised UnicodeDecodeError")
        test_stdout.close()

        
    def test_unicode_dump_to_file(self):
        """
        Test ability to pull unicode text into orgfile
        """

        tasks_tree = m.TasksTree(None)
        task = tasks_tree.add_subtask('السلام عليكم')
        task.notes = ['viele Grüße']

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file_name = temp_file.name
            
        try:
            tasks_tree.write_file(temp_file_name)
        except UnicodeDecodeError:
            self.fail("TasksTree.write_to_orgfile() raised UnicodeDecodeError")

        
    def test_scheduled_and_closed_time(self):
        m.OrgDate.default_locale = getLocaleAlias('us')
        
        org_text = textwrap.dedent("""\
            * Headline 1
              Normal notes
            * Headline 2
              SCHEDULED: <2015-11-18 Wed>
            * Headline 3
              SCHEDULED: <2015-12-09 Wed 19:00-20:00>
            * DONE Headline 4
              CLOSED: [2015-12-10 Thu 03:25]
            * DONE Headline 5
              CLOSED: [2015-12-10 Thu 03:25] SCHEDULED: <2015-12-09 Wed 03:00>
            """)
        tasktree = m.TasksTree.parse_text(org_text)
        
        self.assertEqual(tasktree[0].closed_time, None)
        self.assertEqual(tasktree[0].schedule_time, None)

        self.assertEqual(tasktree[1].closed_time, None)
        self.assertEqual(tasktree[1].schedule_time,
                         m.OrgDate(datetime.date(2015, 11, 18)))

        self.assertEqual(tasktree[2].closed_time, None)
        self.assertEqual(tasktree[2].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 9),
                                   datetime.time(19, 0),
                                   datetime.timedelta(hours=1)))

        self.assertEqual(tasktree[3].closed_time,
                         m.OrgDate(datetime.date(2015, 12, 10),
                                   datetime.time(3, 25)))
        self.assertEqual(tasktree[3].schedule_time, None)

        self.assertEqual(tasktree[4].closed_time,
                         m.OrgDate(datetime.date(2015, 12, 10),
                                   datetime.time(3, 25)))
        self.assertEqual(tasktree[4].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 9),
                                   datetime.time(3, 0)))
                         
        self.assertEqual(str(tasktree), org_text)


if __name__ == '__main__':
    unittest.main()
