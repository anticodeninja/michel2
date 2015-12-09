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
import michel.michel as m

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
        tasktree = m.parse_text_to_tree(org_text)
        self.assertEqual(str(tasktree), result_text)

    def test_unicode_print(self):
        """
        Test ability to print unicode text
        """

        if os.name == 'nt':
            return
        
        unicode_task = {
            'status': 'needsAction',
            'kind': 'tasks#task',
            'title': 'السلام عليكم',
            'notes': 'viele Grüße',
            'id': 'ABC123',
        }
        tasks_tree = m.tasklist_to_tasktree([unicode_task])

        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            tasks_tree._print()
        except UnicodeDecodeError:
            self.fail("TasksTree._print() raised UnicodeDecodeError")
        sys.stdout = old_stdout

    def test_unicode_dump_to_file(self):
        """
        Test ability to pull unicode text into orgfile
        """
        unicode_task = {
            'status': 'needsAction',
            'kind': 'tasks#task',
            'title': 'السلام عليكم',
            'notes': 'viele Grüße',
            'id': 'ABC123',
        }
        tasks_tree = m.tasklist_to_tasktree([unicode_task])

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file_name = temp_file.name
            
        try:
            tasks_tree.write_to_orgfile(temp_file_name)
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

        self.assertRaises(ValueError, m.parse_text_to_tree, org_text)

    def test_no_headlines(self):
        """
        Test the cases where there are no headlines at all in the file.
        
        """
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\

            Some non-headline text...
            Another line of it.
            """)

        self.assertRaises(ValueError, m.parse_text_to_tree, org_text)

    def test_empty_file(self):
        org_text = "" # empty file
        m.parse_text_to_tree(org_text)
        
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
              PREV_ORG_TITLE: Headline B2
              REMOTE_APPEND_NOTE: New B2 body text.
            """)
        
        org_tree = m.parse_text_to_tree(org_text)
        remote_tree = m.parse_text_to_tree(remote_text)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

    def test_remerge_with_fixes(self):
        org_text = textwrap.dedent("""\
            * Headline A1
              Original text.
            * TODO Headline B
            * TODO Headline C
            """)
        remote_text = textwrap.dedent("""\
            * Headline A1
              Original text.
              REMOTE_APPEND_NOTE: Text which should be ignored
            * TODO Headline C
              PREV_ORG_TITLE: Headline B
            * TODO Headline C
            """)
        result_text = textwrap.dedent("""\
            * Headline A1
              Original text.
            * TODO Headline B
            * TODO Headline C
            """)
        
        org_tree = m.parse_text_to_tree(org_text)
        remote_tree = m.parse_text_to_tree(remote_text)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

    def test_remerge_without_fixes(self):
        remote_text = textwrap.dedent("""\
            * Headline A1
              Original text.
              REMOTE_APPEND_NOTE: Text which should be ignored
            * TODO Headline C
              PREV_ORG_TITLE: Headline B
            * TODO Headline C
            """)
        org_text = remote_text
        result_text = remote_text
        
        org_tree = m.parse_text_to_tree(org_text)
        remote_tree = m.parse_text_to_tree(remote_text)
        m.treemerge(org_tree, remote_tree)
        
        self.assertEqual(str(org_tree), result_text)

if __name__ == '__main__':
    unittest.main()
