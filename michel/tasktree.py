#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import re
import io
import datetime

from michel.utils import *

headline_regex = re.compile("^(\*+) *(DONE|TODO)? *(.*)")
timeline_regex = re.compile("(?:CLOSED: \[(.*)\]|(?:SCHEDULED: <(.*)>) *)+")

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
        self.scheduled_has_time = False
        self.scheduled_start_time = None
        self.scheduled_end_time = None
        
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

    def update(self, todo=None, completed=None, notes=None, scheduled_has_time=None, scheduled_start_time=None, scheduled_end_time=None):
        if todo is not None:
            self.todo = todo
            
        if completed is not None:
            self.todo = True
            self.completed = completed

        if notes is not None:
            self.notes = notes

        if completed and not self.closed_time:
            self.closed_time = datetime.datetime.now()

        if scheduled_has_time is not None:
            self.scheduled_has_time = scheduled_has_time

        if scheduled_start_time is not None:
            self.scheduled_start_time = scheduled_start_time

        if scheduled_end_time is not None:
            self.scheduled_end_time = scheduled_end_time
        
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
                    _, self.closed_time, _ = from_emacs_date_format(match[0])

                if len(match[1]) > 0:
                    note_string = False
                    self.scheduled_has_time, self.scheduled_start_time, self.scheduled_end_time = from_emacs_date_format(match[1])
                    
            if note_string:
                real_notes.append(line)

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
                time_line.append("CLOSED: [{0}]".format(
                                 to_emacs_date_format(True, subtask.closed_time)))
            if subtask.scheduled_start_time:
                time_line.append("SCHEDULED: <{0}>".format(
                                 to_emacs_date_format(
                                     subtask.scheduled_has_time,
                                     subtask.scheduled_start_time,
                                     subtask.scheduled_end_time)))
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
