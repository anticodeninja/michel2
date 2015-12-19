import httplib2

import argparse
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from michel.tasktree import TasksTree
from michel.utils import *

class GTaskProvider:
    
    def add_subtask(self, title, task_id = None, parent_id = None):
        """
        Adds a subtask to the tree
        - with the specified task_id
        - as a child of parent_id
        """
        if parent_id is None:
            task = TasksTree(title, task_id)
            self.subtasks.append(task)
            return task
        else:
            if self.get_task_with_id(parent_id) is None:
                raise ValueError("No element with suitable parent id")
            
            return self.get_task_with_id(parent_id).add_subtask(title, task_id, None)

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
    tasks_tree = TasksTree(None)
    gtasks_map = {}

    fail_count = 0
    while tasklist != [] and fail_count < 1000:
        gtask = tasklist.pop(0)
        try:
            if len(gtask['title'].strip()) > 0:
                if 'parent' in gtask and gtask['parent'] in gtasks_map:
                    parent_task = gtasks_map[gtask['parent']]
                else:
                    parent_task = tasks_tree

                task = parent_task.add_subtask(gtask['title'])
                gtasks_map[gtask['id']] = task
                
                task.task_id = gtask['id']
                task.scheduled_start_time = from_google_date_format(gtask['due']) if 'due' in gtask else None
                task.notes = gtask['notes'].split('\n') if 'notes' in gtask else []
                task.todo = True
                task.completed = gtask['status'] == 'completed'
                                                                    
        except ValueError:
            fail_count += 1

    tasks_tree.parse_system_notes()
    return tasks_tree

def push_tasktree(profile, list_name, tree, only_todo):
    """Pushes the task tree to the given list"""

    service = get_service(profile)
    list_id = get_list_id(service, list_name)

    __push_task_tree(service, list_id, tree, only_todo, None)

def __push_task_tree(service, list_id, task, only_todo, parent):
    task_id = None
    
    if task.title is not None and (not only_todo or (task.todo and not task.completed)):
        insert_cmd_args = {
            'tasklist': list_id,
            'body': {
                'title': task.title,
                'notes': '\n'.join(task.notes),
                'status': 'completed' if task.completed else 'needsAction'
            }
        }
        
        if parent:
            insert_cmd_args['parent'] = parent
            
        if task.scheduled_start_time is not None:
            insert_cmd_args['body']['due'] = task.scheduled_start_time.astimezone().isoformat()
            
        res = service.tasks().insert(**insert_cmd_args).execute()
        task_id = res['id']
            
    # the API head inserts, so we insert in reverse.
    for subtask in reversed(task.subtasks):
        __push_task_tree(service, list_id, subtask, only_todo, task_id)
