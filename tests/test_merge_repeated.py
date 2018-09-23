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

class MergeRepeatedTests(unittest.TestCase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.now = m.OrgDate.now()
        m.OrgDate.default_locale = tests.getLocaleAlias('us')


    def __gen_org(self, *days):
        temp = []
        if 1 in days: temp += ["* TODO RepeatedTask","  SCHEDULED: <2015-12-01 Tue>"]
        if 3 in days: temp += ["* TODO RepeatedTask","  SCHEDULED: <2015-12-03 Thu>"]
        if 5 in days: temp += ["* TODO RepeatedTask","  SCHEDULED: <2015-12-05 Sat>"]
        return "\n".join(temp + [""])


    def __gen_remote(self, *days):
        temp = []
        if 1 in days: temp += ["RepeatedTask",
                               dict(todo=True, schedule_time=m.OrgDate(datetime.date(2015, 12, 1)))]
        if 3 in days: temp += ["RepeatedTask",
                               dict(todo=True, schedule_time=m.OrgDate(datetime.date(2015, 12, 3)))]
        if 5 in days: temp += ["RepeatedTask",
                               dict(todo=True, schedule_time=m.OrgDate(datetime.date(2015, 12, 5)))]
        return temp


    def test_repeated_scheduled_task_new_remote_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(3))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(3,5))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(3,5))
        self.assertEqual(len(remote_sync_plan), 0)


    def test_repeated_scheduled_task_new_remote_addin_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(1,3,5))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(1,3,5))
        self.assertEqual(len(remote_sync_plan), 0)


    def test_repeated_scheduled_task_new_org_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(3,5))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(3))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(3,5))
        self.assertEqual(len(remote_sync_plan), 1)

        # Add RepeatedTask <2015-12-5 Fri>
        assertObj = next(x for x in remote_sync_plan if x['item'] not in indexes)
        self.assertEqual(assertObj['action'], 'append')


    def test_repeated_scheduled_task_new_org_addin_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(1,3,5))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(1,3))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(1,3,5))
        self.assertEqual(len(remote_sync_plan), 1)

        # Add RepeatedTask <2015-12-5 Fri>
        assertObj = next(x for x in remote_sync_plan if x['item'] not in indexes)
        self.assertEqual(assertObj['action'], 'append')


    def test_repeated_scheduled_task_reschedule_org_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(1,5))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(1,3))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(1,5))
        self.assertEqual(len(remote_sync_plan), 1)

        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[1])
        self.assertEqual(assertObj['action'], 'update')
        self.assertEqual(assertObj['changes'], ['schedule_time'])


    def test_repeated_scheduled_task_reschedule_remote_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        org_tree = m.TasksTree.parse_text(self.__gen_org(1,3))
        remote_tree, indexes = tests.createTestTree(self.__gen_remote(1,5))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        self.assertEqual(str(org_tree), self.__gen_org(1,5))
        self.assertEqual(len(remote_sync_plan), 0)


    def test_repeated_scheduled_task_reschedule_new_merge(self):

        # Arrange
        base_tree = m.TasksTree.parse_text(self.__gen_org(1))

        org_tree = m.TasksTree.parse_text("""\
            * DONE RepeatedTask
              CLOSED: [2015-12-01 Tue] SCHEDULED: <2015-12-01 Tue>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-03 Sat>
        """)

        remote_tree, indexes = tests.createTestTree(self.__gen_remote(1))

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf([
            [None, "RepeatedTask", None]
        ]))

        # Assert
        result_text = textwrap.dedent("""\
            * DONE RepeatedTask
              CLOSED: [2015-12-01 Tue] SCHEDULED: <2015-12-01 Tue>
            * TODO RepeatedTask
              SCHEDULED: <2015-12-03 Thu>
            """)
        self.assertEqual(str(org_tree), result_text)
        self.assertEqual(len(remote_sync_plan), 2)

        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[0])
        self.assertEqual(assertObj['action'], 'remove')

        assertObj = next(x for x in remote_sync_plan if x['item'] not in indexes)
        self.assertEqual(assertObj['action'], 'append')

    def test_repeated_scheduled_one_day_issue(self):

        # Arrange
        base_tree = m.TasksTree.parse_text("""\
            * TODO RepeatedTask
              SCHEDULED: <2018-09-17 Mon>
            * TODO RepeatedTask
              SCHEDULED: <2018-10-08 Mon>
        """)

        org_tree = m.TasksTree.parse_text("""\
            * TODO RepeatedTask
              SCHEDULED: <2018-10-08 Mon>
            * TODO RepeatedTask
              SCHEDULED: <2018-10-08 Mon>
        """)

        remote_tree, indexes = tests.createTestTree([
            "RepeatedTask",
            dict(todo=True, schedule_time=m.OrgDate(datetime.date(2018, 9, 17))),
            "RepeatedTask",
            dict(todo=True, schedule_time=m.OrgDate(datetime.date(2018, 10, 8))),
        ])

        # Act
        remote_sync_plan = m.treemerge(org_tree, remote_tree, base_tree, tests.TestMergeConf())

        # Assert
        result_text = textwrap.dedent("""\
            * TODO RepeatedTask
              SCHEDULED: <2018-10-08 Mon>
            * TODO RepeatedTask
              SCHEDULED: <2018-10-08 Mon>
            """)
        self.assertEqual(str(org_tree), result_text)
        self.assertEqual(len(remote_sync_plan), 1)

        assertObj = next(x for x in remote_sync_plan if x['item'] == indexes[0])
        self.assertEqual(assertObj['action'], 'update')



if __name__ == '__main__':
    unittest.main()

