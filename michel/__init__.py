#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
michel-orgmode -- a script to push/pull an org-mode text file to/from a google
                  tasks list.

"""

import codecs
import os.path
import shutil
import sys
import re
import io
import ipdb
import json
import locale

from michel.utils import *
from michel.gtasks import *
from michel.mergetask import *

MICHEL_PROFILE = ".michel-profile"
headline_regex = re.compile("^(\*+) *(DONE|TODO)? *(.*)")

        
def print_todolist(profile, list_name=None):
    """Print an orgmode-formatted string representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """
    tasks_tree = get_gtask_list_as_tasktree(profile, list_name)
    tasks_tree._print()

def write_todolist(orgfile_path, profile, list_name=None):
    """Create an orgmode-formatted file representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """
    tasks_tree = get_gtask_list_as_tasktree(profile, list_name)
    tasks_tree.write_to_orgfile(orgfile_path)

def erase_todolist(profile, list_id):
    """Erases the todo list of given id"""
    service = get_service(profile)
    tasks = service.tasks().list(tasklist=list_id).execute()
    for task in tasks.get('items', []):
        service.tasks().delete(tasklist=list_id,
                task=task['id']).execute()

def parse_path(path):
    """Parses an org-mode file and returns a tree"""
    file_lines = codecs.open(path, "r", "utf-8").readlines()
    file_text = "".join(file_lines)
    return parse_text_to_tree(file_text)
    
def parse_text_to_tree(text, remote = False):
    """Parses an org-mode formatted block of text and returns a tree"""
    # create a (read-only) file object containing *text*
    f = io.StringIO(text)
    
    tasks_tree = TasksTree(None)
    tasks_tree.remote = remote
    
    last_task = None
    task_stack = [tasks_tree]

    for line in f:
        line = line.strip()
        matches = headline_regex.findall(line)
        try:
            # assign task_depth; root depth starts at 0
            indent_level = len(matches[0][0])

            # add the task to the tree
            last_task = task_stack[indent_level - 1].add_subtask(matches[0][2])

            # expand if it is needed
            if (indent_level + 1) > len(task_stack):
                task_stack = [task_stack[x] if x < len(task_stack) else None
                              for x in range(indent_level + 1)]
                
            task_stack[indent_level] = last_task
            
            last_task.todo = matches[0][1] == 'DONE' or matches[0][1] == 'TODO'
            last_task.completed = matches[0][1] == 'DONE'

        except IndexError:
            # this is not a task, but a task-notes line
            
            if last_task is None:
                raise ValueError("Text without task is not permitted")

            last_task.notes.append(line)

    f.close()

    tasks_tree.parse_system_notes()
    return tasks_tree

def push_todolist(path, profile, list_name, only_todo):
    """Pushes the specified file to the specified todolist"""
    service = get_service(profile)
    list_id = get_list_id(service, list_name)
    tasks_tree = parse_path(path)
    erase_todolist(profile, list_id)
    push_tasktree(profile, list_name, tasks_tree, only_todo)

def sync_todolist(path, profile, list_name, only_todo):
    """Synchronizes the specified file with the specified todolist"""
    tree_remote = get_gtask_list_as_tasktree(profile, list_name)
    tree_org = parse_path(path)
    
    treemerge(tree_org, tree_remote)
    
    # write merged tree to tasklist
    service = get_service(profile)
    list_id = get_list_id(service, list_name)
    erase_todolist(profile, list_id)
    push_tasktree(profile, list_name, tree_org, only_todo)
        
    # write merged tree to orgfile
    codecs.open(path, "w", "utf-8").write(str(tree_org))


def main():
    parser = argparse.ArgumentParser(description="Synchronize org-mode text" 
                                     "files with a google-tasks list.")
    
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--push", action='store_true',
            help='replace LISTNAME with the contents of FILE.')
    action.add_argument("--pull", action='store_true',
            help='replace FILE with the contents of LISTNAME.')
    action.add_argument("--sync", action='store_true',
            help='synchronize changes between FILE and LISTNAME.')
    action.add_argument("--list", action='store_true',
            help='use action from list.')
    
    parser.add_argument("--todo", action='store_true',
            help='synchronize even not TODO tasks to remote.')
    
    parser.add_argument('--orgfile',
            metavar='FILE',
            help='An org-mode file to push from / pull to')
    # TODO: replace the --profile flag with a URL-like scheme for specifying
    # data sources. (e.g. using file:///path/to/orgfile or
    # gtasks://profile/listname, and having only --from and --to flags)
    parser.add_argument('--profile',
            default="__default",
            required=False,
            help='A user-defined profile name to distinguish between '
                 'different google accounts')
    parser.add_argument('--listname',
            help='A GTasks list to pull from / push to (default list if empty)')
    
    args = parser.parse_args()

    if not args.push and not args.sync and not args.pull:
        args.list = True
    
    if args.push and not args.orgfile:
        parser.error('--orgfile must be specified when using --push')
    if args.sync and not args.orgfile:
        parser.error('--orgfile must be specified when using --sync')
    if args.todo and not (args.push or args.sync):
        parser.error('--todo can be specified only with using --sync or --push')
    
    if args.pull:
        if args.orgfile is None:
            print_todolist(args.profile, args.listname)
        else:
            write_todolist(args.orgfile, args.profile, args.listname)
    elif args.push:
        if not os.path.exists(args.orgfile):
            print("The org-file you want to push does not exist.")
            sys.exit(2)
        push_todolist(args.orgfile, args.profile, args.listname, args.todo)
    elif args.sync:
        if not os.path.exists(args.orgfile):
            print("The org-file you want to synchronize does not exist.")
            sys.exit(2)
        sync_todolist(args.orgfile, args.profile, args.listname, args.todo)
    elif args.list:
        print("Use list of actions")
        with codecs.open(MICHEL_PROFILE, 'r', 'utf-8') as actions_file:
            actions = json.load(actions_file)
        for entry in actions:
            if entry['action'] == 'sync':
                print ("Sync {0} <-> {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                sync_todolist(entry['org_file'], entry['profile'], entry['listname'], entry['todo'])
            elif entry['action'] == 'push':
                print ("Push {0} -> {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                push_todolist(entry['org_file'], entry['profile'], entry['listname'], entry['todo'])
            elif entry['action'] == 'pull':
                print ("Pull {0} <- {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                write_todolist(entry['org_file'], entry['profile'], entry['listname'])
        
if __name__ == "__main__":
    main()

