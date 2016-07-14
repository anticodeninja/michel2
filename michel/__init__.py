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
        
def print_todolist(profile, list_name=None):
    """Print an orgmode-formatted string representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """

    gtask_provider = GTaskProvider(profile, list_name)
    gtask_provider.pull()
    print(gtask_provider.get_tasks())

def write_todolist(path, profile, list_name=None):
    """Create an orgmode-formatted file representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """

    path = os.path.expanduser(path)
    if not os.path.exists(path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)

    gtask_provider = GTaskProvider(profile, list_name)
    gtask_provider.pull()
    gtask_provider.get_tasks().write_file(path)

def push_todolist(path, profile, list_name, only_todo):
    """Pushes the specified file to the specified todolist"""

    path = os.path.expanduser(path)
    if not os.path.exists(path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)

    gtask_provider = GTaskProvider(profile, list_name, only_todo)
    gtask_provider.set_tasks(TasksTree.parse_file(path))
    gtask_provider.push()

def sync_todolist(path, profile, list_name, only_todo):
    """Synchronizes the specified file with the specified todolist"""

    path = os.path.expanduser(path)
    if not os.path.exists(path):
        print("The org-file you want to synchronize does not exist.")
        sys.exit(2)

    gtask_provider = GTaskProvider(profile, list_name, only_todo)
    gtask_provider.pull()
    tree_org = TasksTree.parse_file(path)
    
    sync_plan = treemerge(tree_org, gtask_provider.get_tasks(), InteractiveMergeConf(gtask_provider))
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
    action.add_argument("--script", action='store_true',
            help='use action from script.')
    
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
        args.script = True
    
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
        push_todolist(args.orgfile, args.profile, args.listname, args.only_todo)
    elif args.sync:
        sync_todolist(args.orgfile, args.profile, args.listname, args.only_todo)
    elif args.script:
        try:
            scripts = [".michel-profile", save_data_path("profile")]
            script_file = next(x for x in scripts if os.path.exists(x))
        except:
            print("The script file does not exist.")
            sys.exit(2)

        print("Use actions from script {0}".format(script_file))
            
        with codecs.open(script_file, 'r', 'utf-8') as actions_file:
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

