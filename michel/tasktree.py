#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import codecs
import re
import io
import datetime

from michel.utils import *

headline_regex = re.compile("^(\*+) *(DONE|TODO)? *(.*)")
timeline_regex = re.compile("(?:CLOSED: \[(.*)\]|(?:SCHEDULED: <(.*)>) *)+")

class OrgDate:
    default_locale = None
    _regex = re.compile("(\d+)-(\d+)-(\d+) \S+(?: (\d+):(\d+)(?:-(\d+):(\d+))?)?")

    def __init__(self, date, start_time = None, duration = None):
        if start_time is None and duration is not None:
            raise ValueError("duration cannot be defined without start_time")
            
        self._date = date
        self._start_time = start_time
        self._duration = duration
        

    @classmethod
    def parse_org_format(self, org_time = None):
        if org_time is None:
            return None
        
        temp = [int(x) for x in self._regex.findall(org_time)[0] if len(x) > 0]
        if len(temp) < 3:
            return None

        date = datetime.date(temp[0], temp[1], temp[2])
        start_time = datetime.time(temp[3], temp[4]) if len(temp) > 3 else None
        duration = self._calc_duration(start_time, datetime.time(temp[5], temp[6])) if len(temp) > 5 else None

        return self(date, start_time, duration)

    @classmethod
    def now(self):
        temp = datetime.datetime.now()

        return self(datetime.date(temp.year, temp.month, temp.day),
                    datetime.time(temp.hour, temp.minute))

    def to_org_format(self):
        try:
            old_locale = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, type(self).default_locale)
            res = self._date.strftime("%Y-%m-%d %a")

            if self._start_time:
                res += self._start_time.strftime(" %H:%M")
                
            if self._duration:
                res += self._calc_end_time(self._start_time, self._duration).strftime("-%H:%M")

            if os.name == 'nt':
                # It's hell...
                res = res.encode('latin-1').decode(locale.getpreferredencoding())
                                           
            return res
        finally:
            locale.setlocale(locale.LC_TIME, old_locale)

    def get_date(self):
        return self._date

    def get_time(self):
        return self._time

    def get_hash(self):
        total_days2 = (self._date.year * 12 + self._date.month) * 31 + self._date.day
        total_minutes2 = (self._start_time.hour * 60 + self._start_time.minute) if self._start_time else 0
        return total_days2 * 24 * 60 + total_minutes2

    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            self._date == other._date and \
            self._start_time == other._start_time and \
            self._duration == other._duration

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if self._date < other._date:
            return True
        elif self._date > other._date:
            return False

        if self._start_time is None or other._start_time is None:
            return False
                
        if self._start_time < other._start_time:
            return True
        elif self._start_time > other._start_time:
            return False

        return False

    def __str__(self):
        return self.to_org_format()

    @classmethod
    def _calc_duration(self, time1, time2):
        return datetime.timedelta(minutes = (time2.hour - time1.hour) * 60 + (time2.minute - time1.minute))

    @classmethod
    def _calc_end_time(self, time, duration):
        duration_hours, remainder = divmod(duration.seconds, 3600)
        duration_minutes, _ = divmod(remainder, 60)

        hours = time.hour + duration_hours
        minutes = time.minute + duration_minutes
        
        while minutes >= 60:
            hours += 1
            minutes -= 60
            
        return datetime.time(hours, minutes)
                                        
        
class TasksTree(object):
    """
    Tree for holding tasks

    A TasksTree:
    - is a task (except the root, which just holds the list)
    - has subtasks
    - may have a title
    """

    def __init__(self, title):
        self.title = title
        self.subtasks = []
        self.notes = []

        self.todo = False
        self.completed = False
        
        self.closed_time = None
        self.schedule_time = None
        
    def __getitem__(self, key):
        return self.subtasks[key]
         
    def __setitem__(self, key, val):
        self.subtasks[key] = val
        
    def __delitem__(self, key):
        del(self.subtasks[key])

    def __repr__(self):
        return self.title or "<empty>"

    def __len__(self):
        return len(self.subtasks)

    def update(self, todo=None, completed=None, closed_time=None, schedule_time=None, notes=None):
        if todo is not None:
            self.todo = todo
            
        if completed is not None:
            self.todo = True
            self.completed = completed

        if notes is not None:
            self.notes = notes

        if closed_time is not None:
            self.closed_time = closed_time

        if schedule_time is not None:
            self.schedule_time = schedule_time
        
        return self

    def add_subtask(self, title):
        """
        Adds a subtask to the tree
        """

        task = TasksTree(title)
        self.subtasks.append(task)
        return task

    def remove_subtask(self, task):
        """
        Remove the subtask from the tree
        """

        self.subtasks.remove(task)
        return task

    def find_parent(self, task):
        for item in self:
            if item == task:
                return self
            else:
                result = item.find_parent(task)
                if result is not None:
                    return result

    def parse_system_notes(self):
        for subtask in self.subtasks:
            subtask.parse_system_notes()

        real_notes = []
        for line in self.notes:
            note_string = True
            
            matches = timeline_regex.findall(line)
            for match in matches:                
                if len(match[0]) > 0:
                    note_string = False
                    self.closed_time = OrgDate.parse_org_format(match[0])

                if len(match[1]) > 0:
                    note_string = False
                    self.schedule_time = OrgDate.parse_org_format(match[1])
                    
            if note_string:
                real_notes.append(line)

        while (len(real_notes) > 0) and (len(real_notes[0].strip()) == 0):
            real_notes.pop(0)
        while (len(real_notes) > 0) and (len(real_notes[-1].strip()) == 0):
            real_notes.pop(-1)

        self.notes = real_notes

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

            time_line = [' ' * (level + 1)]
            if subtask.closed_time:
                time_line.append("CLOSED: [{0}]".format(subtask.closed_time.to_org_format()))
            if subtask.schedule_time:
                time_line.append("SCHEDULED: <{0}>".format(subtask.schedule_time.to_org_format()))
            if len(time_line) > 1:
                res.append(' '.join(time_line))

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

    def write_file(self, fname):
        f = codecs.open(fname, "w", "utf-8")
        f.write(self.__str__())
        f.close()

    def parse_file(path):
        """Parses an org-mode file and returns a tree"""
        file_lines = codecs.open(path, "r", "utf-8").readlines()
        file_text = "".join(file_lines)
        return TasksTree.parse_text(file_text)
    
    def parse_text(text):
        """Parses an org-mode formatted block of text and returns a tree"""
        # create a (read-only) file object containing *text*
        f = io.StringIO(text)
    
        tasks_tree = TasksTree(None)
    
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
