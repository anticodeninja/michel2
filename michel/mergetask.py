import datetime
from difflib import SequenceMatcher
from ipdb import set_trace

class PartTree:
    def __init__(self, parent, task):
        self.task = task
        self.parent = parent
        
        self.hash_sum = 0
        if self.task.title:
            for char in self.task.title:
                self.hash_sum += ord(char)

    def is_equal(self, another):
        return self.task.title == another.task.title

    def calc_ratio(self, another):
        return self.__calc_ratio(self.task.title, another.task.title)

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

def merge_attr(task_remote, task_org, attr_name, merge_func, changes_list):
    if getattr(task_remote, attr_name) != getattr(task_org, attr_name):
        setattr(task_org, attr_name, merge_func(getattr(task_remote, attr_name), getattr(task_org, attr_name)))
            
    if getattr(task_remote, attr_name) != getattr(task_org, attr_name):
        setattr(task_remote, attr_name, getattr(task_org, attr_name))
        changes_list.append(attr_name)

def copy_attr(task_dst, task_src):
    for attr_name in ["notes", "todo", "completed", "closed_time", "scheduled_start_time", "scheduled_end_time"]:
        setattr(task_dst, attr_name, getattr(task_src, attr_name))

def treemerge(tree_org, tree_remote, conf):
    tasks_org = []
    tasks_remote = []
    sync_plan = []

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
    while index_remote < len(tasks_remote) and len(tasks_org) > 0:
        index_org = conf.select_best(tasks_remote[index_remote], tasks_org)

        if index_org is not None:
            mapping.append(tuple([tasks_remote.pop(index_remote), tasks_org.pop(index_org), False]))
        else:
            index_remote += 1

    # third step, patching org tree
    for map_entry in mapping:
        diff_notes = []
        changes_list = []

        merge_attr(map_entry[0].task, map_entry[1].task, "completed",
                   lambda a, b: any([a, b]), changes_list)
        merge_attr(map_entry[0].task, map_entry[1].task, "closed_time",
                   lambda a, b: b or a, changes_list)
        merge_attr(map_entry[0].task, map_entry[1].task, "scheduled_start_time",
                   lambda a, b: conf.select_from("scheduled_start_time", [a, b]), changes_list)
        merge_attr(map_entry[0].task, map_entry[1].task, "scheduled_end_time",
                   lambda a, b: conf.select_from("scheduled_end_time", [a, b]), changes_list)
        merge_attr(map_entry[0].task, map_entry[1].task, "title",
                   lambda a, b: conf.select_from("title", [a, b]), changes_list)
        merge_attr(map_entry[0].task, map_entry[1].task, "notes",
                   lambda a, b: conf.merge_notes([a, b]), changes_list)

        if len(changes_list) > 0:
            if conf.is_needed(map_entry[0].task):
                sync_plan.append({
                    "action": "update",
                    "changes": changes_list,
                    "item": map_entry[0].task
                })
            else:
                sync_plan.append({
                    "action": "remove",
                    "item": map_entry[0].task
                })

    # fourth step, append new items to org tree
    for i in range(len(tasks_remote)):
        new_task = tasks_remote[i]

        try:
            parent_task = next(x for x in mapping if x[0] == new_task.parent)[1].task
        except StopIteration:
            parent_task = tree_org

        created_task = parent_task.add_subtask(new_task.task.title)
        copy_attr(created_task, new_task.task)

        if not conf.is_needed(new_task.task):
            sync_plan.append({
                "action": "remove",
                "item": new_task.task
            })

    # fifth step, append new items to remote tree
    for i in range(len(tasks_org)):
        new_task = tasks_org[i]

        try:
            parent_task = next(x for x in mapping if x[1] == new_task.parent)[0].task
        except StopIteration:
            parent_task = tree_remote

        if not conf.is_needed(new_task.task):
            continue

        created_task = parent_task.add_subtask(new_task.task.title)
        copy_attr(created_task, new_task.task)

        sync_plan.append({
            "action": "append",
            "item": new_task.task
        })

    return sync_plan
