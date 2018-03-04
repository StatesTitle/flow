from collections import namedtuple

nodes = []
class Vertex:
    def __init__(self, label, system, actor, depends_on=None):
        self.name = label.replace(' ', '_')
        self.system = system
        self.actor = actor
        nodes.append(self)
        attrs = {}
        if self.name != label:
            attrs['label'] = label
        if self.system == 'ResWare':
            attrs['shape'] = 'box'
        if depends_on is None:
            depends_on = []
        self.depends_on = depends_on

        if attrs:
            self._attrs = '[' + ", ".join([f'{k}="{v}"' for k, v in attrs.items()]) + ']'
        else:
            self._attrs = ''



    def __str__(self):
        return f'{self.name}{self._attrs};'


goals = []
happy_path = True
sad_path = True
group_sections = True
fees = Vertex('Request Fees', 'ResWare', 'Lender')
place_order = Vertex('Place Order', 'ResWare', 'Lender', [fees])
underwrite = Vertex('Underwrite', 'States Title', 'Underwriter', [place_order])
commitment_review = Vertex('Review Commitment', 'ResWare', 'JV')
if happy_path:
    happy_path = Vertex('Happy Path', 'ResWare', 'Underwriter', [underwrite])
    commitment_review.depends_on.append(happy_path)
if sad_path:
    sad_path = Vertex('Sad Path', 'ResWare', 'Underwriter', [underwrite])
    if group_sections:
        commitment_review.depends_on.append(sad_path)
    else:
        title_search = Vertex('Title Search', 'ResWare', 'FAB', [sad_path])
        tax_lookup = Vertex('Lookup Taxes', 'ResWare', 'JV', [sad_path])
        cpl_creation = Vertex('Create CPL', 'ResWare', 'JV', [sad_path])
        typing = Vertex('Typing', 'ResWare', 'JV', [title_search, tax_lookup, cpl_creation])
        commitment_review.depends_on.append(typing)
payoff_info = Vertex('Gather Payoff Info', 'ResWare', 'JV', [place_order])

if group_sections:
    close = Vertex('Closing', 'ResWare', 'JV', [payoff_info, commitment_review])
    create_policy = Vertex('Create Policy', 'ResWare', 'JV', [close])
    goals = [create_policy]
else:
    cd_finalization = Vertex('Finalize CD', 'ResWare', 'JV', [payoff_info, commitment_review])
    schedule_borrower = Vertex('Schedule Closing w Borrower', 'ResWare', 'JV', [cd_finalization])
    schedule_notary = Vertex('Schedule Closing w Notary', 'ResWare', 'JV', [schedule_borrower])

    notify_lender_of_scheduling = Vertex('Notify Lender of Scheduling', 'ResWare', 'JV', [schedule_notary])
    receive_closing_documents = Vertex('Receive Closing Documents', 'ResWare', 'Lender', [notify_lender_of_scheduling])
    prepare_affidavits = Vertex('Prepare Affidavits for Borrower', 'ResWare', 'JV', [receive_closing_documents])
    prepare_fedex = Vertex('Prepare FedEx Label', 'ResWare', 'JV', [schedule_notary])
    prepare_notary_instructions = Vertex('Prepare Notary Instructions', 'ResWare', 'JV', [prepare_affidavits])
    prepare_settlement_statement = Vertex('Prepare ALTA Settlement Statement', 'ResWare', 'JV', [receive_closing_documents])
    send_closing_to_notary = Vertex('Email Closing Docs to Notary', 'ResWare', 'JV', [prepare_fedex, prepare_notary_instructions, prepare_settlement_statement])
    notary_sends_scanned_package = Vertex('Notary Emails Signed Package', 'ResWare', 'Notary', [send_closing_to_notary])
    notary_sends_physical_pacakge = Vertex('Notary FedExes Signed Package', 'ResWare', 'Notary', [send_closing_to_notary])
    send_lender_closing = Vertex('Send Lender Signed Package', 'ResWare', 'JV', [notary_sends_physical_pacakge])
    lender_funds_loan = Vertex('Lender Funds Loan', 'ResWare', 'Lender', [send_lender_closing])
    disbursement_arrives = Vertex('Receive Disbursement sent via Wire', 'ResWare', 'Bank', [lender_funds_loan])
    documents_sent_to_recording = Vertex('Send Documents to Recording', 'ResWare', 'JV', [disbursement_arrives])
    create_title_policy = Vertex('Complete Title Policy', 'ResWare', 'JV', [disbursement_arrives])
    mail_title_policy_with_deed_to_lender = Vertex('Mail Policy with Deed to Lender', 'ResWare', 'JV', [create_title_policy, documents_sent_to_recording])
    mail_title_policy_with_remittance_to_underwriter = Vertex('Mail Policy with Remittance to Underwriter', 'ResWare', 'JV', [create_title_policy])
    goals = [mail_title_policy_with_deed_to_lender, mail_title_policy_with_remittance_to_underwriter, notary_sends_scanned_package]


def print_nodes_and_deps(to_visit, visited):
    visited.add(to_visit)
    print('   ', to_visit)
    for node in to_visit.depends_on:
        if node not in visited:
            print_nodes_and_deps(node, visited)
        print(f'    {node.name} -> {to_visit.name}')

def print_digraph(goals):
    print('digraph G {')
    visited = set()
    for goal in goals:
        print_nodes_and_deps(goal, visited)
    print('}')


print_digraph(goals)
