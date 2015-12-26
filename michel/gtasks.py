import httplib2

import argparse

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from michel.tasktree import TasksTree
from michel.utils import *

class GTaskProvider:

    def __init__(self, profile_name, list_name = None, only_todo = True):
        self.__profile_name = profile_name
        self.__only_todo = only_todo
        self.__list_name = list_name
        self.__tasks_tree = None
        
        self.__init_service()

    def set_tasks(self, tasks_tree):
        self.__tasks_tree = tasks_tree

    def get_tasks(self):
        return self.__tasks_tree

    def push(self):
        """Pushes the task tree to the given list"""

        self.erase()
        
        gtasks_map = {}
        tasks = []

        tasks.append((None, self.__tasks_tree))
        while len(tasks) > 0:
            parent_task, task = tasks.pop()
            skipped = False
        
            if task.title is None:
                skipped = True

            if self.__only_todo and (not task.todo or task.completed):
                skipped = True

            if not skipped:
                notes = [x for x in task.notes]

                if task.prev_title:
                    notes.insert(0, 'PREV_TITLE: ' + task.prev_title)
                if parent_task and parent_task not in gtasks_map and parent_task.title:
                    notes.insert(0, 'PARENT: ' + parent_task.title)
            
                insert_cmd_args = {
                    'tasklist': self.__list_id,
                    'body': {
                        'title': task.title,
                        'notes': '\n'.join(notes),
                        'status': 'completed' if task.completed else 'needsAction'
                    }
                }
        
                if parent_task and parent_task in gtasks_map:
                    insert_cmd_args['parent'] = gtasks_map[parent_task]
            
                if task.scheduled_start_time is not None:
                    insert_cmd_args['body']['due'] = task.scheduled_start_time.astimezone().isoformat()
            
                res = self.__service.tasks().insert(**insert_cmd_args).execute()
                gtasks_map[task] = res['id']
            
            # the API head inserts, so we insert in reverse.
            for subtask in task.subtasks:
                tasks.append((task, subtask))

    def erase(self):
        """Erases the todo list of given id"""
        
        tasks = self.__service.tasks().list(tasklist=self.__list_id).execute()
        for task in tasks.get('items', []):
            self.__service.tasks().delete(tasklist=self.__list_id, task=task['id']).execute()
    
    def pull(self):
        """Get a TaskTree object representing a google tasks list.
        
        The Google Tasks list named *list_name* is retrieved, and converted into a
        TaskTree object which is returned.  If *list_name* is not specified, then
        the default Google-Tasks list will be used.
        
        """
        tasks = self.__service.tasks().list(tasklist=self.__list_id).execute()
        tasklist = [t for t in tasks.get('items', [])]

        self.__tasks_tree = TasksTree(None)
        gtasks_map = {}

        fail_count = 0
        while tasklist != [] and fail_count < 1000:
            gtask = tasklist.pop(0)
            try:
                if len(gtask['title'].strip()) > 0:
                    if 'parent' in gtask and gtask['parent'] in gtasks_map:
                        parent_task = gtasks_map[gtask['parent']]
                    else:
                        parent_task = self.__tasks_tree

                    task = parent_task.add_subtask(gtask['title'])
                    gtasks_map[gtask['id']] = task
                
                    task.task_id = gtask['id']
                    task.scheduled_start_time = from_google_date_format(gtask['due']) if 'due' in gtask else None
                    task.notes = []
                    for note_line in gtask['notes'].split('\n'):
                        note_line = note_line.strip()
                        if len(note_line) > 0:
                            task.notes.append(note_line)
                    task.todo = True
                    task.completed = gtask['status'] == 'completed'
                                                                    
            except ValueError:
                fail_count += 1

        self.__tasks_tree.parse_system_notes()

    def __init_service(self):
        """
        Handle oauth's shit (copy-pasta from
        http://code.google.com/apis/tasks/v1/using.html)
        Yes I do publish a secret key here, apparently it is normal
        http://stackoverflow.com/questions/7274554/why-google-native-oauth2-flow-require-client-secret
        """
        
        storage = oauth2client.file.Storage(save_data_path("gtasks_oauth.dat"))
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
        self.__service = discovery.build(serviceName='tasks', version='v1', http=http)
        
        if self.__list_name is None:
            self.__list_id = "@default"
        else:
            tasklists = self.__service.tasklists().list().execute()
            for tasklist in tasklists['items']:
                if tasklist['title'] == self.__list_name:
                    self.__list_id = tasklist['id']
                    break

        if not self.__list_id:
            raise Exception('ERROR: No google task-list named "{0}"'.format(self.__list_name))

