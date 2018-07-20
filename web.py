import subprocess

import flask
import time
from flask import request, abort

from graph import generate_digraph_from_action_list, build_action_list
from resware_model import build_models
from settings import ACTION_LIST_DEF_ID, WEB_TOKEN

app = flask.Flask(__name__)

last_updated_model = None
model = None


def get_model():
    """Cache the model for 5 seconds so this site can't be used to DDOS our ResWare DB"""
    now = time.time()
    global last_updated_model, model
    if not last_updated_model or now - last_updated_model > 5:
        print("Refreshing model")
        last_updated_model = now
        model = build_models()
    return model


@app.route('/')
def stream():
    if request.args.get('token', '') != WEB_TOKEN:
        abort(401)
    alist = build_action_list(get_model(), ACTION_LIST_DEF_ID)
    digraph = '\n'.join(generate_digraph_from_action_list(alist))
    run = subprocess.run(['dot', '-Tsvg'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/svg+xml')


if __name__ == "__main__":
    app.run(debug=True)
