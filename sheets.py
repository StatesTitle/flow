from apiclient import discovery
from google.oauth2 import service_account
from deps import Vertex, digraph
import os
import json

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
parsed = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
creds = service_account.Credentials.from_service_account_info(parsed, scopes=[SCOPES])


def fetch_digraph():
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', credentials=creds, discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1q0l55EY8FqM5ghJjwm1-Pbp3Nlnj0iFzWwwyXJxA53I'

    ranges = ['Actions!A2:C', 'Dependencies!A2:B']
    result = service.spreadsheets().values().batchGet(spreadsheetId=spreadsheetId, ranges=ranges).execute()
    actions, deps = [r['values'] for r in result['valueRanges']]
    vertices = {}
    for row in actions:
        vertices[row[0]] = Vertex(*row)
    for row in deps:
        vertices[row[0]].depends_on.add(vertices[row[1]])
    return digraph(vertices.values())

if __name__ == '__main__':
    for line in fetch_digraph():
        print(line)

