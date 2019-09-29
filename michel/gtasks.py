# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import httplib2

import os
import sys
import datetime
import argparse
import re

from apiclient import discovery
import oauth2client
import oauth2client.file
from oauth2client import client
from oauth2client import tools

from michel.tasktree import TaskLink, TasksTree, OrgDate
from michel import utils

if 'HTTP_PROXY' in os.environ:
    try:
        import socks
        http_proxy = re.match("^(?P<scheme>http|https|socks):\/\/(?:(?P<username>[^:]+):(?P<password>[^@]+)@)?(?P<address>[^:]+)(?::(?P<port>\d+))?$", os.environ['HTTP_PROXY'])
        socks.set_default_proxy(socks.HTTP,
                                http_proxy.group('address'),
                                int(http_proxy.group('port')),
                                username=http_proxy.group('username'),
                                password=http_proxy.group('password'))
        socks.wrap_module(httplib2)
    except:
        print("HTTP Proxy cannot be used, please install pysocks", file=sys.stderr)
        sys.exit(1)


class GtaskProvider:
    _sys_regex = re.compile(":PARENT: (.*)")
    _google_time_regex = re.compile("(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+).+")

    def __init__(self, path, params):
        self._profile_name = path[0]
        self._list_name = path[1]

        self._tasks_tree = None
        self._task_id_map = None
        self._id_task_map = None

        self._init_service()

    def merge_schedule_time(self, default, mapping):
        remote = mapping.remote.schedule_time
        org = mapping.org.schedule_time

        if not remote or not org:
            return default(mapping)

        remote = remote.get_date()
        org = org.get_date()

        if remote.year != org.year or remote.month != org.month or remote.day != org.day:
            return default(mapping)

        mapping.remote.schedule_time = mapping.org.schedule_time
        return mapping.org.schedule_time

    def get_tasks(self):
        return self._tasks_tree


    def sync(self, sync_plan):
        for item in sync_plan:
            task = item['item']
            if item['action'] == 'append':
                if task.title is None:
                    continue

                notes = [x for x in task.notes]
                parent = self._tasks_tree.find_parent(task)
                gparent = None

                if parent:
                    if parent in self._task_id_map:
                        gparent = self._task_id_map[parent]
                    elif parent.title:
                        notes.insert(0, ':PARENT: ' + parent_task)

                gtask = {
                    'title': task.title,
                    'notes': '\n'.join(notes),
                    'status': 'completed' if task.completed else 'needsAction'
                }

                if task.closed_time is not None:
                    gtask['completed'] = self._to_google_date_format(task.closed_time)

                if task.schedule_time is not None:
                    gtask['due'] = self._to_google_date_format(task.schedule_time)

                if len(task.links) > 0:
                    gtask['links'] = GtaskProvider.convert_links(task.links)

                res = self._service.tasks().insert(
                    tasklist=self._list_id,
                    parent=gparent,
                    body=gtask
                ).execute()

                self._task_id_map[task] = res['id']

            elif item['action'] == 'update':
                gtask = {}
                if 'title' in item['changes']:
                    gtask['title'] = task.title
                if 'notes' in item['changes']:
                    gtask['notes'] = '\n'.join(task.notes)
                if 'completed' in item['changes']:
                    if task.completed:
                        gtask['status'] = 'completed'
                        gtask['completed'] = self._to_google_date_format(task.closed_time)
                    else:
                        gtask['status'] = 'needsAction'
                        gtask['completed'] = None
                if 'schedule_time' in item['changes']:
                    if task.schedule_time:
                        gtask['due'] = self._to_google_date_format(task.schedule_time)
                    else:
                        gtask['due'] = None
                if 'links' in item['changes']:
                    gtask['links'] = GtaskProvider.convert_links(task.links)

                if len(gtask) == 0:
                    continue

                self._service.tasks().patch(
                    tasklist=self._list_id,
                    task=self._task_id_map[task],
                    body=gtask
                ).execute()

            elif item['action'] == 'remove':
                task_id = self._task_id_map[task]

                self._service.tasks().delete(
                    tasklist=self._list_id,
                    task=task_id
                ).execute()

                parent = self._tasks_tree.find_parent(task)
                if parent is not None:
                    parent.remove_subtask(task)

                del self._id_task_map[task_id]
                del self._task_id_map[task]

    def pull(self):
        """Get a TaskTree object representing a google tasks list.

        The Google Tasks list named *list_name* is retrieved, and converted into a
        TaskTree object which is returned.  If *list_name* is not specified, then
        the default Google-Tasks list will be used.

        """

        pageToken = None
        tasklist = []
        while True:
            tasks = self._service.tasks().list(tasklist=self._list_id, pageToken=pageToken).execute()
            tasklist += [t for t in tasks.get('items', [])]

            pageToken = tasks.get('nextPageToken', None)
            if not pageToken:
                break

        self._tasks_tree = TasksTree(None)
        self._task_id_map = {}
        self._id_task_map = {}

        fail_count = 0
        while tasklist != [] and fail_count < 1000:
            gtask = tasklist.pop(0)
            try:
                title = gtask['title'].strip()
                if len(title) == 0:
                    continue

                if 'parent' in gtask and gtask['parent'] in self._id_task_map:
                    parent_task = self._id_task_map[gtask['parent']]
                else:
                    parent_task = self._tasks_tree

                task = parent_task.add_subtask(title)

                self._id_task_map[gtask['id']] = task
                self._task_id_map[task] = gtask['id']

                task.todo = True
                task.completed = gtask['status'] == 'completed'
                task.schedule_time = self._from_google_date_format(gtask['due']) if 'due' in gtask else None
                task.closed_time = self._from_google_date_format(gtask['completed']) if 'completed' in gtask else None

                if 'notes' in gtask:
                    for note_line in gtask['notes'].split('\n'):
                        note_line = note_line.strip()
                        if self._sys_regex.match(note_line):
                            continue

                        if len(note_line) > 0:
                            task.notes.append(note_line)

                if 'links' in gtask:
                    for link in gtask['links']:
                        task.links.append(TaskLink(
                            link['link'],
                            link['description'],
                            [link['type']]))

            except ValueError:
                fail_count += 1

    def _init_service(self):
        """
        Handle oauth's shit (copy-paste from
        http://code.google.com/apis/tasks/v1/using.html)
        Yes I do publish a secret key here, apparently it is normal
        http://stackoverflow.com/questions/7274554/why-google-native-oauth2-flow-require-client-secret
        """

        storage = oauth2client.file.Storage(utils.save_data_path("gtasks_oauth.dat"))
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
        self._service = discovery.build(serviceName='tasks', version='v1', http=http, cache_discovery=False)

        if self._list_name is None or self._list_name == "default":
            self._list_id = "@default"
        else:
            tasklists = self._service.tasklists().list().execute()
            for tasklist in tasklists['items']:
                if tasklist['title'] == self._list_name:
                    self._list_id = tasklist['id']
                    break

        if not self._list_id:
            raise Exception('ERROR: No google task-list named "{0}"'.format(self._list_name))

    @classmethod
    def _from_google_date_format(self, value):
        time = [int(x) for x in self._google_time_regex.findall(value)[0] if len(x) > 0]
        return OrgDate(datetime.date(time[0], time[1], time[2]))

    @classmethod
    def _to_google_date_format(self, value):
        return value.get_date().strftime("%Y-%m-%dT00:00:00Z")

    @classmethod
    def convert_links(self, links):
        return [{
            'link': x.link,
            'description': x.title or x.link,
            'type': x.tags[0] if len(x.tags) > 0 else 'url'
        } for x in links]
