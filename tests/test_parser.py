#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""
import unittest
import textwrap
import datetime
import locale

import michel as m

class TestMichel(unittest.TestCase):

    def test_text_to_tasktree(self):
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\
            * Headline 1
            Body 1a
                Body 1b
            * DONE    Headline 2
            ** Headline 2.1
            """)
        result_text = textwrap.dedent("""\
            * Headline 1
              Body 1a
              Body 1b
            * DONE Headline 2
            ** Headline 2.1
            """)
        tasktree = m.TasksTree.parse_text(org_text)
        self.assertEqual(str(tasktree), result_text)

        
    def test_initial_non_headline_text(self):
        """
        Test the case where the first lines of an org-mode file are not
        org-mode headlines.
        
        """
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\

            Some non-headline text...
            Another line of it.
            * Headline 1
            Body 1a
                Body 1b
            * DONE    Headline 2
            ** Headline 2.1
            """)

        self.assertRaises(ValueError, m.TasksTree.parse_text, org_text)

        
    def test_no_headlines(self):
        """
        Test the cases where there are no headlines at all in the file.
        
        """
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\

            Some non-headline text...
            Another line of it.
            """)

        self.assertRaises(ValueError, m.TasksTree.parse_text, org_text)

        
    def test_empty_file(self):
        org_text = "" # empty file
        m.TasksTree.parse_text(org_text)
        
    
    def test_parsing_special_comments(self):
        m.default_locale = locale.locale_alias['ru']
        
        org_text = textwrap.dedent("""\
            * TODO Headline B
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
              Normal note
            """)
        
        org_tree = m.TasksTree.parse_text(org_text)

        self.assertEqual(len(org_tree), 1)
        self.assertEqual(org_tree[0].title, "Headline B")
        self.assertEqual(org_tree[0].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 9),
                                   datetime.time(20, 0),
                                   datetime.timedelta(hours=1)))
        self.assertEqual(org_tree[0].notes, ["Normal note"])

        
if __name__ == '__main__':
    unittest.main()
