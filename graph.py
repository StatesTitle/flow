"""Takes the raw ResWare data from resware_model and turns that into a connected graph of objects

Allows for the conversion of that graph into a dot language digraph

For the dataclasses below, we've made them frozen when they need a __hash__ method to be put into a set or dict. All of
the instances should be immutable after build_action_list returns, but we're not marking as frozen unless necessary to
keep from dealing with setting compare=False on fields and how dataclass overrides setattr if frozen is true"""
import re
from collections import defaultdict

from typing import List, Set, Tuple, Dict

from dataclasses import asdict, dataclass, field, InitVar

from deps import Vertex, escape_name
from resware_model import Task, build_models, PartnerType
from settings import ACTION_LIST_DEF_ID


def _node_name(*components):
    # Prepend an 'N' for 'node' in case the first component starts with a number, which is a warning in dot
    return escape_name('N' + ' '.join([str(c) for c in components]))


class GroupLookupMixin:
    @property
    def group(self):
        return self._ctx.groups[self.group_id]

class ActionLookupMixin:
    @property
    def action(self):
        return self._ctx.actions[(self.group_id, self.action_id)]

@dataclass
class Context:
    actions: Dict[Tuple[int, int], 'Action'] = field(default_factory=dict)
    groups: Dict[int, 'Group'] = field(default_factory=dict)


@dataclass(frozen=True)
class CtxHolder:
    _ctx: InitVar[Context] = field(compare=False)


@dataclass(frozen=True)
class Affect(CtxHolder, ActionLookupMixin):
    type: str
    group_id: int
    action_id: int


@dataclass(frozen=True)
class AffectTaskAffect(Affect):
    task: Task


@dataclass(frozen=True)
class CompleteActionAffect(AffectTaskAffect):
    @property
    def desc(self):
        return f'{self.task.name} {self.action.path}'



@dataclass(frozen=True)
class OffsetActionAffect(AffectTaskAffect):
    offset: float

    @property
    def desc(self):
        return f'Offset {self.task.name} on {self.action.path} by {self.offset} hours'


@dataclass(frozen=True)
class CreateActionAffect(Affect):
    @property
    def desc(self):
        return f'Create {self.action.path}'


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


@dataclass(frozen=True)
class Email(CtxHolder, ActionLookupMixin):
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
class Action(CtxHolder, GroupLookupMixin):
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
    hidden: bool = field(compare=False)
    dynamic: bool = field(compare=False)
    start_emails: List[Email] = field(default_factory=list, compare=False)
    complete_emails: List[Email] = field(default_factory=list, compare=False)
    start_affects: List[Affect] = field(default_factory=list, compare=False)
    complete_affects: List[Affect] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return _node_name(self.name, self.group_id, self.action_id)

    @property
    def path(self):
        return f'{self.group.name}/{self.name}'


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


def _build_affects(model_affect, ctx):
    if model_affect.affected_group_id is not None:
        if model_affect.offset is not None:
            yield OffsetActionAffect(ctx, 'offset',
                model_affect.affected_group_id, model_affect.affected_action_id,
                model_affect.affected_task, model_affect.offset
            )
        if model_affect.auto_complete:
            yield CompleteActionAffect(ctx, 'complete',
                model_affect.affected_group_id, model_affect.affected_action_id,
                model_affect.affected_task
            )
    if model_affect.created_group_id is not None:
        yield CreateActionAffect(ctx, 'create', model_affect.created_group_id, model_affect.created_action_id)


def _build_triggers(models, model_trigger, ctx):
    external_action = _build_external_action(models, model_trigger)
    for affect in _build_affects(model_trigger, ctx):
        yield Trigger(affect, external_action)


def _build_action(models, model_group_action, ctx):
    model_action = models.actions[model_group_action.action_id]
    action = Action(
        ctx, model_action.id, model_group_action.group_id, model_action.name, model_action.display_name,
        model_action.description, model_action.hidden, model_group_action.dynamic
    )
    key = (action.group_id, action.action_id)
    ctx.actions[key] = action
    for affect in models.group_action_affects[key]:
        if affect.task == Task.START:
            action.start_affects.extend(_build_affects(affect, ctx))
        if affect.task == Task.COMPLETE:
            action.complete_affects.extend(_build_affects(affect, ctx))

    for model_action_email in models.action_emails[action.action_id]:
        if model_action_email.task == Task.START:
            action.start_emails.append(
                Email(ctx,
                    action.group_id, action.action_id, models.emails[model_action_email.email_id].name,
                    model_action_email.task
                )
            )
        if model_action_email.task == Task.COMPLETE:
            action.complete_emails.append(
                Email(ctx,
                    action.group_id, action.action_id, models.emails[model_action_email.email_id].name,
                    model_action_email.task
                )
            )
    return action


def _build_group(models, model_alist_group, ctx):
    model_group = models.groups[model_alist_group.group_id]
    group = Group(model_group.id, model_group.name, model_alist_group.optional)
    ctx.groups[group.id] = group
    for model_group_action in models.group_actions[group.id]:
        group.actions.append(_build_action(models, model_group_action, ctx))
    for model_trigger in models.triggers[group.id]:
        group.triggers.extend(_build_triggers(models, model_trigger, ctx))
    return group


def build_action_list(models, action_list_id):
    model_alist = models.action_lists[action_list_id]

    # Build the structure of all the groups, actions, affects, triggers, and emails
    ctx = Context()
    result = ActionList(model_alist.name)
    for model_alist_group in models.action_list_groups[action_list_id]:
        result.groups.append(_build_group(models, model_alist_group, ctx))

    return result


def _defaultdict_list_factory():
    return defaultdict(list)


@dataclass
class Partner:
    id: int
    name: str
    types: List[PartnerType] = field(default_factory=list, compare=False)
    auto_adds: Dict[PartnerType, List[Tuple['Partner', PartnerType]]] = field(default_factory=_defaultdict_list_factory, compare=False)


def build_partners(models):
    partners = {}
    for model_partner in models.partners.values():
        partner = Partner(model_partner.id, model_partner.name)
        for model_partner_type in models.partners_types[partner.id]:
            partner.types.append(models.partner_types[model_partner_type.type_id])
        partners[partner.id] = partner

    for partner in partners.values():
        for model_auto_add in models.partners_auto_adds[partner.id]:
            our_model_type = models.partner_types[model_auto_add.type_id]
            to_add = (partners[model_auto_add.auto_add_id], models.partner_types[model_auto_add.auto_add_type_id])
            partner.auto_adds[our_model_type].append(to_add)
    return partners, models.partner_types

name_prefix = re.compile('^\w+: ')


def _walk(action: Action, reachable: Set[Action]):
    if action in reachable:
        return
    reachable.add(action)
    for affect in action.start_affects:
        _walk(affect.action, reachable)
    for affect in action.complete_affects:
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
            for affect in action.start_affects + action.complete_affects:
                yield from emit(f'{action.node_name} -> {affect.action.node_name}')
            for email in action.start_emails + action.complete_emails:
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
    models = build_models()
    #print(build_partners(models))
    alist = build_action_list(models, ACTION_LIST_DEF_ID)
#    import json
#    print(json.dumps(asdict(alist), indent='  '))
    for group in alist.groups:
        print('Group:', group.name)
        for trigger in group.triggers:
            print('  Trigger:', trigger.external_action.label, '->', trigger.affect.desc)
        for action in group.actions:
            print('  Action:', action.path)
            emails = action.start_emails + action.complete_emails
            if emails:
                print('    Emails:', ', '.join([email.name for email in emails]))
            affects = action.start_affects + action.complete_affects
            if affects:
                print('    Affects:')
                for affect in affects:
                    print('   ', affect.desc)

    #print('\n'.join(generate_digraph_from_action_list(alist)))
