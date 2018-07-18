import enum

from dataclasses import dataclass

from db import col, tableclass, _connect_to_db, load


class Task(enum.IntEnum):
    START = 1
    COMPLETE = 2


@dataclass
class Affect:
    affected_group_id: int = col('AffectActionListGroupDefID', nullable=True)
    affected_action_id: int = col('AffectActionDefID', nullable=True)
    affected_task: Task = col('AffectActionTypeID', nullable=True)
    offset: float = col('AffectOffset', nullable=True)
    auto_complete: bool = col('AffectAutoComplete', nullable=True)
    created_group_id: int = col('CreateActionActionListGroupDefID', nullable=True)
    created_action_id: int = col('CreateActionActionDefID', nullable=True)


@tableclass('ExternalActionDef')
class ExternalAction:
    id: int = col('ExternalActionDefID')
    name: str = col('Name')


@tableclass('ActionEventDef')
class ActionEvent:
    id: int = col('ActionEventDefID')
    name: str = col('Name')


@tableclass('DocumentType')
class DocumentType:
    id: int = col('DocumentTypeID')
    name: str = col('Name')


@tableclass('ActionEmailTemplate')
class Email:
    id: int = col('ActionEmailTemplateID')
    name: str = col('ActionEmailTemplateName')


def _email_start_complete_to_task(start_complete):
    return Task.COMPLETE if start_complete else Task.START


@tableclass('ActionDefActionEmailTemplateRel', lookup='action_id', one_to_many=True)
class ActionEmail:
    action_id: int = col('ActionDefID')
    email_id: int = col('ActionEmailTemplateID')
    task: Task = col('ActionStartComplete', parser=_email_start_complete_to_task)


@tableclass('ActionListGroupExternalTriggerAffectsDef', lookup='group_id', one_to_many=True)
class Trigger(Affect):
    external_action_id: int = col('ExternalActionDefID')
    group_id: int = col('ActionListGroupDefID')
    action_event_id: int = col('ActionEventDefID', nullable=True)
    document_type_id: int = col('DocumentTypeID', nullable=True)
    # TitleReviewTypeID, PolicyCurativeTypeID


@tableclass('ActionDef')
class Action:
    id: int = col('ActionDefID')
    name: str = col('Name')
    display_name: str = col('DisplayName')
    description: str = col('Description', nullable=True)


@tableclass('ActionListGroupActionDef', lookup='group_id', one_to_many=True)
class GroupAction:
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')


@tableclass('ActionListGroupDef')
class Group:
    id: int = col('ActionListGroupDefID')
    name: str = col('ActionListGroupName')


@tableclass('ActionGroupAffectDef', lookup=('group_id', 'action_id'))
class GroupActionAffect(Affect):
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')
    # TODO additional affect types


@tableclass('ActionListDef')
class ActionList:
    id: int = col('ActionListDefID')
    name: str = col('Name')

@tableclass('ActionListGroupsDef', one_to_many=True)
class ActionListGroups:
    id: int = col('ActionListDefId')
    group_id: int = col('ActionListGroupDefId')
    order: int = col('GroupOrder')
    optional: bool = col('Optional')


class Models:
    def __init__(self, conn):
        self.triggers = load(conn, Trigger)
        self.external_actions = load(conn, ExternalAction)
        self.emails = load(conn, Email)
        self.action_emails = load(conn, ActionEmail)
        self.action_events = load(conn, ActionEvent)
        self.document_types = load(conn, DocumentType)
        self.actions = load(conn, Action)
        self.group_actions = load(conn, GroupAction)
        self.groups = load(conn, Group)
        self.group_action_affects = load(conn, GroupActionAffect)
        self.action_lists = load(conn, ActionList)
        self.action_list_groups = load(conn, ActionListGroups)


def build_models():
    with _connect_to_db() as conn:
        return Models(conn)

if __name__ == '__main__':
    build_models()
