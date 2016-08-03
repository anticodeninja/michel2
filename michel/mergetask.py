#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

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

    def __str__(self):
        return "{0} {1}, p: {2}".format(self.task.title, self.hash_sum, self.parent)

    def __repr__(self):
        return str(self)

class MergeEntry:
    def __init__(self, org, remote, base = None):
        self.org = org
        self.remote = remote
        self.base = base

    def __str__(self):
        return "org:{0} remote:{1} base:{2}".format(self.org, self.remote, self.base)

    def __repr__(self):
        return str(self)

def disassemble_tree(tree, disassemblies, parent = None):
    current = PartTree(parent, tree)
    disassemblies.append(current)

    for i in range(len(tree)):
        disassemble_tree(tree[i], disassemblies, current)

def merge_attr(mapping, attr_name, merge_func, changes_list):
    if getattr(mapping.org, attr_name) != getattr(mapping.remote, attr_name):
        setattr(mapping.org, attr_name, merge_func(mapping))
            
    if getattr(mapping.remote, attr_name) != getattr(mapping.org, attr_name):
        setattr(mapping.remote, attr_name, getattr(mapping.org, attr_name))
        changes_list.append(attr_name)

def copy_attr(task_dst, task_src):
    for attr_name in ["notes", "todo", "completed", "closed_time", "scheduled_start_time", "scheduled_end_time"]:
        setattr(task_dst, attr_name, getattr(task_src, attr_name))


def treemerge(tree_org, tree_remote, tree_base, conf):
    tasks_base = []
    tasks_org = []
    tasks_remote = []
    sync_plan = []

    disassemble_tree(tree_org, tasks_org)
    disassemble_tree(tree_remote, tasks_remote)
    if tree_base is not None:
        disassemble_tree(tree_base, tasks_base)

    tasks_org.sort(key=lambda node: node.hash_sum)
    tasks_remote.sort(key=lambda node: node.hash_sum)
    tasks_base.sort(key=lambda node: node.hash_sum)

    mapped_tasks = []

    # first step, exact matching
    index_remote, index_org = 0, 0
    while index_remote < len(tasks_remote):
        is_mapped = False
        index_org = 0
        
        while index_org < len(tasks_org):
            if tasks_remote[index_remote].is_equal(tasks_org[index_org]):
                mapped_tasks.append(MergeEntry(tasks_org.pop(index_org), tasks_remote.pop(index_remote)))
                is_mapped = True
                break
            else:
                index_org += 1

        if not is_mapped:
            index_remote += 1

    # second step, fuzzy matching
    index_remote, index_org = 0, 0
    while index_remote < len(tasks_remote) and len(tasks_org) > 0:
        index_org = conf.select_org_task(tasks_remote[index_remote].task, (x.task for x in tasks_org))

        if index_org == 'discard':
            tasks_remote[index_remote].task.completed = True
        elif index_org != 'new':
            mapped_tasks.append(MergeEntry(tasks_org.pop(index_org), tasks_remote.pop(index_remote)))
            continue

        index_remote += 1

    # second and half step, base entry exact matching
    index_mapping, index_base = 0, 0
    while index_mapping < len(mapped_tasks):
        index_base = 0

        while index_base < len(tasks_base):
            if mapped_tasks[index_mapping].org.is_equal(tasks_base[index_base]) or \
               mapped_tasks[index_mapping].remote.is_equal(tasks_base[index_base]):
                mapped_tasks[index_mapping].base = tasks_base.pop(index_base)
                break
            else:
                index_base += 1

        index_mapping += 1
            

    # third step, patching org tree
    for map_entry in mapped_tasks:
        diff_notes = []
        changes_list = []

        merge_entry = MergeEntry(
            map_entry.org.task,
            map_entry.remote.task,
            map_entry.base.task if map_entry.base is not None else None)
        
        merge_attr(merge_entry, "title", lambda a: conf.merge_title(a), changes_list)
        merge_attr(merge_entry, "completed", lambda a: conf.merge_completed(a), changes_list)
        merge_attr(merge_entry, "closed_time", lambda a: conf.merge_closed_time(a), changes_list)
        merge_attr(merge_entry, "scheduled_start_time", lambda a: conf.merge_scheduled_start_time(a), changes_list)
        merge_attr(merge_entry, "scheduled_end_time", lambda a: conf.merge_scheduled_end_time(a), changes_list)
        merge_attr(merge_entry, "notes", lambda a: conf.merge_notes(a), changes_list)

        if conf.is_needed(map_entry.remote.task):
            if len(changes_list) > 0:
                sync_plan.append({
                    "action": "update",
                    "changes": changes_list,
                    "item": map_entry.remote.task
                })
        else:
            if map_entry.remote.task.title is not None:
                sync_plan.append({
                    "action": "remove",
                    "item": map_entry.remote.task
                })

    # fourth step, append new items to org tree
    for i in range(len(tasks_remote)):
        new_task = tasks_remote[i]

        try:
            parent_task = next(x for x in mapped_tasks if x.remote == new_task.parent).org.task
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

        if not conf.is_needed(new_task.task):
            continue

        try:
            parent_task = next(x for x in mapped_tasks if x.org == new_task.parent).remote.task
        except StopIteration:
            parent_task = tree_remote

        created_task = parent_task.add_subtask(new_task.task.title)
        copy_attr(created_task, new_task.task)

        sync_plan.append({
            "action": "append",
            "item": created_task
        })

    return sync_plan
