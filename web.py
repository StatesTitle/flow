import flask
import json
import os
import subprocess
from google.oauth2 import service_account
from sheets import fetch_digraph, SCOPES

parsed = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
creds = service_account.Credentials.from_service_account_info(parsed, scopes=[SCOPES])

app = flask.Flask(__name__)

@app.route( '/' )
def stream():
    digraph = '\n'.join(fetch_digraph(creds))
    run = subprocess.run(['dot', '-Tpng'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
