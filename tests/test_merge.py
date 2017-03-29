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
import tests

class TestMichel(unittest.TestCase):

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
        # Preparations
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

        # Actions
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "NewTodoEntry", None]
        ]))

        # Verifications
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
        # Preparations
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

        # Actions
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline A1.1", None],
            ["Headline B2", "Headline B2 modified", "Headline B2 modified"],
        ]))

        # Verifications
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
        # Preparations
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

        # Actions
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline G", None],
        ]))

        # Verifications
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
        # Preparations
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

        # Actions
        remote_sync_plan = m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf([
            [None, "Headline G", None],
            [None, "Headline H", None],
            ["Headline B2", "Headline B2 modified", "Headline B2 modified"],
            ["Headline B3 original", "Headline B3", "Headline B3 original"],
        ]))

        # Verifications
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
        # Preparations
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

        # Actions
        m.treemerge(org_tree, remote_tree, None, tests.TestMergeConf())

        # Verifications
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
        # Preparations
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

        # Actions
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            ["TitleMergeTask2 org-edited", "TitleMergeTask2", None],
            ["TitleMergeTask3", "TitleMergeTask3 remote-edited", None],
        ]))


        # Verifications
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

    def test_repeated_task_merge(self):
        # Preparations
        base_tree = m.TasksTree.parse_text("""\
            * TODO RepeatedTask
              SCHEDULED: <2015-12-09 Wed>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-10 Thu>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-12 Sat>
        """)

        org_tree = m.TasksTree.parse_text("""\
            * TODO RepeatedTask
              SCHEDULED: <2015-12-09 Wed>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-10 Thu>
            * DONE RepeatedTask
              CLOSED: [2015-12-12 Sat] SCHEDULED: <2015-12-12 Sat>
        """)

        remote_tree, indexes = tests.createTestTree([
            "RepeatedTask", dict(completed=True,
                                 closed_time=m.OrgDate(datetime.date(2015, 12, 11)),
                                 schedule_time=m.OrgDate(datetime.date(2015, 12, 11))),
            "RepeatedTask", dict(todo=True,
                                 schedule_time=m.OrgDate(datetime.date(2015, 12, 9))),
            "RepeatedTask", dict(todo=True,
                                 schedule_time=m.OrgDate(datetime.date(2015, 12, 12))),
            "RepeatedTask", dict(todo=True,
                                 schedule_time=m.OrgDate(datetime.date(2015, 12, 14))),
        ])

        # Actions
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf())

        # Verifications
        result_text = textwrap.dedent("""\
            * TODO RepeatedTask
              SCHEDULED: <2015-12-09 Wed>
            * DONE RepeatedTask
              CLOSED: [2015-12-11 Fri] SCHEDULED: <2015-12-11 Fri>
            * DONE RepeatedTask
              CLOSED: [2015-12-12 Sat] SCHEDULED: <2015-12-12 Sat>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-14 Mon>
            """)
        self.assertEqual(str(org_tree), result_text)


        self.assertEqual(len(remote_sync_plan), 2)

        # Remove RepeatedTask <2015-12-11 Fri>
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[0])
        self.assertEqual(assertObj['action'], 'remove')

        # Remove RepeatedTask <2015-12-12 Sat>
        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[2])
        self.assertEqual(assertObj['action'], 'remove')


if __name__ == '__main__':
    unittest.main()
