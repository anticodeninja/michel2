#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import textwrap
import datetime
import locale

import michel as m

class ParserTests(unittest.TestCase):

    def test_text_to_tasktree(self):
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
        Test the case with org-mode properties
        """

        org_text = textwrap.dedent("""\
            Some non-headline text...
            Another line of it.
            * Headline 1
              Body 1a
              Body 1b
            * DONE Headline 2
            ** Headline 2.1
            """)

        tasktree = m.TasksTree.parse_text(org_text)
        self.assertEqual(str(tasktree), org_text)


    def test_no_headlines(self):
        """
        Test the cases where there are no headlines at all in the file.
        """

        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\
            Some non-headline text...
            Another line of it.
            """)

        tasktree = m.TasksTree.parse_text(org_text)
        self.assertEqual(str(tasktree), org_text)


    def test_empty_file(self):
        org_text = "" # empty file
        m.TasksTree.parse_text(org_text)


    def test_parsing_special_comments(self):
        m.default_locale = locale.locale_alias['ru']

        org_text = textwrap.dedent("""\
            * TODO Headline A
              CLOSED: [2015-12-09 Wed 12:34] SCHEDULED: <2015-12-09 Wed>
            * TODO Headline B
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
              https://anticode.ninja
              [[https://anticode.ninja][#anticode.ninja# blog]]
              [[https://github.com/anticodeninja/michel2][michel2 #repo #github]]
              Normal note
            """)

        org_tree = m.TasksTree.parse_text(org_text)

        self.assertEqual(len(org_tree), 2)

        self.assertEqual(org_tree[0].title, "Headline A")
        self.assertEqual(len(org_tree[0].links), 0)
        self.assertEqual(org_tree[0].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 9)))
        self.assertEqual(org_tree[0].closed_time,
                         m.OrgDate(datetime.date(2015, 12, 9),
                                   datetime.time(12, 34)))
        self.assertEqual(org_tree[0].notes, [])

        self.assertEqual(org_tree[1].title, "Headline B")
        self.assertEqual(len(org_tree[1].links), 3)
        self.assertEqual(org_tree[1].links[0], m.TaskLink('https://anticode.ninja'))
        self.assertEqual(org_tree[1].links[1], m.TaskLink('https://anticode.ninja', '#anticode.ninja# blog'))
        self.assertEqual(org_tree[1].links[2], m.TaskLink('https://github.com/anticodeninja/michel2', 'michel2', ['repo', 'github']))
        self.assertEqual(org_tree[1].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 9),
                                   datetime.time(20, 0),
                                   datetime.timedelta(hours=1)))
        self.assertEqual(org_tree[1].notes, ["Normal note"])

        self.assertEqual(str(org_tree), org_text)


if __name__ == '__main__':
    unittest.main()
