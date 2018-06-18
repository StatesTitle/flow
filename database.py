import builtins
import enum
import itertools
import re

import pymssql

from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from typing import Dict, List
from typing import NamedTuple

from deps import Vertex, digraph, escape_name
from settings import (
    RESWARE_DATABASE_NAME, RESWARE_DATABASE_PASSWORD, RESWARE_DATABASE_PORT,
    RESWARE_DATABASE_SERVER, RESWARE_DATABASE_USER, ACTION_LIST_DEF_ID, INCLUDE_TRIGGERS
)
import sys


@contextmanager
def _connect_to_db():
    with pymssql.connect(
        RESWARE_DATABASE_SERVER,
        RESWARE_DATABASE_USER,
        RESWARE_DATABASE_PASSWORD,
        RESWARE_DATABASE_NAME,
        port=RESWARE_DATABASE_PORT,
        as_dict=True
    ) as conn:
        yield conn


def col(name, parser=None, nullable=False):
    metadata = {'column': name, 'nullable': nullable}
    if parser:
        metadata['parser'] = parser
    return field(metadata=metadata)


class ColumnMissing(Exception):
    pass

class ParsingFailed(Exception):
    pass


def parse_col(dclass, field, row):
    if field.metadata['column'] not in row:
        raise ColumnMissing(f'{dclass} field {field.name} expected a column named {field.metadata["column"]} in the row')
    val = row[field.metadata['column']]
    if val is None and not field.metadata['nullable']:
        raise ColumnMissing(f'{dclass} field {field.name} expected a column named {field.metadata["column"]} in the row but got NULL from the db')
    parser = field.metadata.get('parser', field.type)
    try:
        return parser(val)
    except ColumnMissing:
        raise
    except Exception as e:
        raise ParsingFailed(f'{dclass} field {field.name} parser {parser} blew up on "{val}"') from e


def create_from_db(dclass, row):
    return dclass(*[parse_col(dclass, f, row) for f in fields(dclass) if 'column' in f.metadata])


@dataclass
class Email:
    id: int = col('ActionEmailTemplateID')
    name: str = col('ActionEmailTemplateName')

    @property
    def node_name(self):
        return escape_name('Email ' + self.name)


@dataclass
class Action:
    id: int = col('ActionDefID')
    name: str = col('Name')
    display_name: str = col('DisplayName')
    description: str = col('Description', nullable=True)
    emails: List[Email] = field(default_factory=list)


class GroupActionProperties:
    '''A mixin for classes that have group_id and action_id fields to add group and action properties that look them up'''
    @property
    def group(self):
        return self._groups[self.group_id]

    @property
    def action(self):
        return self._actions[self.action_id]



# All actions in a group in ResWare have "start" and "complete" tasks. Those tasks can be marked
# "done". All affects happen on either start or complete being marked done.  That's tracked in the
# AffectTypeID column in the ActionGroupAffectDef table. If AffectTypeID is 1, that means the affect
# happens on on the group action's start being marked done. If it's 2, it means the affect happens
# on the complete being marked done.
#
# What an affect does is determined by which additional columns are set on the row in ActionGroupAffectDef:
# 1. If AffectActionListGroupDefID and AffectActionDefID are set,  another GroupAction is being changed.
#    AffectActionTypeID determines if it's the start or complete task that's being changed, just like with
#    AffectTypeID. It can do one of two things:
#     a. If AffectOffset is set, it's changing the due date offset
#     b. If AffectAutoComplete is not null and true, it's marking a task as done. Despite Complete 
#        being in the column name, this doesn't have anything to do with it targeting the start 
#        or complete task. If this is not null and false, that means it's an offset affect
# 2. If CreateActionActionListGroupDefID and CreateActionActionDefID are set, it's adding a new
#    action on the file
# 3. If CreateGroupActionListGroupDefID is set, it's adding a new action group to the file

# Other known affect types and the required columns to identify them
# ('DISPLAY_NAME', ['DisplayName']),
# ('SET_VALUE', ['AffectResWareActionDefValuesID']),
# ('SEND_XML', ['XMLSchemaID'], ['XMLToPartnerTypeID', 'ActionEventDefID']),
# ('CREATE_RECORDING_DOCUMENT', ['RecordingDocumentTypeID']),
# Ones that only require only one of the columns
# ('CREATE_CURATIVE', ['CreateTitleReviewTypeID', 'CreatePolicyCurativeTypeID'],
#         ['CreateTitleReviewTypeOnlyIfNotExists', 'CreatePolicyCurativeTypeOnlyIfNotExists'],
# ('MARK_CURATIVE_INTERNALLY_CLEARED', ['ClearTitleReviewTypeID', 'ClearPolicyCurativeTypeID'],)


class AffectTask(enum.IntEnum):
    STARTED = 1
    COMPLETED = 2


@dataclass
class Affect(GroupActionProperties):
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')
    task: AffectTask = col('ActionTypeID')


@dataclass
class ActionAffect(Affect):
    affected_group_id: int = col('AffectActionListGroupDefID')
    affected_action_id: int = col('AffectActionDefID')
    affected_task: AffectTask = col('AffectActionTypeID')

    @property
    def affected_group_action(self):
        return self._group_actions[(self.affected_group_id, self.affected_action_id)]


@dataclass
class OffsetAffect(ActionAffect):
    offset: float = col('AffectOffset')


def require_true(val):
    if val:
        return val
    raise ColumnMissing('MarkDoneAffect requires column AffectAutoComplete to be true')


@dataclass
class MarkDoneAffect(ActionAffect):
    auto_complete :bool = col('AffectAutoComplete', parser=require_true)

@dataclass
class CreateActionAffect(Affect):
    created_group_id: int = col('CreateActionActionListGroupDefID')
    created_action_id: int = col('CreateActionActionDefID')

    @property
    def affected_group_action(self):
        return self._group_actions[(self.created_group_id, self.created_action_id)]


@dataclass
class CreateGroupAffect(Affect):
    # What does CreateGroupActionListGroupDefActionTypeID mean here?
    created_group_id: int = col('CreateGroupActionListGroupDefID')

affect_types = [OffsetAffect, MarkDoneAffect, CreateActionAffect, CreateGroupAffect]

@dataclass(unsafe_hash=True)
class GroupAction(GroupActionProperties):
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')
    affects: List[Affect] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return escape_name('Group ' + self.group.name + ' Action ' + self.action.name)


@dataclass
class Group:
    id: int = col('ActionListGroupDefID')
    name: str = col('ActionListGroupName')
    optional: bool = col('Optional')
    actions: List[GroupAction] = field(default_factory=list)


class Trigger(NamedTuple):
    pass


@dataclass
class ActionList:
    groups : List[Group]
    triggers : List[Trigger]


def load_action_list(conn, action_list_id):
    @contextmanager
    def execute(sql, params=None):
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            yield cursor

    def fetchone(sql, params=None):
        with execute(sql, params) as cursor:
            return cursor.fetchone()

    def fetchall(sql, params=None):
        with execute(sql, params) as cursor:
            return cursor.fetchall()

    class Cache(dict):
        def __init__(self, load_fn):
            self.load_fn = load_fn

        def __missing__(self, key):
            self[key] = self.load_fn(key)
            return self[key]

    def load_email(email_id):
        row = fetchone('SELECT * FROM ActionEmailTemplate WHERE ActionEmailTemplateID=%s', email_id)
        return create_from_db(Email, row)

    def load_action(action_id):
        row = fetchone('''SELECT * FROM ActionDef AS ad WHERE ad.ActionDefID=%s''', action_id)
        action = create_from_db(Action, row)
        rows = fetchall(
            'SELECT * FROM ActionDefActionEmailTemplateRel WHERE ActionDefID=%s', action_id
        )
        action.emails = [load_email(row['ActionEmailTemplateID']) for row in rows]
        return action

    actions = Cache(load_action)
    group_actions = {}

    def load_affects(group_id, action_id):
        rows = fetchall(
            '''SELECT * FROM ActionGroupAffectDef
                WHERE ActionListGroupDefID=%s AND ActionDefID=%s ORDER BY AffectOrder''',
            (group_id, action_id)
        )
        for affect in rows:
            found = []
            for t in affect_types:
                try:
                    found.append(create_from_db(t, affect))
                except ColumnMissing:
                    continue
            yield from found

    def _setup_group_action_properties_fields(gap):
        gap._actions = actions
        gap._groups = groups_by_id
        gap._group_actions = group_actions
        return gap

    def load_group_action(group, row):
        ga = _setup_group_action_properties_fields(create_from_db(GroupAction, row))
        group_actions[(ga.group_id, ga.action_id)] = ga
        ga.affects = [_setup_group_action_properties_fields(a) for a in load_affects(group.id, ga.action.id)]
        return ga

    rows = fetchall(
        '''SELECT * FROM ActionListGroupsDef AS algs
            JOIN ActionListGroupDef AS alg ON alg.ActionListGroupDefID = algs.ActionListGroupDefID
            WHERE algs.ActionListDefID=%s ORDER BY GroupOrder''', action_list_id
    )
    groups = [create_from_db(Group, row) for row in rows]
    groups_by_id = {g.id:g for g in groups}
    for g in groups:
        rows = fetchall(
            '''SELECT * FROM ActionListGroupActionDef
                WHERE ActionListGroupDefID=%s ORDER BY ActionOrder''', g.id
        )
        g.actions = [load_group_action(g, r) for r in rows]
    affected_group_actions = set()
    for g in groups:
        for ga in g.actions:
            for a in ga.affects:
                affected_group_actions.add(a.affected_group_action)

    for g in groups:
        for ga in g.actions[:]:
            if not ga in affected_group_actions and not ga.affects:
                g.actions.remove(ga)

    return ActionList(groups, [])


def _get_external_trigger_affects(cursor):
    cursor.execute(
        '''SELECT * FROM ActionListGroupExternalTriggerAffectsDef AS tad
            LEFT JOIN ExternalActionDef AS ead ON
                ead.ExternalActionDefID = tad.ExternalActionDefID''',
    )
    return _extract_rows(cursor)


name_prefix = re.compile('^\w+: ')

def generate_digraph_from_action_list(action_list_def_id=ACTION_LIST_DEF_ID):
    with _connect_to_db() as conn, conn.cursor(as_dict=True) as cursor:
        action_list = load_action_list(conn, action_list_def_id)

    yield 'digraph G {'
    for group in action_list.groups:
        for group_action in group.actions:
            yield str(Vertex(name_prefix.sub('', group_action.action.name), shape='box', name=group_action.node_name))
            for affect in group_action.affects:
                yield f'{group_action.node_name} -> {affect.affected_group_action.node_name}'
            for email in group_action.action.emails:
                yield str(Vertex(email.name, shape='oval', fill_color='cornflowerblue', name=email.node_name))
                yield f'{group_action.node_name} -> {email.node_name}'

    yield '}'

if __name__ == '__main__':
    print('\n'.join(generate_digraph_from_action_list()))
