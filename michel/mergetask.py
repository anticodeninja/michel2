import datetime
from difflib import SequenceMatcher
from ipdb import set_trace

RATIO_THRESHOLD = 0.85

class PartTree:
    def __init__(self, parent, task):
        self.task = task
        self.parent = parent
        self.hash_sum = 0
        self.titles = []

        if task.title is not None:
            self.titles.append(task.title)
        if task.prev_title is not None:
            self.titles.append(task.prev_title)
        
        self.notes = " ".join(task.notes)

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
            map_entry[1].task.closed_time = datetime.datetime.now()

        if map_entry[0].task.scheduled_start_time and not map_entry[1].task.scheduled_start_time:
            map_entry[1].task.scheduled_start_time = map_entry[0].task.scheduled_start_time

        # Merge contents
        if map_entry[0].task.title != map_entry[1].task.title:
            if map_entry[1].task.title not in map_entry[0].titles:
                map_entry[1].task.prev_title = map_entry[1].task.title
                map_entry[1].task.title = map_entry[0].task.title

        if map_entry[0].task.notes != map_entry[1].task.notes:
            for note_line in map_entry[0].task.notes:
                if note_line not in map_entry[1].task.notes:
                    diff_notes.append("SYNC: {0}".format(note_line))

        map_entry[1].task.notes += diff_notes

    # fourth step, append new items
    for i in range(len(tasks_remote)):
        new_task = tasks_remote[i]

        try:
            parent_task = next(x for x in mapping if x[0] == new_task.parent)[1].task
        except StopIteration:
            parent_task = tree_org
            new_task.task.notes.append("MERGE_INFO: parent is not exist")

        created_task = parent_task.add_subtask(new_task.task.title)
        created_task.notes = new_task.task.notes
        created_task.todo = new_task.task.todo
        created_task.completed = new_task.task.completed
        created_task.scheduled_start_time = new_task.task.scheduled_start_time

        mapping.append(tuple([PartTree(parent_task, created_task), new_task, True]))
