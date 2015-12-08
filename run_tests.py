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
    def setUp(self):
        pass
    def test_text_to_tasktree(self):
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\
            * Headline 1
            Body 1a
                Body 1b
            * DONE    Headline 2
            ** Headline 2.1
            """)
        tasktree = m.parse_text_to_tree(org_text)
        self.assertEqual(str(tasktree), org_text)

    def test_unicode_print(self):
        """
        Test ability to print unicode text
        """
        unicode_task = {
            u'status': u'needsAction',
            u'kind': u'tasks#task',
            u'title': u'السلام عليكم',
            u'notes': u'viele Grüße',
            u'id': u'ABC123',
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
            u'status': u'needsAction',
            u'kind': u'tasks#task',
            u'title': u'السلام عليكم',
            u'notes': u'viele Grüße',
            u'id': u'ABC123',
            }
        tasks_tree = m.tasklist_to_tasktree([unicode_task])

        fname = tempfile.NamedTemporaryFile().name
        try:
            tasks_tree.write_to_orgfile(fname)
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

        tasktree = m.parse_text_to_tree(org_text)
        # a dummy headline will be added to contain the initial text
        self.assertEqual(str(tasktree), "* \n" + org_text)

    def test_no_headlines(self):
        """
        Test the cases where there are no headlines at all in the file.
        
        """
        # text should have trailing "\n" character, like most textfiles
        org_text1 = textwrap.dedent("""\

            Some non-headline text...
            Another line of it.
            """)
        org_text2 = "" # empty file

        for org_text in [org_text1, org_text2]:
            tasktree = m.parse_text_to_tree(org_text)
            # a dummy headline will be added to contain the initial text
            self.assertEqual(str(tasktree), "* \n" + org_text)

    def test_add_subtrees(self):
        org_text1 = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            """)
        org_text2 = textwrap.dedent("""\
            * Headline B1
            ** Headline B1.1
            * Headline B2
            """)
        tree1 = m.parse_text_to_tree(org_text1)
        tree2 = m.parse_text_to_tree(org_text2)
        
        # test tree concatenation
        target_tree = m.concatenate_trees(tree1, tree2)
        target_text = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
            * Headline B2
            """)
        self.assertEqual(str(target_tree), target_text)
        
        # test subtree grafting
        # add tree2's children to first child of tree1
        tree1[0].add_subtree(tree2)
        target_tree = tree1
        target_text = textwrap.dedent("""\
            * Headline A1
            ** Headline B1
            *** Headline B1.1
            ** Headline B2
            * Headline A2
            ** Headline A2.1
            """)
        self.assertEqual(str(target_tree), target_text)
        
    def test_merge(self):
        org_text = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
               Remote append B1.1 body text.
            * Headline B2
            * TODO Headline C
            * TODO Headline D
            """)
        remote_text = textwrap.dedent("""\
            * Headline A1
            ** Headline A1.1
            * Headline B1
            ** Headline B1.1
               REMOTE_APPEND_NOTE: Remote append B1.1 body text.
            * Headline A2
            ** Headline A2.1
            * Headline B2 modified
              New B2 body text.
            * TODO Headline D
              PREV_ORG_TITLE: Headline C
            * TODO Headline D
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
            * TODO Headline C
            * TODO Headline D
            """)
        
        org_tree = m.parse_text_to_tree(org_text)
        remote_tree = m.parse_text_to_tree(remote_text)
        m.treemerge(org_tree, remote_tree)

        print(result_text)
        print(str(org_tree))
        
        self.assertEqual(str(org_tree), result_text)

if __name__ == '__main__':
    unittest.main()
