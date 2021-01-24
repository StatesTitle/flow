"""Raw in-memory representations of the data in ResWare's db relating to action list definitions and friends

We make it easy to load all of that at once to make it easier to create an object graph without having to do
complicated queries to only fetch the bits we once. Since the action lists will never be 1000s and 1000s of steps,
loading all of this shouldn't be prohibitive."""
import enum

from dataclasses import dataclass

from database import col, tableclass, ResWareDatabaseConnection, load


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
# 1. If AffectActionListGroupDefID and AffectActionDefID are set, another GroupAction is being changed.
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
    created_action_group_id: int = col('CreateActionActionListGroupDefID', nullable=True)
    created_action_action_id: int = col('CreateActionActionDefID', nullable=True)
    created_group_id: int = col('CreateGroupActionListGroupDefID', nullable=True)


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
    subject: str = col('EmailSubject', nullable=True)
    body: str = col('EmailBody', nullable=True)
    # 0 - neither attach by template or document type
    # 1 - attach by template only
    # 2 - attach by document type
    # 3 - attach by both template and document type
    email_attachment_type: int = col('EmailAttachmentType')
    generate_hud: bool = col('GenerateHUD')
    generate_buyer_statement: bool = col('GenerateBuyerStatement')
    combine_as_pdf: bool = col('CombineAsPDF')
    pdf_name: str = col("PDFName", nullable=True)
    pdf_document_type_id: int = col("PDFDocumentTypeID", nullable=True)
    # 1 = user, 2 = internet orders, 3 = team, 4 = team group, 5 = user's reply to, 6 = issue tracker, 7 = assigned team
    reply_to_type: int = col("ReplyToType")
    transmit_via_xml: bool = col('TransmitViaXML')
    combine_generated_documents_attach_to_email: bool = col(
        'CombineGeneratedDocumentsAttachToEmail'
    )
    # There are also a huge number of columns controlling what's generated. Add em as needed


@tableclass('ActionEmailTemplateDocumentTypeRef', lookup='email_id', one_to_many=True)
class EmailDocument:
    email_id: int = col('ActionEmailTemplateID')
    document_type_id: int = col('DocumentTypeID')


@tableclass('ActionEmailTemplatePartnerTypeRef', lookup='email_id', one_to_many=True)
class EmailPartnerTypeRecipient:
    """The partner type that should receive the email"""
    email_id: int = col('ActionEmailTemplateID')
    partner_type_id: int = col('PartnerTypeID')


@tableclass('PartnerCompanyActionEmailTemplateRel', one_to_many=True, lookup='email_id')
class EmailPartnerRestriction:
    partner_id: int = col('PartnerCompanyID', nullable=True)
    email_id: int = col('ActionEmailTemplateID')
    include: bool = col('IncludeExclude')


@tableclass('ActionEmailTemplateTemplateRef', lookup='email_id', one_to_many=True)
class EmailTemplate:
    email_id: int = col('ActionEmailTemplateID')
    template_id: int = col('TemplateID')


@tableclass('Template')
class Template:
    id: int = col('TemplateID')
    name: str = col('Name')
    filename: str = col('Filename')
    document_type_id: int = col('DocumentTypeID')
    # lots more columns about how the document is generated


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
    hidden: bool = col('Hidden')


def _group_partner_include(type_id):
    assert type_id == 1 or type_id == 2, f'Expected type_id to be either 1 for include or 2 for exclude, not {type_id}'
    return type_id == 1


@tableclass(
    'ActionListGroupActionDefPartnerRel', one_to_many=True, lookup=('group_id', 'action_id')
)
class GroupActionPartnerRestriction:
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')
    partner_id: int = col('PartnerCompanyID')
    include: bool = col('ActionPartnerAddTypeID', parser=_group_partner_include)


@tableclass('ActionListGroupActionDef', lookup='group_id', one_to_many=True)
class GroupAction:
    group_id: int = col('ActionListGroupDefID')
    action_id: int = col('ActionDefID')
    dynamic: bool = col('Dynamic')


@tableclass('ActionListGroupDefPartnerRel', one_to_many=True, lookup='group_id')
class GroupPartnerRestriction:
    group_id: int = col('ActionListGroupDefID')
    partner_id: int = col('PartnerCompanyID')
    include: bool = col('ActionPartnerAddTypeID', parser=_group_partner_include)


@tableclass('ActionListGroupDef')
class Group:
    id: int = col('ActionListGroupDefID')
    name: str = col('ActionListGroupName')


@tableclass('ActionGroupAffectDef', lookup=('group_id', 'action_id'), one_to_many=True)
class GroupActionAffect(Affect):
    task: Task = col('ActionTypeID', nullable=True)
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


@tableclass('PartnerCompany')
class Partner:
    id: int = col('PartnerCompanyID')
    name: str = col('Name')


@tableclass('PartnerCompanyPartnerTypeRel', one_to_many=True)
class PartnerTypes:
    id: int = col('PartnerCompanyID')
    type_id: int = col('PartnerTypeID')


@tableclass('PartnerAutoAddPartnerRel', one_to_many=True)
class PartnerAutoAdds:
    id: int = col('PartnerCompanyID')
    type_id: int = col('PartnerTypeId')
    auto_add_id: int = col('AutoAddPartnerCompanyID')
    auto_add_type_id: int = col('AutoAddPartnerTypeID')


@tableclass('PartnerType', frozen=True)
class PartnerType:
    id: int = col('PartnerTypeID')
    name: str = col('Name')


class Models:
    def __init__(self, conn):
        self.partners = load(conn, Partner)
        self.partners_types = load(conn, PartnerTypes)
        self.partners_auto_adds = load(conn, PartnerAutoAdds)
        self.partner_types = load(conn, PartnerType)
        self.triggers = load(conn, Trigger)
        self.external_actions = load(conn, ExternalAction)
        self.emails = load(conn, Email)
        self.email_documents = load(conn, EmailDocument)
        self.email_partner_type_recipients = load(conn, EmailPartnerTypeRecipient)

        # There's at least one restriction column for every email template The partner is NULL if
        # it's a placeholder and there aren't any real ones
        self.email_partner_restrictions = load(conn, EmailPartnerRestriction)
        for email_id, partners in list(self.email_partner_restrictions.items()):
            for partner in partners[:]:
                if partner.partner_id is None:
                    partners.remove(partner)
            # If the list is now empty, delete it from the dict
            if len(partners) == 0:
                del self.email_partner_restrictions[email_id]

        self.email_templates = load(conn, EmailTemplate)
        self.templates = load(conn, Template)
        self.action_emails = load(conn, ActionEmail)
        self.action_events = load(conn, ActionEvent)
        self.document_types = load(conn, DocumentType)
        self.actions = load(conn, Action)
        self.group_actions = load(conn, GroupAction)
        self.group_action_partner_restrictions = load(conn, GroupActionPartnerRestriction)
        self.groups = load(conn, Group)
        self.group_partner_restrictions = load(conn, GroupPartnerRestriction)
        self.group_action_affects = load(conn, GroupActionAffect)
        self.action_lists = load(conn, ActionList)
        self.action_list_groups = load(conn, ActionListGroups)


def build_models():
    with ResWareDatabaseConnection() as conn:
        return Models(conn)


if __name__ == '__main__':
    build_models()
