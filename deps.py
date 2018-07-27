from collections import namedtuple


def escape_name(name):
    name = name.replace('&', 'and')
    for c in ' ./#?,!@$%^*()+=[]{}:;"-\\\'':
        name = name.replace(c, '_')
    return name


class Vertex:
    def __init__(self, label, depends_on=None, fill_color=None, shape=None, name=None, **dot_attrs):
        label = label.replace('"', '\\"')
        if name is None:
            name = label
        self.name = escape_name(name)
        attrs = {**dot_attrs}
        if self.name != label:
            attrs['label'] = label
        if shape:
            attrs['shape'] = shape
        if fill_color:
            attrs['style'] = 'filled'
            attrs['fillcolor'] = fill_color
        if depends_on is None:
            depends_on = []
        self.depends_on = set(depends_on)

        if attrs:
            self._attrs = '[' + ", ".join([f'{k}="{v}"' for k, v in attrs.items()]) + ']'
        else:
            self._attrs = ''

    def __str__(self):
        return f'{self.name}{self._attrs};'


def print_nodes_and_deps(to_visit, visited):
    if to_visit in visited:
        return
    visited.add(to_visit)
    yield f'    {to_visit}'
    for node in to_visit.depends_on:
        yield from print_nodes_and_deps(node, visited)
        yield f'    {node.name} -> {to_visit.name}'


def digraph(goals):
    yield 'digraph G {'
    visited = set()
    for goal in goals:
        yield from print_nodes_and_deps(goal, visited)
    yield '}'


if __name__ == '__main__':
    happy_path = True
    sad_path = True
    fees = Vertex('Request Fees')
    place_order = Vertex('Place Order', [fees])
    underwrite = Vertex('Underwrite', [place_order])
    commitment_review = Vertex('Review Commitment')
    if happy_path:
        happy_path = Vertex('Happy Path', [underwrite])
        commitment_review.depends_on.add(happy_path)
    if sad_path:
        sad_path = Vertex('Sad Path', [underwrite])
        title_search = Vertex('Title Search', [sad_path])
        tax_lookup = Vertex('Lookup Taxes', [sad_path])
        cpl_creation = Vertex('Create CPL', [sad_path])
        typing = Vertex('Typing', [title_search, tax_lookup, cpl_creation])
        commitment_review.depends_on.add(typing)
    payoff_info = Vertex('Gather Payoff Info', [place_order])
    cd_finalization = Vertex('Finalize CD', [payoff_info, commitment_review])
    schedule_borrower = Vertex('Schedule Closing w Borrower', [cd_finalization])
    schedule_notary = Vertex('Schedule Closing w Notary', [schedule_borrower])

    notify_lender_of_scheduling = Vertex('Notify Lender of Scheduling', [schedule_notary])
    receive_closing_documents = Vertex('Receive Closing Documents', [notify_lender_of_scheduling])
    prepare_affidavits = Vertex('Prepare Affidavits for Borrower', [receive_closing_documents])
    prepare_fedex = Vertex('Prepare FedEx Label', [schedule_notary])
    prepare_notary_instructions = Vertex('Prepare Notary Instructions', [prepare_affidavits])
    prepare_settlement_statement = Vertex(
        'Prepare ALTA Settlement Statement', [receive_closing_documents]
    )
    send_closing_to_notary = Vertex(
        'Email Closing Docs to Notary',
        [prepare_fedex, prepare_notary_instructions, prepare_settlement_statement]
    )
    notary_sends_scanned_package = Vertex('Notary Emails Signed Package', [send_closing_to_notary])
    notary_sends_physical_pacakge = Vertex(
        'Notary FedExes Signed Package', [send_closing_to_notary]
    )
    send_lender_closing = Vertex('Send Lender Signed Package', [notary_sends_physical_pacakge])
    lender_funds_loan = Vertex('Lender Funds Loan', [send_lender_closing])
    disbursement_arrives = Vertex('Receive Disbursement sent via Wire', [lender_funds_loan])
    documents_sent_to_recording = Vertex('Send Documents to Recording', [disbursement_arrives])
    create_title_policy = Vertex('Complete Title Policy', [disbursement_arrives])
    mail_title_policy_with_deed_to_lender = Vertex(
        'Mail Policy with Deed to Lender', [create_title_policy, documents_sent_to_recording]
    )
    mail_title_policy_with_remittance_to_underwriter = Vertex(
        'Mail Policy with Remittance to Underwriter', [create_title_policy]
    )

    for line in digraph([
        mail_title_policy_with_deed_to_lender, mail_title_policy_with_remittance_to_underwriter,
        notary_sends_scanned_package
    ]):
        print(line)
