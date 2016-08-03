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

class TestAdapter:
    pass

@unittest.skipUnless(os.getenv('MANUAL_TESTING'), 'Enable only for manual-testing')
class TestInteractiveMerge(unittest.TestCase):

    def test_select_org_task(self):        
        conf = m.InteractiveMergeConf(TestAdapter())
        tasks = [m.TasksTree('Correct Task'), m.TasksTree('Absolutely Another Task')]
        
        self.assertEqual(conf.select_org_task(m.TasksTree('Select Correct Task'), tasks), 0)
        self.assertEqual(conf.select_org_task(m.TasksTree('Create new'), tasks), 'new')
        self.assertEqual(conf.select_org_task(m.TasksTree('Discard it'), tasks), 'discard')

    def test_merge_title(self):        
        conf = m.InteractiveMergeConf(TestAdapter())
        tasks = [m.TasksTree('Choose it'), m.TasksTree('Do not chouse it')]
        
        self.assertEqual(conf.merge_title(m.MergeEntry(tasks[0], tasks[1])), tasks[0].title)

    def test_merge_scheduled_start_time(self):
        conf = m.InteractiveMergeConf(TestAdapter())
        tasks = [
            m.TasksTree('!!!Choose earlier!!!').update(
                scheduled_start_time=datetime.datetime(2015, 12, 15, tzinfo = m.LocalTzInfo())),
            m.TasksTree('Press Ctrl-D').update(
                scheduled_start_time=datetime.datetime(2015, 12, 10, tzinfo = m.LocalTzInfo()))]
        
        self.assertEqual(conf.merge_scheduled_start_time(m.MergeEntry(tasks[0], tasks[1])), tasks[1].scheduled_start_time)

    def test_merge_notes(self):        
        conf = m.InteractiveMergeConf(TestAdapter())
        tasks = [
            m.TasksTree('Simply choose necessary block').update(
                notes=["Choose this block", ":) :) :)"]),
            m.TasksTree('Press Ctrl-D').update(
                notes=["Do not choose it", ":( :( :("])]

        self.assertEqual(conf.merge_notes(m.MergeEntry(tasks[0], tasks[1])), tasks[0].notes)

        tasks = [
            m.TasksTree('Merge it by external editor').update(
                notes=["Choose this block"]),
            m.TasksTree('Press Ctrl-D').update(
                notes=["Remove this block", "Remove part from this block<REMOVE_IT>"])]
        self.assertEqual(conf.merge_notes(m.MergeEntry(tasks[0], tasks[1])), ["Choose this block", "Remove part from this block"])
        
if __name__ == '__main__':
    unittest.main()
