"""Takes the raw ResWare data from resware_model and turns that into a connected graph of objects

Allows for the conversion of that graph into a dot language digraph

For the dataclasses below, we've made them unsafe_hash when they need a __hash__ method to be put into a set or dict. All of
the instances should be immutable after build_action_list returns, but we're not marking as frozen because we set _ctx in __post_init__"""

import re
import sys

from functools import wraps
from typing import Iterable, List, Set, Tuple, Dict

from dataclasses import asdict, dataclass, field, InitVar

from deps import Vertex, escape_name
from resware_model import Task, build_models, PartnerType
from settings import ACTION_LIST_DEF_ID


def _node_name(*components):
    # Prepend an 'N' for 'node' in case the first component starts with a number, which is a warning in dot
    return escape_name("N" + " ".join([str(c) for c in components]))


@dataclass
class Partner:
    id: int
    name: str
    types: List[PartnerType] = field(default_factory=list, compare=False)


class GroupLookupMixin:
    @property
    def group(self):
        return self._ctx.groups[self.group_id]


class ActionLookupMixin(GroupLookupMixin):
    @property
    def action(self):
        key = (self.group_id, self.action_id)
        return self._ctx.actions[key]


@dataclass
class Context:
    actions: Dict[Tuple[int, int], "Action"] = field(default_factory=dict)
    groups: Dict[int, "Group"] = field(default_factory=dict)


@dataclass(unsafe_hash=True)
class CtxHolder:
    _ctx: InitVar[Context]

    def __post_init__(self, ctx):
        self._ctx = ctx


@dataclass(unsafe_hash=True)
class Affect(CtxHolder, ActionLookupMixin):
    type: str
    group_id: int
    action_id: int

    @property
    def affected_name(self):
        return f"{self.action.name}"


@dataclass(unsafe_hash=True)
class AffectTaskAffect(Affect):
    task: Task


@dataclass(unsafe_hash=True)
class CompleteActionAffect(AffectTaskAffect):
    @property
    def affect(self):
        return f"{self.task.name}"

    @property
    def desc(self):
        return f"{self.task.name} {self.action.path}"


@dataclass(unsafe_hash=True)
class OffsetActionAffect(AffectTaskAffect):
    offset: float

    @property
    def affect(self):
        return f"Offset {self.task.name} by {self.offset} hours"

    @property
    def desc(self):
        return f"{self.affect} on {self.action.path}"


@dataclass(unsafe_hash=True)
class CreateActionAffect(Affect):
    @property
    def affect(self):
        return "Create Action"

    @property
    def desc(self):
        return f"Create Action {self.action.path}"


@dataclass(unsafe_hash=True)
class CreateGroupAffect(CtxHolder, GroupLookupMixin):
    type: str
    group_id: int

    @property
    def affect(self):
        return "Create Group"

    @property
    def desc(self):
        return f"Create Group {self.group.name}"

    @property
    def affected_name(self):
        return f"{self.group.name}"

    @property
    def action(self):
        # Somewhat arbitrarily say the action affected by creating a group is the first action
        # in the group. This gets the linkage in place in the graph
        return self.group.actions[0]


@dataclass(unsafe_hash=True)
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
        return {"fillcolor": "#a6cee3", "style": "filled"}

    @property
    def vertex(self):
        return Vertex(self.label, name=self.node_name, **self.dot_attrs)


@dataclass
class DocumentType:
    id: int
    name: str


@dataclass(unsafe_hash=True)
class DocumentAdded(ExternalAction):
    document: DocumentType

    @property
    def label(self):
        return self.document.name + " Added"

    @property
    def node_name(self):
        return _node_name(self.document.name, self.id, self.document.id)

    @property
    def dot_attrs(self):
        return {"fillcolor": "#b2df8a", "style": "filled"}


@dataclass(unsafe_hash=True)
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
        return {"fillcolor": "#1f78b4", "style": "filled", "fontcolor": "white"}


@dataclass
class Trigger:
    """A combination of an external action that ResWare detects and the affect it performs when it detects it"""

    affect: Affect
    external_action: ExternalAction


@dataclass
class Template:
    name: str
    filename: str
    document_type: DocumentType


@dataclass(unsafe_hash=True)
class Email(CtxHolder, ActionLookupMixin):
    """An email template that's sent on the start or completion of an action"""

    action_id: int
    group_id: int
    name: str
    subject: str
    body: str
    task: Task
    documents: List[DocumentType] = field(default_factory=list, compare=False)
    templates: List[DocumentType] = field(default_factory=list, compare=False)
    recipients: List[PartnerType] = field(default_factory=list, compare=False)
    required: List[Partner] = field(default_factory=list, compare=False)
    excluded: List[Partner] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return _node_name(self.name, self.group_id, self.action_id)

    @property
    def dot_attrs(self):
        return {"fillcolor": "#33a02c", "style": "filled", "fontcolor": "white"}

    @property
    def vertex(self):
        return Vertex(self.name, name=self.node_name, **self.dot_attrs)


@dataclass(unsafe_hash=True)
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
    required: List[Partner] = field(default_factory=list, compare=False)
    excluded: List[Partner] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return _node_name(self.name, self.group_id, self.action_id)

    @property
    def path(self):
        return f"{self.group.name}/{self.name}"

    @property
    def affects(self):
        return self.start_affects + self.complete_affects

    @property
    def vertex(self):
        return Vertex(name_prefix.sub("", self.name), shape="box", name=self.node_name)


@dataclass(unsafe_hash=True)
class Group:
    """A group of actions and triggers that can be added to a file"""

    id: int
    name: str
    optional: bool
    actions: List[Action] = field(default_factory=list, compare=False)
    triggers: List[Trigger] = field(default_factory=list, compare=False)
    required: List[Partner] = field(default_factory=list, compare=False)
    excluded: List[Partner] = field(default_factory=list, compare=False)

    @property
    def node_name(self):
        return _node_name(self.name, self.id)

    @property
    def vertex(self):
        return Vertex(self.name, shape="octagon", name=self.node_name)


@dataclass
class ActionList:
    name: str
    groups: List[Group] = field(default_factory=list, compare=False)


def _build_external_action(models, model_trigger):
    name = models.external_actions[model_trigger.external_action_id].name
    if model_trigger.document_type_id is not None:
        model_doc = models.document_types[model_trigger.document_type_id]
        doc = DocumentType(model_doc.id, model_doc.name)
        return DocumentAdded(model_trigger.external_action_id, name, doc)
    elif model_trigger.action_event_id is not None:
        ae = models.action_events[model_trigger.action_event_id]
        return ActionEventReceived(
            model_trigger.external_action_id, name, ae.id, ae.name
        )
    else:
        return ExternalAction(model_trigger.external_action_id, name)


def _build_affects(model_affect, ctx):
    if model_affect.affected_group_id is not None:
        if model_affect.offset is not None:
            yield OffsetActionAffect(
                ctx,
                "offset",
                model_affect.affected_group_id,
                model_affect.affected_action_id,
                model_affect.affected_task,
                model_affect.offset,
            )
        if model_affect.auto_complete:
            yield CompleteActionAffect(
                ctx,
                "complete",
                model_affect.affected_group_id,
                model_affect.affected_action_id,
                model_affect.affected_task,
            )
    if model_affect.created_action_group_id is not None:
        yield CreateActionAffect(
            ctx,
            "create_action",
            model_affect.created_action_group_id,
            model_affect.created_action_action_id,
        )
    if model_affect.created_group_id is not None:
        yield CreateGroupAffect(ctx, "create_group", model_affect.created_group_id)


def _build_triggers(models, model_trigger, ctx):
    external_action = _build_external_action(models, model_trigger)
    for affect in _build_affects(model_trigger, ctx):
        yield Trigger(affect, external_action)


def _build_document_type(models, document_type_id):
    model_doc = models.document_types[document_type_id]
    return DocumentType(model_doc.id, model_doc.name)


def _build_email(models, model_action_email, action, ctx):
    model_email = models.emails[model_action_email.email_id]
    email = Email(
        ctx,
        action.group_id,
        action.action_id,
        model_email.name,
        model_email.subject,
        model_email.body,
        model_action_email.task,
    )
    for model_email_doc in models.email_documents[model_action_email.email_id]:
        email.documents.append(
            _build_document_type(models, model_email_doc.document_type_id)
        )
    for model_email_template in models.email_templates[model_action_email.email_id]:
        model_template = models.templates[model_email_template.template_id]
        doc = _build_document_type(models, model_template.document_type_id)
        email.templates.append(
            Template(model_template.name, model_template.filename, doc)
        )
    for model_email_partner_type_recipient in models.email_partner_type_recipients[
        model_action_email.email_id
    ]:
        email.recipients.append(
            models.partner_types[model_email_partner_type_recipient.partner_type_id]
        )
    _add_partner_restrictions(
        models, email, models.email_partner_restrictions[model_action_email.email_id]
    )
    return email


def _build_action(models, model_group_action, ctx):
    model_action = models.actions[model_group_action.action_id]
    action = Action(
        ctx,
        model_action.id,
        model_group_action.group_id,
        model_action.name,
        model_action.display_name,
        model_action.description,
        model_action.hidden,
        model_group_action.dynamic,
    )
    key = (action.group_id, action.action_id)
    ctx.actions[key] = action
    for affect in models.group_action_affects[key]:
        if affect.task == Task.START:
            action.start_affects.extend(_build_affects(affect, ctx))
        if affect.task == Task.COMPLETE:
            action.complete_affects.extend(_build_affects(affect, ctx))

    for model_action_email in models.action_emails[action.action_id]:
        email = _build_email(models, model_action_email, action, ctx)
        if model_action_email.task == Task.START:
            action.start_emails.append(email)
        if model_action_email.task == Task.COMPLETE:
            action.complete_emails.append(email)

    _add_partner_restrictions(
        models, action, models.group_action_partner_restrictions[key]
    )

    return action


def _add_partner_restrictions(models, restricted, restrictions):
    for restriction in restrictions:
        partner = _build_partner(models, models.partners[restriction.partner_id])
        if restriction.include:
            restricted.required.append(partner)
        else:
            restricted.excluded.append(partner)


def _build_group(models, model_group, optional, ctx):
    group = Group(model_group.id, model_group.name, optional)
    ctx.groups[group.id] = group
    for model_group_action in models.group_actions[group.id]:
        group.actions.append(_build_action(models, model_group_action, ctx))
    for model_trigger in models.triggers[group.id]:
        group.triggers.extend(_build_triggers(models, model_trigger, ctx))
    _add_partner_restrictions(
        models, group, models.group_partner_restrictions[group.id]
    )
    return group


def build_action_list(models, action_list_id):
    model_alist = models.action_lists[action_list_id]

    # Build the structure of all the groups, actions, affects, triggers, and emails
    ctx = Context()

    # We build all the groups, not just the groups in the given action list. It's possible for
    # an affect to create a group or action in a group even if that group isn't directly in the
    # action list.
    #
    # For groups not in the action list, we mark them as optional just like other explicitly
    # optional groups
    nonoptional = set(
        g.group_id for g in models.action_list_groups[action_list_id] if not g.optional
    )
    for model_group in models.groups.values():
        _build_group(models, model_group, model_group.id not in nonoptional, ctx)

    # It's possible for a group to be completely empty. If that's the case, we'll never display
    # it as it has no actions. Affects can still reference that empty group though. To keep from
    # trying to display arrows to nowhere, remove those affects
    for group in ctx.groups.values():
        if len(group.actions) == 0 and len(group.triggers) == 0:
            for possibly_referencing_group in ctx.groups.values():
                if group == possibly_referencing_group:
                    continue
                for action in possibly_referencing_group.actions:
                    for affect in action.start_affects[:]:
                        if affect.group_id == group.id:
                            action.start_affects.remove(affect)
                    for affect in action.complete_affects[:]:
                        if affect.group_id == group.id:
                            action.complete_affects.remove(affect)

    # Now that we have a clean set of groups, create the action list with the ordered list of
    # groups that are directly in it
    result = ActionList(model_alist.name)
    for model_alist_group in models.action_list_groups[action_list_id]:
        result.groups.append(ctx.groups[model_alist_group.group_id])

    return ctx, result


def _build_partner(models, model_partner):
    partner = Partner(model_partner.id, model_partner.name)
    for model_partner_type in models.partners_types[partner.id]:
        partner.types.append(models.partner_types[model_partner_type.type_id])
    return partner


def build_partners(models):
    partners = {}
    for model_partner in models.partners.values():
        partners[model_partner.id] = _build_partner(models, model_partner)
    return partners, models.partner_types


name_prefix = re.compile("^\w+: ")


def _walk(action: Action, reachable: Set[Action]):
    if action is None or action in reachable:
        return
    reachable.add(action)
    for affect in action.start_affects:
        _walk(affect.action, reachable)
    for affect in action.complete_affects:
        _walk(affect.action, reachable)


def digraph(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        lines = ["digraph G {"]
        yielded = set()
        for obj in f(*args, **kwargs):
            # We're not distinguishing offset vs start vs complete affects in the arrows yet. That leads to dupe arrows, so
            # filter them out here
            line = str(obj)
            if line in yielded:
                continue
            yielded.add(line)
            lines.append(line)
        lines.append("}")
        return "\n".join(lines)

    return decorated_function


def find_incoming(groups: Iterable[Group], group: Group):
    incoming_group = set()
    incoming_action = set()
    for g in groups:
        if g == group:
            continue
        for act in g.actions:
            for aff in act.affects:
                if aff.group == group:
                    if aff.type == "create_group":
                        incoming_group.add(g)
                    elif aff.action is not None:
                        incoming_action.add((g, aff.action))
    return incoming_group, incoming_action


@digraph
def generate_digraph_from_group(groups: Iterable[Group], group: Group):
    incoming_group, incoming_action = find_incoming(groups, group)
    if len(incoming_group) > 0:
        for g in incoming_group:
            yield g.vertex
        yield group.vertex
        for g in incoming_group:
            yield f"{g.node_name} -> {group.node_name}"
    for g, _ in incoming_action:
        yield g.vertex
    for _, act in incoming_action:
        yield act.vertex
    for g, act in incoming_action:
        yield f"{g.node_name} -> {act.node_name}"
    for trigger in group.triggers:
        if trigger.affect.action.group != group:
            continue
        yield trigger.external_action.vertex
        yield f"{trigger.external_action.node_name} -> {trigger.affect.action.node_name}"
    for action in group.actions:
        yield action.vertex
        for affect in action.start_affects + action.complete_affects:
            if affect.action.group != group:
                continue
            yield f"{action.node_name} -> {affect.action.node_name}"
        for email in action.start_emails + action.complete_emails:
            yield email.vertex
            yield f"{action.node_name} -> {email.node_name}"

    for act in group.actions:
        for aff in act.affects:
            if aff.group != group:
                yield aff.group.vertex
                yield f"{act.node_name} -> {aff.group.node_name}"


@digraph
def generate_digraph_from_action_list(action_list: ActionList):
    for group in action_list.groups:
        for trigger in group.triggers:
            yield trigger.external_action.vertex
            yield f"{trigger.external_action.node_name} -> {trigger.affect.action.node_name}"

        for action in group.actions:
            yield action.vertex
            for affect in action.start_affects + action.complete_affects:
                yield f"{action.node_name} -> {affect.action.node_name}"
            for email in action.start_emails + action.complete_emails:
                yield email.vertex
                yield f"{action.node_name} -> {email.node_name}"


def find_roots(action_list, external_actions=None):
    """Finds actions affected by the given external actions"""
    if external_actions is None:
        external_actions = {
            121: "Document Added",
            14: "File Created",
            154: "Received Action Event",
        }
    roots = set()
    for group in action_list.groups:
        for trigger in group.triggers:
            if trigger.external_action.id in external_actions:
                roots.add(trigger.affect.action)
    return roots


def pprint_groups(alist):
    for group in alist.groups:
        print("Group:", group.name)
        for trigger in group.triggers:
            print(
                "  Trigger:", trigger.external_action.label, "->", trigger.affect.desc
            )
        for action in group.actions:
            print("  Action:", action.path)
            emails = action.start_emails + action.complete_emails
            if emails:
                print("    Emails:", ", ".join([email.name for email in emails]))
            affects = action.start_affects + action.complete_affects
            if affects:
                print("    Affects:")
                for affect in affects:
                    print("   ", affect.desc)


if __name__ == "__main__":
    models = build_models()
    ctx, alist = build_action_list(models, ACTION_LIST_DEF_ID)
    action = sys.argv[1] if len(sys.argv) > 1 else "digraph"
    if action == "digraph":
        print(generate_digraph_from_action_list(alist))
    elif action == "group":
        group_id = int(sys.argv[2])
        group = ctx.groups[group_id]
        print(generate_digraph_from_group(ctx.groups.values(), group))
    elif action == "partners":
        print(build_partners(models))
    elif action == "json":
        import json

        print(json.dumps(asdict(alist), indent="  "))
    elif action == "pprint":
        pprint_groups(alist)
    elif action == "build":
        pass
    else:
        print(
            f"Unknown action {action}. Valid options are digraph, build, partners, json, and pprint"
        )
        sys.exit(1)
