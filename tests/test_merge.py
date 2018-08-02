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
import os
import sys
import tempfile
import datetime
import locale

import michel as m
import tests

class MergeTests(unittest.TestCase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.now = m.OrgDate.now()
        m.OrgDate.default_locale = tests.getLocaleAlias('us')

    def test_org_date(self):
        reference = m.OrgDate(datetime.date(2016, 8, 5),
                              datetime.time(12, 0))
        same = m.OrgDate(datetime.date(2016, 8, 5),
                         datetime.time(12, 0))
        earlier = m.OrgDate(datetime.date(2016, 8, 4),
                         datetime.time(12, 0))
        later = m.OrgDate(datetime.date(2016, 8, 5),
                          datetime.time(12, 45))

        self.assertEqual(reference, same)
        self.assertEqual(earlier < reference, True)
        self.assertEqual(reference < later, True)
        self.assertEqual(min(later, earlier, reference), earlier)

    def test_todo_only(self):

        # Arrange
        org_tree = m.TasksTree.parse_text("""\
            * NotEntry
            * TODO TodoEntry
            * DONE CompletedEntry
              CLOSED: [{0}]
            * NotExtEntry
            ** NotExtNotIntEntry
            ** TODO NotExtTodoIntEntry
            ** DONE NotExtCompletedIntEntry
               CLOSED: [{0}]
            * TODO TodoExtEntry
            ** TodoExtNotIntEntry
            ** TODO TodoExtTodoIntEntry
            ** DONE TodoExtCompletedIntEntry
               CLOSED: [{0}]
        """.format(self.now.to_org_format()))

        remote_tree, indexes = tests.createTestTree([
            "TodoEntry", dict(completed=True,
                              closed_time=self.now),
            "NotExtTodoIntEntry", dict(completed=True,
                                       closed_time=self.now),
            "TodoExtEntry", dict(completed=True,
                                 closed_time=self.now),
            "TodoExtTodoIntEntry", dict(completed=True,
                                        closed_time=self.now),
            "NewTodoEntry", dict(todo=True),
        ])

        # Act
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "NewTodoEntry", None]
        ]))

        # Assert
        result_text = textwrap.dedent("""\
            * NotEntry
            * DONE TodoEntry
              CLOSED: [{0}]
            * DONE CompletedEntry
              CLOSED: [{0}]
            * NotExtEntry
            ** NotExtNotIntEntry
            ** DONE NotExtTodoIntEntry
               CLOSED: [{0}]
            ** DONE NotExtCompletedIntEntry
               CLOSED: [{0}]
            * DONE TodoExtEntry
              CLOSED: [{0}]
            ** TodoExtNotIntEntry
            ** DONE TodoExtTodoIntEntry
               CLOSED: [{0}]
            ** DONE TodoExtCompletedIntEntry
               CLOSED: [{0}]
            * TODO NewTodoEntry
        """.format(self.now.to_org_format()))
        self.assertEqual(str(org_tree), result_text)


    def test_safemerge(self):

        # Arrange
        org_tree = m.TasksTree.parse_text("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
            * Headline B2
        """)

        remote_tree, indexes = tests.createTestTree([
            "Headline A1",
            " Headline A1.1",
            "Headline B1",
            " Headline B1.1", dict(notes=["Remote append B1.1 body text."]),
            "Headline A2", dict(todo=True),
            " Headline A2.1",
            "Headline B2 modified", dict(notes=["New B2 body text."])
        ])

        # Act
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline A1.1", None],
            ["Headline B2", "Headline B2 modified", "Headline B2 modified"],
        ]))

        # Assert
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

        # Arrange
        org_tree = m.TasksTree.parse_text("""\
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

        remote_tree, indexes = tests.createTestTree([
            "Headline B1", dict(completed=True,
                                closed_time=self.now),
            "Headline C", dict(completed=True,
                               closed_time=self.now),
            "Headline D", dict(todo=True),
            "Headline G", dict(todo=True),
        ])

        # Act
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline G", None],
        ]))

        # Assert
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
            """.format(self.now.to_org_format()))
        self.assertEqual(str(org_tree), result_text)


    def test_fast_merge(self):

        # Arrange
        org_tree = m.TasksTree.parse_text("""\
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
        """.format(self.now.to_org_format()))

        remote_tree, indexes = tests.createTestTree([
            "Headline B1", dict(completed=True,
                                closed_time=self.now),
            "Headline B2 modified", dict(todo=True),
            "Headline B3", dict(todo=True),
            "Headline C", dict(completed=True,
                               closed_time=self.now),
            "Headline D1", dict(todo=True),
            "Headline G", dict(todo=True),
            "Headline H", dict(completed=True,
                               closed_time=self.now),
        ])

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline G", None],
            [None, "Headline H", None],
            ["Headline B2", "Headline B2 modified", "Headline B2 modified"],
            ["Headline B3 original", "Headline B3", "Headline B3 original"],
        ]))

        # Assert
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
            """.format(self.now.to_org_format()))
        self.assertEqual(str(org_tree), result_text)


        self.assertEqual(len(remote_sync_plan), 7)

        # Headline B1
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[0])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline B2
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[1])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline B3
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[2])
        self.assertEqual(assertObj['action'], 'update')
        self.assertEqual(assertObj['changes'], ['title'])
        self.assertEqual(assertObj['item'].title, 'Headline B3 original')

        # Headline C
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[3])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline D1
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[4])
        self.assertEqual(assertObj['action'], 'remove')

        # Headline F
        assertObj = next(x for x in remote_sync_plan if x['item'].title == "Headline F")
        self.assertEqual(assertObj['action'], 'append')
        self.assertEqual(assertObj['item'].title, 'Headline F')

        # Headline H
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[6])
        self.assertEqual(assertObj['action'], 'remove')


    def test_sync_time(self):

        # Arrange
        org_tree = m.TasksTree.parse_text("""\
            * TODO Headline A
            * TODO Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
        """)

        remote_tree, indexes = tests.createTestTree([
            "Headline A", dict(todo=True,
                               schedule_time=m.OrgDate(datetime.date(2015, 12, 9))),
            "Headline B", dict(todo=True),
            "Headline C", dict(completed=True,
                               closed_time=self.now,
                               schedule_time=m.OrgDate(datetime.date(2015, 12, 9),
                                                       datetime.time(20, 0),
                                                       datetime.timedelta(hours=1))),
            "Headline D", dict(todo=True,
                               schedule_time=m.OrgDate(datetime.date(2015, 12, 9))),
        ])

        # Act
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf())

        # Assert
        result_text = textwrap.dedent("""\
            * TODO Headline A
              SCHEDULED: <2015-12-09 Wed>
            * TODO Headline B
            * DONE Headline C
              CLOSED: [{0}] SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            * TODO Headline D
              SCHEDULED: <2015-12-09 Wed>
            """.format(self.now.to_org_format()))
        self.assertEqual(str(org_tree), result_text)

    def test_3way_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text("""\
            * NotTodoTestTask
            * TitleMergeTest
            ** TODO TitleMergeTask1
            ** TODO TitleMergeTask2
            ** TODO TitleMergeTask3
            * ScheduleMergeTest
            * TODO ScheduleMergeTask1
              SCHEDULED: <2015-12-09 Wed>
            * TODO ScheduleMergeTask2
              SCHEDULED: <2015-12-09 Wed>
            * TODO ScheduleMergeTask3
              SCHEDULED: <2015-12-09 Wed>
        """.format(self.now.to_org_format()))

        org_tree = m.TasksTree.parse_text("""\
            * NotTodoTestTask
            * TitleMergeTest
            ** TODO TitleMergeTask1
            ** TODO TitleMergeTask2 org-edited
            ** TODO TitleMergeTask3
            * ScheduleMergeTest
            * TODO ScheduleMergeTask1
              SCHEDULED: <2015-12-09 Wed>
            * TODO ScheduleMergeTask2
              SCHEDULED: <2015-12-10 Thu>
            * TODO ScheduleMergeTask3
              SCHEDULED: <2015-12-09 Wed>
        """.format(self.now.to_org_format()))

        remote_tree, indexes = tests.createTestTree([
            "TitleMergeTask1", dict(todo=True),
            "TitleMergeTask2", dict(todo=True),
            "TitleMergeTask3 remote-edited", dict(todo=True),
            "ScheduleMergeTask1", dict(todo=True,
                                       schedule_time=m.OrgDate(datetime.date(2015, 12, 9))),
            "ScheduleMergeTask2", dict(todo=True,
                                       schedule_time=m.OrgDate(datetime.date(2015, 12, 9))),
            "ScheduleMergeTask3", dict(todo=True,
                                       schedule_time=m.OrgDate(datetime.date(2015, 12, 11)))
        ])

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            ["TitleMergeTask2 org-edited", "TitleMergeTask2", None],
            ["TitleMergeTask3", "TitleMergeTask3 remote-edited", None],
        ]))

        # Assert
        result_text = textwrap.dedent("""\
            * NotTodoTestTask
            * TitleMergeTest
            ** TODO TitleMergeTask1
            ** TODO TitleMergeTask2 org-edited
            ** TODO TitleMergeTask3 remote-edited
            * ScheduleMergeTest
            * TODO ScheduleMergeTask1
              SCHEDULED: <2015-12-09 Wed>
            * TODO ScheduleMergeTask2
              SCHEDULED: <2015-12-10 Thu>
            * TODO ScheduleMergeTask3
              SCHEDULED: <2015-12-11 Fri>
            """)
        self.assertEqual(str(org_tree), result_text)


        self.assertEqual(len(remote_sync_plan), 2)

        # TitleMergeTask2 org-edited
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[1])
        self.assertEqual(assertObj['action'], 'update')
        self.assertEqual(assertObj['changes'], ['title'])
        self.assertEqual(assertObj['item'].title, 'TitleMergeTask2 org-edited')

        # ScheduleMergeTask2
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[4])
        self.assertEqual(assertObj['action'], 'update')
        self.assertEqual(assertObj['changes'], ['schedule_time'])
        self.assertEqual(assertObj['item'].schedule_time,
                         m.OrgDate(datetime.date(2015, 12, 10)))


if __name__ == '__main__':
    unittest.main()
