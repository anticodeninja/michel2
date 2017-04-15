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
import json
import locale
import argparse

from michel.utils import *
from michel.mergetask import *
from michel.mergeconf import *
from michel.tasktree import *

def print_todolist(url):
    """Print an orgmode-formatted string representing a google tasks list.

    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.

    """

    provider = get_provider(url)
    provider.pull()
    print(provider.get_tasks())

def write_todolist(path, url):
    """Create an orgmode-formatted file representing a google tasks list.

    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.

    """

    path = os.path.expanduser(path)
    if not os.path.exists(path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)

    provider = get_provider(url)
    provider.pull()
    provider.get_tasks().write_file(path)

def push_todolist(org_path, profile, list_name, only_todo):
    """Pushes the specified file to the specified todolist"""

    org_path = os.path.expanduser(org_path)
    if not os.path.exists(org_path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)
    org_tree = TasksTree.parse_file(org_path)

    provider = get_provider(url)
    provider.erase()
    remote_tree = provider.get_tasks()

    sync_plan = treemerge(org_tree, remote_tree, None, InteractiveMergeConf(provider, only_todo))
    provider.sync(sync_plan)

def sync_todolist(org_path, url, only_todo):
    """Synchronizes the specified file with the specified todolist"""

    org_path = os.path.expanduser(org_path)
    if not os.path.exists(org_path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)
    org_tree = TasksTree.parse_file(org_path)

    provider = get_provider(url)
    provider.pull()
    remote_tree = provider.get_tasks()

    base_path = os.path.splitext(org_path)[0] + ".base"
    base_tree = TasksTree.parse_file(base_path) if os.path.exists(base_path) else None

    sync_plan = treemerge(org_tree, remote_tree, base_tree, InteractiveMergeConf(provider, only_todo))
    provider.sync(sync_plan)
    codecs.open(org_path, "w", "utf-8").write(str(org_tree))
    codecs.open(base_path, "w", "utf-8").write(str(org_tree))

def main():
    parser = argparse.ArgumentParser(description="Synchronize org-mode files with cloud.")

    subparsers = parser.add_subparsers(dest='command', title='commands')

    push_command = subparsers.add_parser('push', help='push the file to cloud.')
    push_command.add_argument('orgfile')
    push_command.add_argument('url')
    push_command.add_argument("--only_todo", action='store_true',
                              help='push only TODO tasks to cloud.')

    print_command = subparsers.add_parser('print', help='print list from cloud.')
    print_command.add_argument('url')

    pull_command = subparsers.add_parser('pull', help='pull the file from cloud.')
    pull_command.add_argument('orgfile')
    pull_command.add_argument('url')

    sync_command = subparsers.add_parser('sync', help='sync the file with cloud.')
    sync_command.add_argument('orgfile')
    sync_command.add_argument('url')
    sync_command.add_argument("--only_todo", action='store_true',
                              help='synchronize only TODO tasks with cloud.')

    run_command = subparsers.add_parser('run', help='run actions from script.')
    run_command.add_argument('script', nargs='?')

    args = parser.parse_args()

    if args.command == 'print':
        print_todolist(args.url)
    elif args.command == 'pull':
        write_todolist(args.orgfile, args.url)
    elif args.command == 'push':
        push_todolist(args.orgfile, args.url, args.only_todo)
    elif args.command == 'sync':
        sync_todolist(args.orgfile, args.url, args.only_todo)
    elif args.command == 'run' or not args.command:
        script_file = getattr(args, 'script', None) or save_data_path("profile")
        if not os.path.exists(script_file):
            print("The script file does not exist.")
            sys.exit(2)

        print("Use actions from script {0}".format(script_file))

        with codecs.open(script_file, 'r', 'utf-8') as actions_file:
            actions = json.load(actions_file)

        for entry in actions:
            if entry['action'] == 'sync':
                print ("Sync {0} <-> {1}".format(entry['org_file'], entry['url']))
                sync_todolist(entry['org_file'], entry['url'], entry['only_todo'])
            elif entry['action'] == 'push':
                print ("Push {0} -> {1}".format(entry['org_file'], entry['url']))
                push_todolist(entry['org_file'], entry['url'], entry['only_todo'])
            elif entry['action'] == 'pull':
                print ("Pull {0} <- {1}".format(entry['org_file'], entry['url']))
                write_todolist(entry['org_file'], entry['url'])

if __name__ == "__main__":
    main()
