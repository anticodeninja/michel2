#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
michel-orgmode -- a script to push/pull an org-mode text file to/from a google
                  tasks list.

"""

import httplib2

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from difflib import SequenceMatcher
import codecs
import argparse
import os.path
import shutil
import sys
import re
import io
import datetime
import time
import ipdb
import json

RATIO_THRESHOLD = 0.85
MICHEL_PROFILE = ".michel-profile"

headline_regex = re.compile("^(\*+) *(DONE|TODO)? *(.*)")
spec_re = re.compile("([^.]+): (.+)")
spec_notes = re.compile("(?:CLOSED: \[(.*)\]|(?:SCHEDULED: <(.*)>) *)+")
time_regex = re.compile("(\d+)-(\d+)-(\d+) \S+(?: (\d+):(\d+)(?:-(\d+):(\d+))?)?")

class LocalTzInfo(datetime.tzinfo):
    _offset = datetime.timedelta(seconds = time.timezone)
    _dst = datetime.timedelta(seconds = time.daylight)
    _name = time.tzname
    def utcoffset(self, dt):
        return self.__class__._offset
    def dst(self, dt):
        return self.__class__._dst
    def tzname(self, dt):
        return self.__class__._name

class TasksTree(object):
    """
    Tree for holding tasks

    A TasksTree:
    - is a task (except the root, which just holds the list)
    - has subtasks
    - may have a task_id
    - may have a title
    """

    def __init__(self, title=None, task_id=None, task_notes=None, task_todo=False, task_completed=False):
        self.title = title
        self.task_id = task_id
        self.subtasks = []
        self.notes = task_notes or []
        self.todo = task_todo
        self.completed = task_completed
        self.closed_time = None
        self.scheduled_start_time = None
        self.scheduled_end_time = None
        
    def __getitem__(self, key):
        return self.subtasks[key]
         
    def __setitem__(self, key, val):
        self.subtasks[key] = val
        
    def __delitem__(self, key):
        del(self.subtasks[key])

    def __len__(self):
        return len(self.subtasks)

    def get_task_with_id(self, task_id):
        """Returns the task of given id"""
        if self.task_id == task_id:
            return self
        else:
            # depth first search for id
            for subtask in self.subtasks:
                if subtask.get_task_with_id(task_id) is not None:
                    return subtask.get_task_with_id(task_id)
            # if there are no subtasks to search
            return None

    def add_subtask(self, title, task_id = None, parent_id = None,
                    task_notes = None, task_todo = False, task_completed = False):
        """
        Adds a subtask to the tree
        - with the specified task_id
        - as a child of parent_id
        """
        if parent_id is None:
            task = TasksTree(title, task_id, task_notes, task_todo, task_completed)
            self.subtasks.append(task)
            return task
        else:
            if self.get_task_with_id(parent_id) is None:
                raise ValueError("No element with suitable parent id")
            
            return self.get_task_with_id(parent_id).add_subtask(title, task_id, None,
                                                         task_notes, task_todo, task_completed)

    def last_task_node_at_level(self, level):
        """Return the last task added at a given level of the tree.
        
        Level 0 is the "root" node of the tree, and there is only one node at
        this level, which contains all of the level 1 nodes (tasks/headlines).
        
        A TaskTree object is returned that corresponds to the last task having
        the specified level.  This TaskTree object will have the last task as
        the root node of the tree, and will maintain all of the node's
        descendants.
        
        """
        if level == 0:
            return self
        else:
            res = None
            for subtask in self.subtasks:
                x = subtask.last_task_node_at_level(level - 1)
                if x is not None:
                    res = x
            if res is not None:
                return res

    def push(self, service, list_id, only_todo, parent = None, root=True):
        """Pushes the task tree to the given list"""
        # We do not want to push the root node
        if not root and (not only_todo or (self.todo and not self.completed)):
            insert_cmd_args = {
                'tasklist': list_id,
                'body': {
                    'title': self.title,
                    'notes': '\n'.join(self.notes),
                    'status': 'completed' if self.completed else 'needsAction'
                }
            }
            if parent:
                insert_cmd_args['parent'] = parent
            if self.scheduled_start_time is not None:
                insert_cmd_args['body']['due'] = self.scheduled_start_time.astimezone().isoformat()
            res = service.tasks().insert(**insert_cmd_args).execute()
            self.task_id = res['id']
        # the API head inserts, so we insert in reverse.
        for subtask in reversed(self.subtasks):
            subtask.push(service, list_id, only_todo, parent=self.task_id, root=False)

    def normalize_todo(self):
        for subtask in self.subtasks:
            subtask_todo, subtask_completed = subtask.normalize_todo()
            self.todo = self.todo or subtask_todo
            if subtask_todo:
                self.completed = self.completed and subtask_completed

        return self.todo, self.completed
                

    def _lines(self, level):
        """Returns the sequence of lines of the string representation"""
        res = []
        
        for subtask in self.subtasks:
            task_line = ['*' * (level + 1)]
            if subtask.completed:
                task_line.append('DONE')
            elif subtask.todo:
                task_line.append('TODO')
            task_line.append(subtask.title)
                
            res.append(' '.join(task_line))

            for note_line in subtask.notes:
                # add initial space to lines starting w/'*', so that it isn't treated as a task
                if note_line.startswith("*"):
                    note_line = " " + note_line
                note_line = ' ' * (level + 2) + note_line
                res.append(note_line)
                
            res += subtask._lines(level + 1)
            
        return res


    def __str__(self):
        """string representation of the tree.
        
        Only the root-node's children (and their descendents...) are printed,
        not the root-node itself.
        
        """
        # always add a trailing "\n" because text-files normally include a "\n"
        # at the end of the last line of the file.
        return '\n'.join(self._lines(0)) + "\n"

    def _print(self):
        print(self.__str__())

    def write_to_orgfile(self, fname):
        f = codecs.open(fname, "w", "utf-8")
        f.write(self.__str__())
        f.close()

def save_data_path(file_name):
    data_path = os.path.join(os.path.expanduser('~'), ".michel")
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    return os.path.join(data_path, file_name)
        
def treemerge(tree_org, tree_remote):
    tasks_org = []
    tasks_remote = []

    disassemble_tree(tree_org, tasks_org)
    disassemble_tree(tree_remote, tasks_remote)

    tasks_org.sort(key=lambda node: node.hash_sum)
    tasks_remote.sort(key=lambda node: node.hash_sum)

    mapping = []

    # first step, exact matching
    index_remote, index_org = 0, 0
    while index_remote < len(tasks_remote):
        is_mapped = False
        index_org = 0
        
        while index_org < len(tasks_org):
            if tasks_remote[index_remote].is_equal(tasks_org[index_org]):
                mapping.append(tuple([tasks_remote.pop(index_remote), tasks_org.pop(index_org), True]))
                is_mapped = True
                break
            else:
                index_org += 1

        if not is_mapped:
            index_remote += 1

    # second step, fuzzy matching
    index_remote, index_org = 0, 0
    while index_remote < len(tasks_remote):
        index_org = 0
        best_index_org = None
        best_ratio = RATIO_THRESHOLD
        
        while index_org < len(tasks_org):
            ratio = tasks_org[index_org].calc_ratio(tasks_remote[index_remote])
            if ratio > best_ratio:
                best_ratio = ratio
                best_index_org = index_org
            index_org += 1

        if best_index_org is not None:
            mapping.append(tuple([tasks_remote.pop(index_remote), tasks_org.pop(best_index_org), False]))
        else:
            index_remote += 1

    # third step, patching org tree
    for map_entry in mapping:
        diff_notes = []

        # Merge attributes
        if map_entry[0].task.completed == True and map_entry[1].task.completed != True:
            map_entry[1].task.completed = True

        # Merge contents
        if map_entry[0].task.title != map_entry[1].task.title:
            if map_entry[1].task.title not in map_entry[0].titles:
                diff_notes.append("PREV_ORG_TITLE: {0}".format(map_entry[1].task.title))
                map_entry[1].task.title = map_entry[0].task.title

        if map_entry[0].task.notes != map_entry[1].task.notes:
            for note_line in map_entry[0].task.notes:
                matches = spec_re.findall(note_line)
                if len(matches) > 0:
                    if matches[0][0] == "PREV_ORG_TITLE" or \
                       matches[0][0] == "REMOTE_APPEND_NOTE":
                        continue
                    
                matches = time_regex.findall(note_line)
                if len(matches) > 0:
                    continue
                    
                if note_line not in map_entry[1].task.notes:
                    diff_notes.append("REMOTE_APPEND_NOTE: {0}".format(note_line))

        map_entry[1].task.notes += diff_notes

    # fourth step, append new items
    for i in range(len(tasks_remote)):
        new_task = tasks_remote[i]

        try:
            parent_task = next(x for x in mapping if x[0] == new_task.parent)[1].task
        except StopIteration:
            parent_task = tree_org
            new_task.task.notes.append("MERGE_INFO: parent is not exist")

        created_task = parent_task.add_subtask(
            title=new_task.task.title,
            task_notes=new_task.task.notes,
            task_todo=new_task.task.todo,
            task_completed=new_task.task.completed)

        mapping.append(tuple([PartTree(parent_task, created_task), new_task, True]))

class PartTree:
    def __init__(self, parent, task):
        self.task = task
        self.parent = parent
        self.hash_sum = 0
        self.titles = []

        if task.title is not None:
            self.titles.append(task.title)
        
        notes = []
        for note_line in task.notes:
            matches = spec_re.findall(note_line)
            if len(matches) > 0:
                if matches[0][0] == "PREV_ORG_TITLE":
                    if matches[0][1] not in self.titles:
                        self.titles.append(matches[0][1])
                    continue
                elif matches[0][0] == "REMOTE_APPEND_NOTE":
                    note_line = matches[0][1]
            notes.append(note_line)
        self.notes = " ".join(notes)

        for title in self.titles:
            for char in title:
                self.hash_sum += ord(char)
        for char in self.notes:
            self.hash_sum += ord(char)

    def is_equal(self, another):
        if len(self.titles) == 0 and len(another.titles) == 0:
            return True
        
        return any(a == b for a in self.titles for b in another.titles) and self.notes == another.notes

    def calc_ratio(self, another):
        return max(self.__calc_ratio(a, b) for a in self.titles for b in another.titles) * 0.7 +\
            self.__calc_ratio(self.notes, another.notes) * 0.3

    def __calc_ratio(self, str1, str2):
        if len(str1) == 0 and len(str2) == 0:
            return 1
        
        seq = SequenceMatcher(None, str1, str2)
        ratio = 0
        
        for opcode in seq.get_opcodes():
            if opcode[0] == 'equal' or opcode[0] == 'insert':
                continue
            if opcode[0] == 'delete':
                ratio += opcode[2] - opcode[1]
            if opcode[0] == 'replace':
                ratio += max(opcode[4] - opcode[3], opcode[2] - opcode[1])
        return 1 - ratio/max(len(str1), len(str2))

    def __str__(self):
        return "{0} {1}, p: {2}".format(self.task.title, self.hash_sum, self.parent)

    def __repr__(self):
        return str(self)

def disassemble_tree(tree, disassemblies, parent = None):
    current = PartTree(parent, tree)
    disassemblies.append(current)

    for i in range(len(tree)):
        disassemble_tree(tree[i], disassemblies, current)
        

def get_service(profile_name):
    """
    Handle oauth's shit (copy-pasta from
    http://code.google.com/apis/tasks/v1/using.html)
    Yes I do publish a secret key here, apparently it is normal
    http://stackoverflow.com/questions/7274554/why-google-native-oauth2-flow-require-client-secret
    """
    storage = oauth2client.file.Storage(save_data_path("oauth.dat"))
    credentials = storage.get()
    if not credentials or credentials.invalid:
        flow = client.OAuth2WebServerFlow(
            client_id='617841371351.apps.googleusercontent.com',
            client_secret='_HVmphe0rqwxqSR8523M6g_g',
            scope='https://www.googleapis.com/auth/tasks',
            user_agent='michel/0.0.1')
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args("")
        credentials = tools.run_flow(flow, storage, flags)
    http = httplib2.Http()
    http = credentials.authorize(http)
    return discovery.build(serviceName='tasks', version='v1', http=http)

def get_list_id(service, list_name=None):
    if list_name is None:
        list_id = "@default"
    else:
        # look up id by list name
        tasklists = service.tasklists().list().execute()
        for tasklist in tasklists['items']:
            if tasklist['title'] == list_name:
                list_id = tasklist['id']
                break
        else:
            # no list with the given name was found
            print('\nERROR: No google task-list named "%s"\n' % list_name)
            sys.exit(2)

    return list_id

def get_gtask_list_as_tasktree(profile, list_name=None):
    """Get a TaskTree object representing a google tasks list.
    
    The Google Tasks list named *list_name* is retrieved, and converted into a
    TaskTree object which is returned.  If *list_name* is not specified, then
    the default Google-Tasks list will be used.
    
    """
    service = get_service(profile)
    list_id = get_list_id(service, list_name)
    tasks = service.tasks().list(tasklist=list_id).execute()
    tasklist = [t for t in tasks.get('items', [])]

    return tasklist_to_tasktree(tasklist)

def tasklist_to_tasktree(tasklist):
    """Convert a list of task dictionaries to a task-tree.

    Take a list of task-dictionaries, and convert them to a task-tree object.
    Each dictionary can have the following keys:

        title -- title of task [required]
        id -- unique identification number of task [required]
        parent -- unique identification number of task's parent
        notes -- additional text describing task
        status -- flag indicating whether or not task is crossed off

    """
    tasks_tree = TasksTree()

    fail_count = 0
    while tasklist != [] and fail_count < 1000:
        t = tasklist.pop(0)
        try:
            if len(t['title'].strip()) > 0:
                tasks_tree.add_subtask(
                    title = t['title'],
                    task_id = t['id'],
                    parent_id = t.get('parent'),
                    task_notes = t.get('notes').split('\n') if t.get('notes') else None,
                    task_todo = True,
                    task_completed = t.get('status') == 'completed')
        except ValueError:
            fail_count += 1
            tasklist.append(t)

    return tasks_tree

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
    
def parse_text_to_tree(text):
    """Parses an org-mode formatted block of text and returns a tree"""
    # create a (read-only) file object containing *text*
    f = io.StringIO(text)
    
    tasks_tree = TasksTree()
    last_task = None

    for line in f:
        line = line.strip()
        matches = headline_regex.findall(line)
        try:
            # assign task_depth; root depth starts at 0
            indent_level = len(matches[0][0])

            # add the task to the tree
            last_task = tasks_tree.last_task_node_at_level(indent_level-1).add_subtask(
                title=matches[0][2],
                task_todo=matches[0][1] == 'DONE' or matches[0][1] == 'TODO',
                task_completed=matches[0][1] == 'DONE')

        except IndexError:
            # this is not a task, but a task-notes line
            
            if last_task is None:
                raise ValueError("Text without task is not permitted")
            
            matches = spec_notes.findall(line)
            for match in matches:
                if len(match[0]) > 0:
                    time = [int(x) for x in time_regex.findall(match[0])[0] if len(x) > 0]
                    last_task.closed_time = datetime.datetime(time[0], time[1], time[2],
                                                              time[3], time[4], tzinfo = LocalTzInfo())
                if len(match[1]) > 0:
                    time = [int(x) for x in time_regex.findall(match[1])[0] if len(x) > 0]

                    last_task.scheduled_start_time = datetime.datetime(time[0], time[1], time[2],
                                                                       tzinfo = LocalTzInfo())

                    if len(time) > 3:
                        last_task.scheduled_start_time = datetime.datetime(time[0], time[1], time[2],
                                                                           time[3], time[4], tzinfo = LocalTzInfo())
                    if len(time) > 5:
                        last_task.scheduled_end_time = datetime.datetime(time[0], time[1], time[2],
                                                                         time[5], time[6], tzinfo = LocalTzInfo())

            last_task.notes.append(line.strip())

    f.close()

    tasks_tree.normalize_todo()
    return tasks_tree

def to_google_date_format(value):
    return "{0:0>4}-{1:0>2}-{2:0>2}T00:00:00Z".format(value.year, value.month, value.day)

def push_todolist(path, profile, list_name, only_todo):
    """Pushes the specified file to the specified todolist"""
    service = get_service(profile)
    list_id = get_list_id(service, list_name)
    tasks_tree = parse_path(path)
    erase_todolist(profile, list_id)
    tasks_tree.push(service, list_id, only_todo)

def sync_todolist(path, profile, list_name, only_todo):
    """Synchronizes the specified file with the specified todolist"""
    tree_remote = get_gtask_list_as_tasktree(profile, list_name)
    tree_org = parse_path(path)
    
    treemerge(tree_org, tree_remote)
    
    # write merged tree to tasklist
    service = get_service(profile)
    list_id = get_list_id(service, list_name)
    erase_todolist(profile, list_id)
    tree_org.push(service, list_id, only_todo)
        
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
                print ("Pull {0} -> {1}:{2}".format(entry['org_file'], entry['profile'], entry['listname']))
                write_todolist(entry['org_file'], entry['profile'], entry['listname'])
        
if __name__ == "__main__":
    main()
