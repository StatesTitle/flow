from typing import Dict, List, Tuple

from dataclasses import dataclass, field

from resware_model import Task, Models, build_models
from settings import ACTION_LIST_DEF_ID


class Affect:
    def _bind(self, actionarium):
        raise NotImplementedError


@dataclass
class AffectTaskAffect(Affect):
    group_id: int
    action_id: int
    task: Task

    def _bind(self, actionarium):
        self.action = actionarium.actions[(self.group_id, self.action_id)]


@dataclass
class CompleteActionAffect(AffectTaskAffect):
    pass


@dataclass
class OffsetActionAffect(AffectTaskAffect):
    offset: float


@dataclass
class CreateActionAffect(Affect):
    group_id :int
    action_id: int

    def _bind(self, actionarium):
        self.action = actionarium.actions[(self.group_id, self.action_id)]


@dataclass(frozen=True)
class ExternalAction:
    id: int
    name: str


@dataclass(frozen=True)
class DocumentAdded(ExternalAction):
    document_type_id: int
    document_name: str


@dataclass(frozen=True)
class ActionEventReceived(ExternalAction):
    action_event_id: int
    action_event_name: str


@dataclass
class Trigger:
    affect: Affect
    external_action: ExternalAction


@dataclass
class Email:
    name: str
    task: Task


@dataclass
class Action:
    action_id: int
    group_id: int
    name: str
    display_name: str
    description: str
    emails: List[Email] = field(default_factory=list, compare=False)
    affects: List[Affect] = field(default_factory=list, compare=False)


@dataclass
class Group:
    id: int
    name: str
    optional: bool
    actions: List[Action] = field(default_factory=list, compare=False)
    triggers: List[Trigger] = field(default_factory=list, compare=False)


@dataclass
class ActionList:
    name: str
    groups: List[Group] = field(default_factory=list, compare=False)


@dataclass
class Actionarium:
    models: Models
    action_list: ActionList
    actions: Dict[Tuple[int, int], Action] = field(default_factory=dict, compare=False)
    groups: Dict[int, Group] = field(default_factory=dict, compare=False)
    external_actions: Dict[ExternalAction, ExternalAction] = field(default_factory=dict, compare=False)


def _build_external_action(actionarium, model_trigger):
    name = actionarium.models.external_actions[model_trigger.external_action_id].name
    if model_trigger.document_type_id is not None:
        doc = actionarium.models.document_types[model_trigger.document_type_id]
        external_action = DocumentAdded(model_trigger.external_action_id, name, doc.id, doc.name)
    elif model_trigger.action_event_id is not None:
        ae = actionarium.models.action_events[model_trigger.action_event_id]
        external_action = ActionEventReceived(model_trigger.external_action_id, name, ae.id, ae.name)
    else:
        external_action = ExternalAction(model_trigger.document_type_id, name)
    if external_action in actionarium.external_actions:
        return actionarium.external_actions[external_action]
    actionarium.external_actions[external_action] = external_action
    return external_action


def _build_affects(model_affect):
    if model_affect.affected_group_id is not None:
        if model_affect.offset is not None:
            yield OffsetActionAffect(model_affect.affected_group_id, model_affect.affected_action_id, model_affect.affected_task, model_affect.offset)
        if model_affect.auto_complete:
            yield CompleteActionAffect(model_affect.affected_group_id, model_affect.affected_action_id, model_affect.affected_task)
    if model_affect.created_group_id is not None:
        yield CreateActionAffect(model_affect.created_group_id, model_affect.created_action_id)


def _build_triggers(actionarium, model_trigger):
    external_action = _build_external_action(actionarium, model_trigger)
    for affect in _build_affects(model_trigger):
        yield Trigger(affect, external_action)


def _build_action(actionarium, model_group_action):
    model_action = actionarium.models.actions[model_group_action.action_id]
    action = Action(model_action.id, model_group_action.group_id, model_action.name, model_action.display_name, model_action.description)
    actionarium.actions[(action.group_id, action.action_id)] = action
    key = (action.group_id, action.action_id)
    if key in actionarium.models.group_action_affects:
        action.affects.extend(_build_affects(actionarium.models.group_action_affects[key]))
    for model_action_email in actionarium.models.action_emails[action.action_id]:
        action.emails.append(Email(actionarium.models.emails[model_action_email.email_id].name, model_action_email.task))
    return action


def _build_group(actionarium, model_alist_group):
    model_group = actionarium.models.groups[model_alist_group.group_id]
    group = Group(model_group.id, model_group.name, model_alist_group.optional)
    actionarium.groups[group.id] = group
    for model_group_action in actionarium.models.group_actions[group.id]:
        group.actions.append(_build_action(actionarium, model_group_action))
    for model_trigger in actionarium.models.triggers[group.id]:
        group.triggers.extend(_build_triggers(actionarium, model_trigger))
    return group


def build_action_list(models, action_list_id):
    model_alist = models.action_lists[action_list_id]

    # Build the structure of all the groups, actions, affects, triggers, and emails
    alist = ActionList(model_alist.name)
    actionarium = Actionarium(models, alist)
    for model_alist_group in models.action_list_groups[action_list_id]:
        alist.groups.append(_build_group(actionarium, model_alist_group))

    # Hook affects to the action and group instances they affect
    for group in alist.groups:
        for trigger in group.triggers:
            trigger.affect._bind(actionarium)
        for action in group.actions:
            for affect in action.affects:
                affect._bind(actionarium)

    return alist


if __name__ == '__main__':
    alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    print(alist)
