from apiclient import discovery
from google.oauth2 import service_account
from deps import Vertex, digraph

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
SERVICE_ACCOUNT_FILE = 'sheets.googleapis.service.json'

def fetch_digraph():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[SCOPES])
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', credentials=credentials, discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1q0l55EY8FqM5ghJjwm1-Pbp3Nlnj0iFzWwwyXJxA53I'

    ranges = ['Actions!A2:C', 'Dependencies!A2:B']
    result = service.spreadsheets().values().batchGet(spreadsheetId=spreadsheetId, ranges=ranges).execute()
    actions, deps = [r['values'] for r in result['valueRanges']]
    vertices = {}
    for row in actions:
        vertices[row[0]] = Vertex(*row)
    for row in deps:
        vertices[row[0]].depends_on.append(vertices[row[1]])
    return digraph([vertices[k] for k in ['Mail Policy with Remittance to Underwriter', 'Mail Policy with Deed to Lender', 'Notary Emails Signed Package']])

if __name__ == '__main__':
    for line in fetch_digraph():
        print(line)

