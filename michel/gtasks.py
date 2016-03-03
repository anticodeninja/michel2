import pdb; pdb.set_trace();
import httplib2

import argparse

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from michel.tasktree import TasksTree
from michel.utils import *

sys_regex = re.compile(":PARENT: (.*)")

class GTaskProvider:

    def __init__(self, profile_name, list_name, conf):
        self.__profile_name = profile_name
        self.__list_name = list_name
        self.__conf = conf
        
        self.__tasks_tree = None
        self.__task_id_map = None
        self.__id_task_map = None
        
        self.__init_service()


    def get_tasks(self):
        return self.__tasks_tree

    def erase(self):
        """Erases the todo list of given id"""
        
        tasks = self.__service.tasks().list(tasklist=self.__list_id).execute()
        for task in tasks.get('items', []):
            self.__service.tasks().delete(tasklist=self.__list_id, task=task['id']).execute()

        self.pull()
            

    def sync(self, sync_plan):
        print(sync_plan)

        for item in sync_plan:
            task = item['item']            
            if item['action'] == 'append':
                if task.title is None:
                    continue
                
                notes = [x for x in task.notes]
                parent = self.__tasks_tree.find_parent(task)
                gparent = None

                if parent:
                    if parent in self.__task_id_map:
                        gparent = self.__task_id_map[parent]
                    elif parent.title:
                        notes.insert(0, ':PARENT: ' + parent_task)
                        
                gtask = {
                    'title': task.title,
                    'notes': '\n'.join(notes),
                    'status': 'completed' if task.completed else 'needsAction'
                }
                
                if task.closed_time is not None:
                    gtask['completed'] = task.closed_time.astimezone().isoformat()
                
                if task.scheduled_start_time is not None:
                    gtask['due'] = task.scheduled_start_time.astimezone().isoformat()

                res = self.__service.tasks().insert(
                    tasklist=self.__list_id,
                    parent=gparent,
                    body=gtask
                ).execute()
                
                self.__task_id_map[task] = res['id']
                
            elif item['action'] == 'update':
                gtask = {}
                if 'title' in item['changes']:
                    gtask['title'] = task.title
                if 'notes' in item['changes']:
                    gtask['notes'] = '\n'.join(task.notes)
                if 'completed' in item['changes']:
                    if task.completed:
                        gtask['status'] = 'completed'
                        gtask['completed'] = task.closed_time.astimezone().isoformat()
                    else:
                        gtask['status'] = 'needsAction'
                        gtask['completed'] = None
                if 'scheduled_start_time' in item['changes']:
                    gtask['due'] = task.scheduled_start_time.astimezone().isoformat()

                if len(gtask) == 0:
                    continue

                print(gtask)
                
                self.__service.tasks().patch(
                    tasklist=self.__list_id,
                    task=self.__task_id_map[task],
                    body=gtask
                ).execute()  
            
            elif item['action'] == 'remove':
                task_id = self.__task_id_map[task]

                self.__service.tasks().delete(
                    tasklist=self.__list_id,
                    task=task_id
                ).execute()

                parent = self.__tasks_tree.find_parent(task)
                if parent is not None:
                    parent.remove_subtask(task)
                
                del self.__id_task_map[task_id]
                del self.__task_id_map[task]
    
    def pull(self):
        """Get a TaskTree object representing a google tasks list.
        
        The Google Tasks list named *list_name* is retrieved, and converted into a
        TaskTree object which is returned.  If *list_name* is not specified, then
        the default Google-Tasks list will be used.
        
        """
        tasks = self.__service.tasks().list(tasklist=self.__list_id).execute()
        tasklist = [t for t in tasks.get('items', [])]

        self.__tasks_tree = TasksTree(None)
        self.__task_id_map = {}
        self.__id_task_map = {}

        fail_count = 0
        while tasklist != [] and fail_count < 1000:
            gtask = tasklist.pop(0)
            try:
                title = gtask['title'].strip()
                if len(title) == 0:
                    continue
                
                if 'parent' in gtask and gtask['parent'] in self.__id_task_map:
                    parent_task = self.__id_task_map[gtask['parent']]
                else:
                    parent_task = self.__tasks_tree

                task = parent_task.add_subtask(title)
                
                self.__id_task_map[gtask['id']] = task
                self.__task_id_map[task] = gtask['id']

                task.todo = True
                task.completed = gtask['status'] == 'completed'
                task.scheduled_start_time = from_google_date_format(gtask['due']) if 'due' in gtask else None
                task.closed_time = from_google_date_format(gtask['completed']) if 'completed' in gtask else None

                if task.completed and not task.closed_time:
                    task.closed_time = datetime.datetime.now()
                    
                task.notes = []
                if 'notes' in gtask:
                    for note_line in gtask['notes'].split('\n'):
                        note_line = note_line.strip()
                        if sys_regex.match(note_line):
                            continue
                        
                        if len(note_line) > 0:
                            task.notes.append(note_line)
                                                                    
            except ValueError:
                fail_count += 1

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

