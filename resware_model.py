"""Raw in-memory representations of the data in ResWare's db relating to action list definitions and friends

We make it easy to load all of that at once to make it easier to create an object graph without having to do
complicated queries to only fetch the bits we once. Since the action lists will never be 1000s and 1000s of steps,
loading all of this shouldn't be prohibitive."""
import enum

from dataclasses import dataclass

from database import col, tableclass, _connect_to_db, load


class Task(enum.IntEnum):
    START = 1
    COMPLETE = 2

# All actions in a group in ResWare have "start" and "complete" tasks. Those tasks can be marked "done". All affects
# happen on either start or complete being marked done.  That's tracked in the ActionTypeID column in the
# ActionGroupAffectDef and ActionListGroupExternalTriggerAffectsDef tables. If ActionTypeID is 1, that means the
# affect happens on on the group action's start being marked done. If it's 2, it means the affect happens on the
# complete being marked done.
#
# What an affect does is determined by which additional columns are set on the row in ActionGroupAffectDef:
# 1. If AffectActionListGroupDefID and AffectActionDefID are set,  another GroupAction is being changed.
#    AffectActionTypeID determines if it's the start or complete task that's being changed, just like with
#    ActionTypeID. It can do one of two things:
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


@dataclass
class Affect:
    affected_group_id: int = col('AffectActionListGroupDefID', nullable=True)
    affected_action_id: int = col('AffectActionDefID', nullable=True)
    affected_task: Task = col('AffectActionTypeID', nullable=True)
    offset: float = col('AffectOffset', nullable=True)
    auto_complete: bool = col('AffectAutoComplete', nullable=True)
    created_group_id: int = col('CreateActionActionListGroupDefID', nullable=True)
    created_action_id: int = col('CreateActionActionDefID', nullable=True)
    # TODO CreateGroupActionListGroupDefID


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


@tableclass('ActionGroupAffectDef', lookup=('group_id', 'action_id'), one_to_many=True)
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
