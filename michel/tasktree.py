import codecs
import re
import datetime

from michel.utils import *

timeline_regex = re.compile("(?:CLOSED: \[(.*)\]|(?:SCHEDULED: <(.*)>) *)+")
systemline_regex = re.compile("([^.]+): (.+)")

class TasksTree(object):
    """
    Tree for holding tasks

    A TasksTree:
    - is a task (except the root, which just holds the list)
    - has subtasks
    - may have a task_id
    - may have a title
    """

    def __init__(self, title):
        self.title = title
        self.prev_title = None
        self.subtasks = []
        self.notes = []

        self.todo = False
        self.completed = False
        
        self.closed_time = None
        self.scheduled_has_time = False
        self.scheduled_start_time = None
        self.scheduled_end_time = None

        self.task_id = None
        self.remote = False
        
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

    def add_subtask(self, title):
        """
        Adds a subtask to the tree
        """

        task = TasksTree(title)
        task.remote = self.remote
        self.subtasks.append(task)
        return task

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
                    
                    if not self.remote:
                        _, self.closed_time, _ = from_emacs_date_format(match[0])

                if len(match[1]) > 0:
                    note_string = False

                    if not self.remote:
                        self.scheduled_has_time, self.scheduled_start_time, self.scheduled_end_time = from_emacs_date_format(match[1])

            matches = systemline_regex.findall(line)
            if len(matches) > 0:
                if matches[0][0] == "PREV_TITLE":
                    note_string = False
                    self.prev_title = matches[0][1]

                if matches[0][0] == "SYNC":
                    note_string = not self.remote
                    
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

            if subtask.prev_title:
                system_line = [' ' * (level + 1)]
                system_line.append("PREV_TITLE: {0}".format(subtask.prev_title))
                res.append(' '.join(system_line))

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

    def _print(self):
        print(self.__str__())

    def write_to_orgfile(self, fname):
        f = codecs.open(fname, "w", "utf-8")
        f.write(self.__str__())
        f.close()
