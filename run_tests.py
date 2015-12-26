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

class TestMichel(unittest.TestCase):

    def getLocaleAlias(self, lang_code):
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

    def test_format_google_dates(self):
        self.assertEqual("2015-12-09T00:00:00Z",
                         m.to_google_date_format(
                             datetime.datetime(2015, 12, 9, 20, 00)))
        self.assertEqual("2015-11-18T00:00:00Z",
                         m.to_google_date_format(
                             datetime.datetime(2015, 11, 18)))
        self.assertEqual("2015-12-10T00:00:00Z",
                         m.to_google_date_format(
                             datetime.datetime(2015, 12, 10, 3, 25)))
                         

    def test_format_emacs_dates(self):
        import michel.utils as mu

        test_locale = self.getLocaleAlias('ru')
        if test_locale:
            mu.default_locale = test_locale
            self.assertEqual(
                "2015-12-09 Ср 20:00-21:00",
                m.to_emacs_date_format(
                    True,
                    datetime.datetime(2015, 12, 9, 20, 00),
                    datetime.datetime(2015, 12, 9, 21, 00)))

        test_locale = self.getLocaleAlias('us')
        if test_locale:
            mu.default_locale = test_locale
            self.assertEqual(
                "2015-11-18 Wed",
                m.to_emacs_date_format(
                    False,
                    datetime.datetime(2015, 11, 18)))

        test_locale = self.getLocaleAlias('de')
        if test_locale:
            mu.default_locale = test_locale
            self.assertEqual(
                "2015-12-10 Do 03:25",
                m.to_emacs_date_format(
                    True,
                    datetime.datetime(2015, 12, 10, 3, 25)))

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
        tasktree = m.TasksTree.parse_text(org_text, False)
        self.assertEqual(str(tasktree), result_text)

    @unittest.skipIf(os.name == 'nt', "unicode console is not supported")
    def test_unicode_print(self):
        """
        Test ability to print unicode text
        """
        
        tasks_tree = m.TasksTree(None)
        task = tasks_tree.add_subtask('السلام عليكم')
        task.notes = ['viele Grüße']

        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            print(tasks_tree)
        except UnicodeDecodeError:
            self.fail("TasksTree._print() raised UnicodeDecodeError")
        sys.stdout.close()
        sys.stdout = old_stdout

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
        remote_text = textwrap.dedent("""\
            * Headline A1
            ** Headline A1.1
            * Headline B1
            ** Headline B1.1
               Remote append B1.1 body text.
            * Headline A2
            ** Headline A2.1
            * Headline B2 modified
              New B2 body text.
            """)
        result_text = textwrap.dedent("""\
            * Headline A1
            ** Headline A1.1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
               Remote append B1.1 body text.
            * Headline B2 modified
              PREV_TITLE: Headline B2
              SYNC: New B2 body text.
            """)
        
        org_tree = m.TasksTree.parse_text(org_text, False)
        remote_tree = m.TasksTree.parse_text(remote_text, True)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

    def test_remerge_with_fixes(self):
        import michel.utils as mu
        mu.default_locale = self.getLocaleAlias('us')
        
        org_text = textwrap.dedent("""\
            * Headline A1
              Original text.
            * TODO Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            """)
        remote_text = textwrap.dedent("""\
            * Headline A1
              Original text.
              SYNC: Text which should be ignored
            * TODO Headline C
              PREV_TITLE: Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 19:00-20:00>
            """)
        result_text = textwrap.dedent("""\
            * Headline A1
              Original text.
            * TODO Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            """)
        
        org_tree = m.TasksTree.parse_text(org_text, False)
        remote_tree = m.TasksTree.parse_text(remote_text, True)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

    def test_remerge_without_fixes(self):
        import michel.utils as mu
        mu.default_locale = self.getLocaleAlias('us')
        
        remote_text = textwrap.dedent("""\
            * Headline A1
              Original text.
              Text which should be ignored
            * TODO Headline C
              PREV_TITLE: Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 19:00-20:00>
            """)
        org_text = remote_text
        result_text = remote_text
        
        org_tree = m.TasksTree.parse_text(org_text, False)
        remote_tree = m.TasksTree.parse_text(remote_text, True)
        m.treemerge(org_tree, remote_tree)
        
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
        remote_text = textwrap.dedent("""\
            * DONE Headline B1
            * DONE Headline C
            * TODO Headline D
            * TODO Headline G
            """)
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
        
        org_tree = m.TasksTree.parse_text(org_text, False)
        remote_tree = m.TasksTree.parse_text(remote_text, True)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

    def test_scheduled_and_closed_time(self):
        import michel.utils as mu
        mu.default_locale = self.getLocaleAlias('us')
        
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
        tasktree = m.TasksTree.parse_text(org_text, False)
        
        self.assertEqual(tasktree[0].closed_time, None)
        self.assertEqual(tasktree[0].scheduled_start_time, None)
        self.assertEqual(tasktree[0].scheduled_end_time, None)
        self.assertFalse(tasktree[0].scheduled_has_time)

        self.assertEqual(tasktree[1].closed_time, None)
        self.assertEqual(tasktree[1].scheduled_start_time, datetime.datetime(2015, 11, 18, 0, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(tasktree[1].scheduled_end_time, None)
        self.assertEqual(m.to_google_date_format(tasktree[1].scheduled_start_time), "2015-11-18T00:00:00Z")
        self.assertFalse(tasktree[1].scheduled_has_time)

        self.assertEqual(tasktree[2].closed_time, None)
        self.assertEqual(tasktree[2].scheduled_start_time, datetime.datetime(2015, 12, 9, 19, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(tasktree[2].scheduled_end_time, datetime.datetime(2015, 12, 9, 20, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(m.to_google_date_format(tasktree[2].scheduled_start_time), "2015-12-09T00:00:00Z")
        self.assertTrue(tasktree[2].scheduled_has_time)

        self.assertEqual(tasktree[3].closed_time, datetime.datetime(2015, 12, 10, 3, 25, tzinfo = m.LocalTzInfo()))
        self.assertEqual(tasktree[3].scheduled_start_time, None)
        self.assertEqual(tasktree[3].scheduled_end_time, None)
        self.assertFalse(tasktree[3].scheduled_has_time)

        self.assertEqual(tasktree[4].closed_time, datetime.datetime(2015, 12, 10, 3, 25, tzinfo = m.LocalTzInfo()))
        self.assertEqual(tasktree[4].scheduled_start_time, datetime.datetime(2015, 12, 9, 3, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(tasktree[4].scheduled_end_time, None)
        self.assertEqual(m.to_google_date_format(tasktree[4].scheduled_start_time), "2015-12-09T00:00:00Z")
        self.assertTrue(tasktree[4].scheduled_has_time)
                         
        self.assertEqual(str(tasktree), org_text)

    def test_sync_time(self):
        import michel.utils as mu
        mu.default_locale = self.getLocaleAlias('us')
        
        org_text = textwrap.dedent("""\
            * TODO Headline A
            * TODO Headline B
            * TODO Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            """)
        remote_text = textwrap.dedent("""\
            * TODO Headline A
              SCHEDULED: <2015-12-09 Wed>
            * TODO Headline B
            * DONE Headline C
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            * TODO Headline D
              SCHEDULED: <2015-12-09 Wed>
            """)
        
        result_text = textwrap.dedent("""\
            * TODO Headline A
              SCHEDULED: <2015-12-09 Wed>
            * TODO Headline B
            * DONE Headline C
              CLOSED: [{0}] SCHEDULED: <2015-12-09 Wed 20:00-21:00>
            * TODO Headline D
              SCHEDULED: <2015-12-09 Wed>
            """.format(m.to_emacs_date_format(True, datetime.datetime.now())))
        
        org_tree = m.TasksTree.parse_text(org_text, False)
        remote_tree = m.TasksTree.parse_text(remote_text, False)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)
        
    def test_parsing_special_comments(self):
        m.default_locale = locale.locale_alias['ru']
        
        org_text = textwrap.dedent("""\
            * TODO Headline B
              PREV_TITLE: Headline A
              SYNC: Text which should be ignored
              SCHEDULED: <2015-12-09 Wed 20:00-21:00>
              Normal note
            """)
        
        org_tree = m.TasksTree.parse_text(org_text, False)

        self.assertEqual(len(org_tree), 1)
        self.assertEqual(org_tree[0].title, "Headline B")
        self.assertEqual(org_tree[0].prev_title, "Headline A")
        self.assertTrue(org_tree[0].scheduled_has_time)
        self.assertEqual(org_tree[0].scheduled_start_time, datetime.datetime(2015, 12, 9, 20, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(org_tree[0].scheduled_end_time, datetime.datetime(2015, 12, 9, 21, 0, tzinfo = m.LocalTzInfo()))
        self.assertEqual(org_tree[0].notes, [
            "SYNC: Text which should be ignored",
            "Normal note"])

        org_tree = m.TasksTree.parse_text(org_text, True)

        self.assertEqual(len(org_tree), 1)
        self.assertEqual(org_tree[0].title, "Headline B")
        self.assertEqual(org_tree[0].prev_title, "Headline A")
        self.assertFalse(org_tree[0].scheduled_has_time)
        self.assertIsNone(org_tree[0].scheduled_start_time)
        self.assertIsNone(org_tree[0].scheduled_end_time)
        self.assertEqual(org_tree[0].notes, ["Normal note"])

if __name__ == '__main__':
    unittest.main()
