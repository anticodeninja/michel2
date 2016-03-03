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

@unittest.skipUnless(os.getenv('MANUAL_TESTING'), 'Enable only for manual-testing')
class TestInteractiveMerge(unittest.TestCase):

    def test_selectbest(self):        
        conf = m.InteractiveMergeConf(True)
        tasks = [m.TasksTree('Headline A modified'), m.TasksTree('Headline B')]
        self.assertEqual(conf.select_best(m.TasksTree('Headline A'), tasks), 0)
        self.assertEqual(conf.select_best(m.TasksTree('Headline C'), tasks), 'new')
        self.assertEqual(conf.select_best(m.TasksTree('Discard it'), tasks), 'discard')

    def test_selectfrom(self):        
        conf = m.InteractiveMergeConf(True)
        self.assertEqual(conf.select_from("title", [
            "Choose it",
            "Do not chouse it"
        ]), "Choose it")

        print("------ Choose earlier ------")
        self.assertEqual(conf.select_from("scheduled_start_time", [
            datetime.datetime(2015, 12, 15, tzinfo = m.LocalTzInfo()),
            datetime.datetime(2015, 12, 10, tzinfo = m.LocalTzInfo())
        ]), datetime.datetime(2015, 12, 10, tzinfo = m.LocalTzInfo()))

    def test_mergenotes(self):        
        conf = m.InteractiveMergeConf(True)
        self.assertEqual(conf.merge_notes([
            ["Choose this block", ":) :) :)"],
            ["Do not choose it", ":( :( :("]
        ]), ["Choose this block", ":) :) :)"])
        self.assertEqual(conf.merge_notes([
            ["Merge it by external editor", "And choose it"],
            ["But remove it", "Remove part from this<REMOVE_IT>"]
        ]), ["Merge it by external editor", "And choose it", "Remove part from this"])
        
if __name__ == '__main__':
    unittest.main()
