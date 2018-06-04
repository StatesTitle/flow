import builtins
import enum

import pymssql

from contextlib import contextmanager
from typing import NamedTuple

from deps import Vertex, digraph
from settings import (
    RESWARE_DATABASE_NAME, RESWARE_DATABASE_PASSWORD, RESWARE_DATABASE_PORT,
    RESWARE_DATABASE_SERVER, RESWARE_DATABASE_USER, ACTION_LIST_DEF_ID, INCLUDE_TRIGGERS
)


@contextmanager
def _connect_to_db():
    with pymssql.connect(
        RESWARE_DATABASE_SERVER,
        RESWARE_DATABASE_USER,
        RESWARE_DATABASE_PASSWORD,
        RESWARE_DATABASE_NAME,
        port=RESWARE_DATABASE_PORT
    ) as conn:
        yield conn


def _query(conn, fn, **kwargs):
    with conn.cursor(as_dict=True) as cursor:
        return fn(cursor, **kwargs)


def _extract_rows(cursor):
    """Detach cursor, and return result set"""
    return [row for row in cursor]


def _get_action_list_group_by_action_list(cursor, action_list_def_id):
    cursor.execute(
        '''SELECT * FROM ActionListGroupsDef AS algs
            JOIN ActionListGroupDef AS alg ON alg.ActionListGroupDefID = algs.ActionListGroupDefID
            WHERE algs.ActionListDefID=%s ORDER BY GroupOrder''', action_list_def_id
    )
    return _extract_rows(cursor)


def _get_actions_by_action_list_group(cursor, action_list_group_def_id):
    cursor.execute(
        '''SELECT * FROM ActionListGroupActionDef AS algad
            JOIN ActionDef AS ad ON ad.ActionDefID = algad.ActionDefID
            WHERE algad.ActionListGroupDefID=%s ORDER BY ActionOrder''', action_list_group_def_id
    )
    return _extract_rows(cursor)


def _get_action_affects_by_action_list_group(cursor, action_list_group_def_id, action_def_id):
    cursor.execute(
        '''SELECT * FROM ActionGroupAffectDef
            WHERE ActionListGroupDefID=%s AND ActionDefID=%s ORDER BY AffectOrder''',
        (action_list_group_def_id, action_def_id)
    )
    return _extract_rows(cursor)


def _get_external_trigger_affects(cursor):
    cursor.execute(
        '''SELECT * FROM ActionListGroupExternalTriggerAffectsDef AS tad
            LEFT JOIN ExternalActionDef AS ead ON
                ead.ExternalActionDefID = tad.ExternalActionDefID''',
    )
    return _extract_rows(cursor)


def _get_action_emails_by_action(cursor, action_def_id):
    cursor.execute(
        '''SELECT * FROM ActionDefActionEmailTemplateRel AS adaetr
            JOIN ActionEmailTemplate AS aet ON
                adaetr.ActionEmailTemplateID = aet.ActionEmailTemplateID
            WHERE adaetr.ActionDefID=%s''', action_def_id
    )
    return _extract_rows(cursor)


class AffectType(enum.IntEnum):
    DISPLAY_NAME = 0
    CREATE_ACTION = 1
    CREATE_ACTION_GROUP = 2
    AFFECTS_ACTION = 3
    SET_VALUE = 4
    SEND_XML = 5
    CREATE_RECORDING_DOCUMENT = 6
    CREATE_CURATIVE = 7
    MARK_CURATIVE_INTERNALLY_CLEARED = 8


class AffectColumnOperator(enum.Enum):
    AND = 'all'
    OR = 'any'


class AffectColumns(NamedTuple):
    required: list
    optional: list = None
    required_operator: AffectColumnOperator = AffectColumnOperator.AND

    @staticmethod
    def is_affect(affect_type, columns, required, required_operator):
        operator = builtins.getattr(builtins, required_operator.value)
        return operator([columns.get(column) for column in required])


AffectTypeToAffectColumnsMapping = {
    AffectType.DISPLAY_NAME:
    AffectColumns(['DisplayName']),
    AffectType.CREATE_ACTION:
    AffectColumns(['CreateActionActionListGroupDefID', 'CreateActionActionDefID']),
    AffectType.CREATE_ACTION_GROUP:
    AffectColumns(['CreateGroupActionListGroupDefID', 'CreateGroupActionListGroupDefActionTypeID']),
    AffectType.AFFECTS_ACTION:
    AffectColumns(['AffectActionListGroupDefID', 'AffectActionDefID', 'AffectActionTypeID'],
                  ['AffectOverwrites', 'AffectOffset', 'AffectAutoComplete']),
    AffectType.SET_VALUE:
    AffectColumns(['AffectResWareActionDefValuesID']),
    AffectType.SEND_XML:
    AffectColumns(['XMLSchemaID'], ['XMLToPartnerTypeID', 'ActionEventDefID']),
    AffectType.CREATE_RECORDING_DOCUMENT:
    AffectColumns(['RecordingDocumentTypeID']),
    AffectType.CREATE_CURATIVE:
    AffectColumns(
        ['CreateTitleReviewTypeID', 'CreatePolicyCurativeTypeID'],
        ['CreateTitleReviewTypeOnlyIfNotExists', 'CreatePolicyCurativeTypeOnlyIfNotExists'],
        AffectColumnOperator.OR
    ),
    AffectType.MARK_CURATIVE_INTERNALLY_CLEARED:
    AffectColumns(['ClearTitleReviewTypeID', 'ClearPolicyCurativeTypeID'], None,
                  AffectColumnOperator.OR)
}


def _get_affect_types(columns, mapping):
    return [
        affect_type for (affect_type, affect_mapping) in mapping.items() if AffectColumns.
        is_affect(affect_type, columns, affect_mapping.required, affect_mapping.required_operator)
    ]


def _identify_affect_action_dependencies(affects):
    actions = set()
    for affect in affects:
        affect_types = _get_affect_types(affect, AffectTypeToAffectColumnsMapping)
        for affect_type in affect_types:
            if affect_type in [
                AffectType.CREATE_ACTION, AffectType.AFFECTS_ACTION, AffectType.CREATE_ACTION_GROUP
            ]:
                actions.add((
                    affect['CreateActionActionListGroupDefID']
                    or affect['AffectActionListGroupDefID']
                    or affect['CreateGroupActionListGroupDefID'], affect['CreateActionActionDefID']
                    or affect['AffectActionDefID'] or None
                ))
    return actions


def _get_action_trigger_and_dependencies(actions):
    with _connect_to_db() as conn:
        triggers = _query(conn, _get_external_trigger_affects)
        for t in triggers:
            t['ActionDependency'] = _identify_affect_action_dependencies([t])
        return triggers


def _get_action_list_actions_and_dependencies(action_list_def_id):
    all_actions = {}
    with _connect_to_db() as conn:
        action_groups = _query(
            conn, _get_action_list_group_by_action_list, action_list_def_id=action_list_def_id
        )

        for ag in action_groups:
            actions = _query(
                conn,
                _get_actions_by_action_list_group,
                action_list_group_def_id=ag['ActionListGroupDefID']
            )

            # Create a map
            actions = {(ag['ActionListGroupDefID'], a['ActionDefID']): a for a in actions}
            for k, a in actions.items():
                if k not in all_actions:
                    all_actions[k] = a
                a['ActionGroupAffectDef'] = _query(
                    conn,
                    _get_action_affects_by_action_list_group,
                    action_list_group_def_id=ag['ActionListGroupDefID'],
                    action_def_id=a['ActionDefID']
                )
                a['ActionGroupAffectDefActions'] = _identify_affect_action_dependencies(
                    a['ActionGroupAffectDef']
                )
                a['ActionDefActionEmailTemplateRel'] = _query(
                    conn, _get_action_emails_by_action, action_def_id=a['ActionDefID']
                )
    return all_actions


def _build_vertex_from_action(action, depends_on=set()):
    return Vertex(action['DisplayName'], 'ResWare', 'Unknown', depends_on)


def _build_vertex_from_trigger(trigger, depends_on=set()):
    return Vertex(trigger['Name'], 'ResWare-Trigger', 'Unknown', depends_on, fill_color='grey')


def _build_vertex_from_email(email, depends_on=set()):
    return Vertex(
        f'Email: {email["ActionEmailTemplateName"]}',
        'ResWare-Email',
        'Unknown',
        depends_on,
        fill_color='cornflowerblue'
    )


class build_vertices:
    def __init__(self):
        self.collection = {}

    def get_vertex(self, key):
        return self.collection[key] if key in self.collection else None

    def __call__(self, key, builder_fn, entity, depends_on=set()):
        vertex = self.get_vertex(key)
        if not vertex:
            vertex = self.collection[key] = builder_fn(entity, depends_on)
        if depends_on:
            vertex.depends_on |= depends_on
        return vertex


def _build_dependencies(
    vertices, actions, entity_key, entity, dependencies, email_actions, vertex_builder_fn
):
    skipped_dependencies = []
    vertex = vertices(entity_key, vertex_builder_fn, entity)
    for dependency_key in dependencies:
        if dependency_key not in actions:
            skipped_dependencies.append(dependency_key)
        else:
            vertices(dependency_key, vertex_builder_fn, actions[dependency_key], set([vertex]))
    for email_action in email_actions:
        vertices(
            email_action['ActionEmailTemplateName'], _build_vertex_from_email, email_action,
            set([vertex])
        )
    return skipped_dependencies


def _add_notes(skipped_action_deps, skipped_trigger_deps):
    def _print_note(name, label):
        return f'{name}[label="{label}", shape="note", style="filled", fillcolor="yellow"]'

    if skipped_action_deps:
        yield _print_note(
            'skipped_action_deps', f'Skipped Action Dependencies:{skipped_action_deps}'
        )
    if skipped_trigger_deps:
        yield _print_note(
            'skipped_trigger_deps', f'Skipped Trigger Dependencies:{skipped_trigger_deps}'
        )


def generate_digraph_from_action_list(action_list_def_id=ACTION_LIST_DEF_ID):
    skipped_action_dependencies = []
    skipped_trigger_dependencies = []
    all_actions = _get_action_list_actions_and_dependencies(action_list_def_id)
    vertices = build_vertices()
    for action_key, action in all_actions.items():
        skipped_action_dependencies.extend(
            _build_dependencies(
                vertices, all_actions, action_key, action, action['ActionGroupAffectDefActions'],
                action['ActionDefActionEmailTemplateRel'], _build_vertex_from_action
            )
        )
    if INCLUDE_TRIGGERS:
        triggers = _get_action_trigger_and_dependencies(all_actions)
        for trigger in triggers:
            skipped_trigger_dependencies.extend(
                _build_dependencies(
                    vertices, all_actions, ('ExternalTrigger', trigger['ExternalActionDefID']),
                    trigger, trigger['ActionDependency'], _build_vertex_from_trigger
                )
            )

    added_note = False
    for line in digraph([
        vertex for vertex in vertices.collection.values() if len(vertex.depends_on)
    ]):
        yield line
        if not added_note:
            added_note = True
            yield from _add_notes(skipped_action_dependencies, skipped_trigger_dependencies)


if __name__ == '__main__':
    print('\n'.join(generate_digraph_from_action_list()))
