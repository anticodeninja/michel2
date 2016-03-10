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

from michel.utils import *
from michel.gtasks import *
from michel.mergetask import *
from michel.mergeconf import *

MICHEL_PROFILE = ".michel-profile"
        
def print_todolist(profile, list_name=None):
    """Print an orgmode-formatted string representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """

    gtask_provider = GTaskProvider(profile, list_name)
    gtask_provider.pull()
    print(gtask_provider.get_tasks())

def write_todolist(orgfile_path, profile, list_name=None):
    """Create an orgmode-formatted file representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """

    gtask_provider = GTaskProvider(profile, list_name)
    gtask_provider.pull()
    gtask_provider.get_tasks().write_file(orgfile_path)

def push_todolist(path, profile, list_name, only_todo):
    """Pushes the specified file to the specified todolist"""

    gtask_provider = GTaskProvider(profile, list_name, only_todo)
    gtask_provider.set_tasks(TasksTree.parse_file(path))
    gtask_provider.push()

def sync_todolist(path, profile, list_name, only_todo):
    """Synchronizes the specified file with the specified todolist"""

    gtask_provider = GTaskProvider(profile, list_name, only_todo)
    gtask_provider.pull()
    tree_org = TasksTree.parse_file(path)
    
    sync_plan = treemerge(tree_org, gtask_provider.get_tasks(), InteractiveMergeConf(only_todo))
    gtask_provider.sync(sync_plan)
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
    
    parser.add_argument("--only_todo", action='store_true',
            help='synchronize only TODO tasks to remote.')
    
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
    if args.only_todo and not (args.push or args.sync):
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
        push_todolist(args.orgfile, args.profile, args.listname, args.only_todo)
    elif args.sync:
        if not os.path.exists(args.orgfile):
            print("The org-file you want to synchronize does not exist.")
            sys.exit(2)
        sync_todolist(args.orgfile, args.profile, args.listname, args.only_todo)
    elif args.list:
        print("Use list of actions")
        with codecs.open(MICHEL_PROFILE, 'r', 'utf-8') as actions_file:
            actions = json.load(actions_file)
        for entry in actions:
            if entry['action'] == 'sync':
                print ("Sync {0} <-> {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                sync_todolist(entry['org_file'], entry['profile'], entry['listname'], entry['only_todo'])
            elif entry['action'] == 'push':
                print ("Push {0} -> {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                push_todolist(entry['org_file'], entry['profile'], entry['listname'], entry['only_todo'])
            elif entry['action'] == 'pull':
                print ("Pull {0} <- {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                write_todolist(entry['org_file'], entry['profile'], entry['listname'])
        
if __name__ == "__main__":
    main()

