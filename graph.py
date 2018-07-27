"""Takes the raw ResWare data from resware_model and turns that into a connected graph of objects

Allows for the conversion of that graph into a dot language digraph

For the dataclasses below, we've made them frozen when they need a __hash__ method to be put into a set or dict. All of
the instances should be immutable after build_action_list returns, but we're not marking as frozen unless necessary to
keep from dealing with setting compare=False on fields and how dataclass overrides setattr if frozen is true"""
import re
from typing import List, Set

from dataclasses import dataclass, field

from deps import Vertex, escape_name
from resware_model import Task, build_models
from settings import ACTION_LIST_DEF_ID


def _node_name(*components):
    # Prepend an 'N' for 'node' in case the first component starts with a number, which is a warning in dot
    return escape_name('N' + ' '.join([str(c) for c in components]))


@dataclass
class Affect:
    group_id: int
    action_id: int


@dataclass
class AffectTaskAffect(Affect):
    task: Task


@dataclass
class CompleteActionAffect(AffectTaskAffect):
    pass


@dataclass
class OffsetActionAffect(AffectTaskAffect):
    offset: float


@dataclass
class CreateActionAffect(Affect):
    pass


@dataclass(frozen=True)
class ExternalAction:
    """Something happening outside of ResWare that ResWare can detect and use to trigger an affect

    There are a fair number of specific actions that are instances of this class, and then for document addition and
    action events receipt, we create an instance of the subclasses below"""
    id: int
    name: str

    @property
    def label(self):
        return self.name

    @property
    def node_name(self):
        return _node_name(self.name, self.id)

    @property
    def dot_attrs(self):
        return {'fillcolor': '#a6cee3', 'style': 'filled'}


@dataclass(frozen=True)
class DocumentAdded(ExternalAction):
    document_type_id: int
    document_name: str

    @property
    def label(self):
        return self.document_name + ' Added'

    @property
    def node_name(self):
        return _node_name(self.document_name, self.id, self.document_type_id)

    @property
    def dot_attrs(self):
        return {'fillcolor': '#b2df8a', 'style': 'filled'}


@dataclass(frozen=True)
class ActionEventReceived(ExternalAction):
    action_event_id: int
    action_event_name: str

    @property
    def label(self):
        return "Event: " + self.action_event_name

    @property
    def node_name(self):
        return _node_name(self.action_event_name, self.id, self.action_event_id)

    @property
    def dot_attrs(self):
        return {'fillcolor': '#1f78b4', 'style': 'filled', 'fontcolor': 'white'}


@dataclass
class Trigger:
    """A combination of an external action that ResWare detects and the affect it performs when it detects it"""
    affect: Affect
    external_action: ExternalAction


@dataclass
class Email:
    """An email template that's sent on the start or completion of an action"""
    action_id: int
    group_id: int
    name: str
    task: Task

    @property
    def node_name(self):
        return _node_name(self.name, self.group_id, self.action_id)

    @property
    def dot_attrs(self):
        return {'fillcolor': '#33a02c', 'style': 'filled', 'fontcolor': 'white'}


@dataclass(frozen=True)
class Action:
    """An action in a group with the emails it sends and the affects its start or completion cause

    ResWare itself has separate concepts for 'global actions' and instances of actions in a group. We only represent
    the instance on a group here. That means it's possible for the same global action to be in the graph multiple times.
    If that's the case, it'll always be a separate instance in the group. Since the affects are on the instance anyway,
    the global action concept isn't very useful."""
    action_id: int
    group_id: int
    name: str = field(compare=False)
    display_name: str = field(compare=False)
    description: str = field(compare=False)
    emails: List[Email] = field(default_factory=list, compare=False)
    affects: List[Affect] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return _node_name(self.name, self.group_id, self.action_id)


@dataclass
class Group:
    """A group of actions and triggers that can be added to a file"""
    id: int
    name: str
    optional: bool
    actions: List[Action] = field(default_factory=list, compare=False)
    triggers: List[Trigger] = field(default_factory=list, compare=False)


@dataclass
class ActionList:
    name: str
    groups: List[Group] = field(default_factory=list, compare=False)


def _build_external_action(models, model_trigger):
    name = models.external_actions[model_trigger.external_action_id].name
    if model_trigger.document_type_id is not None:
        doc = models.document_types[model_trigger.document_type_id]
        return DocumentAdded(model_trigger.external_action_id, name, doc.id, doc.name)
    elif model_trigger.action_event_id is not None:
        ae = models.action_events[model_trigger.action_event_id]
        return ActionEventReceived(model_trigger.external_action_id, name, ae.id, ae.name)
    else:
        return ExternalAction(model_trigger.external_action_id, name)


def _build_affects(model_affect):
    if model_affect.affected_group_id is not None:
        if model_affect.offset is not None:
            yield OffsetActionAffect(
                model_affect.affected_group_id, model_affect.affected_action_id,
                model_affect.affected_task, model_affect.offset
            )
        if model_affect.auto_complete:
            yield CompleteActionAffect(
                model_affect.affected_group_id, model_affect.affected_action_id,
                model_affect.affected_task
            )
    if model_affect.created_group_id is not None:
        yield CreateActionAffect(model_affect.created_group_id, model_affect.created_action_id)


def _build_triggers(models, model_trigger):
    external_action = _build_external_action(models, model_trigger)
    for affect in _build_affects(model_trigger):
        yield Trigger(affect, external_action)


def _build_action(models, model_group_action):
    model_action = models.actions[model_group_action.action_id]
    action = Action(
        model_action.id, model_group_action.group_id, model_action.name, model_action.display_name,
        model_action.description
    )
    key = (action.group_id, action.action_id)
    for affect in models.group_action_affects[key]:
        action.affects.extend(_build_affects(affect))
    for model_action_email in models.action_emails[action.action_id]:
        action.emails.append(
            Email(
                action.group_id, action.action_id, models.emails[model_action_email.email_id].name,
                model_action_email.task
            )
        )
    return action


def _build_group(models, model_alist_group):
    model_group = models.groups[model_alist_group.group_id]
    group = Group(model_group.id, model_group.name, model_alist_group.optional)
    for model_group_action in models.group_actions[group.id]:
        group.actions.append(_build_action(models, model_group_action))
    for model_trigger in models.triggers[group.id]:
        group.triggers.extend(_build_triggers(models, model_trigger))
    return group


def build_action_list(models, action_list_id):
    model_alist = models.action_lists[action_list_id]

    # Build the structure of all the groups, actions, affects, triggers, and emails
    result = ActionList(model_alist.name)
    for model_alist_group in models.action_list_groups[action_list_id]:
        result.groups.append(_build_group(models, model_alist_group))

    def key(id_holder):
        return id_holder.group_id, id_holder.action_id

    # Build a dict from (group_id, action_id) to action for all actions in the action list
    actions = {}
    for group in result.groups:
        for action in group.actions:
            actions[key(action)] = action

    # Hook affects to the action instances they affect. Do this in a second pass so all the instances will exist from
    # the first pass.
    for group in result.groups:
        for trigger in group.triggers:
            trigger.affect.action = actions[key(trigger.affect)]
        for action in group.actions:
            for affect in action.affects:
                affect.action = actions[key(affect)]

    return result


name_prefix = re.compile('^\w+: ')


def _walk(action: Action, reachable: Set[Action]):
    if action in reachable:
        return
    reachable.add(action)
    for affect in action.affects:
        _walk(affect.action, reachable)


def generate_digraph_from_action_list(action_list: ActionList, roots: Set[Action] = None):
    if roots is None:
        roots = find_roots(action_list)

    # Find the actions reachable from the given roots
    reachable = set()
    for root in roots:
        _walk(root, reachable)

    yielded = set()

    def emit(obj):
        # We're not distinguishing offset vs start vs complete affects in the arrows yet. That leads to dupe arrows, so
        # filter them out here
        line = str(obj)
        if line in yielded:
            return
        yielded.add(line)
        yield line

    yield 'digraph G {'
    for group in action_list.groups:
        for trigger in group.triggers:
            if trigger.affect.action not in reachable:
                continue
            yield from emit(
                Vertex(
                    trigger.external_action.label,
                    name=trigger.external_action.node_name,
                    **trigger.external_action.dot_attrs
                )
            )
            yield from emit(
                f'{trigger.external_action.node_name} -> {trigger.affect.action.node_name}'
            )
        for action in group.actions:
            if action not in reachable:
                continue
            yield from emit(
                Vertex(name_prefix.sub('', action.name), shape='box', name=action.node_name)
            )
            for affect in action.affects:
                yield from emit(f'{action.node_name} -> {affect.action.node_name}')
            for email in action.emails:
                yield from emit(str(Vertex(email.name, name=email.node_name, **email.dot_attrs)))
                yield from emit(f'{action.node_name} -> {email.node_name}')
    yield '}'


def find_roots(action_list, external_actions=None):
    """Finds actions affected by the given external actions"""
    if external_actions is None:
        external_actions = {121: 'Document Added', 14: 'File Created', 154: 'Received Action Event'}
    roots = set()
    for group in action_list.groups:
        for trigger in group.triggers:
            if trigger.external_action.id in external_actions:
                roots.add(trigger.affect.action)
    return roots


if __name__ == '__main__':
    alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    print('\n'.join(generate_digraph_from_action_list(alist)))
