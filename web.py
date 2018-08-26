import subprocess

import flask
from flask import request, abort
from flask import jsonify

from graph import generate_digraph_from_action_list, build_action_list, AffectTaskAffect
from resware_model import build_models, Task
from settings import ACTION_LIST_DEF_ID, WEB_TOKEN

app = flask.Flask(__name__)


@app.route('/')
def stream():
    if request.args.get('token', '') != WEB_TOKEN:
        abort(401)
    alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    digraph = '\n'.join(generate_digraph_from_action_list(alist))
    run = subprocess.run(['dot', '-Tsvg'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/svg+xml')


@app.route('/api/action_list')
def api_action_list():
    if request.args.get('token', '') != WEB_TOKEN:
        abort(401)

    groups = build_action_list(build_models(), ACTION_LIST_DEF_ID).groups
    actions = [action for action_group in groups for action in action_group.actions]

    response = jsonify(get_json(actions))
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def get_json(action_list):
    return [{
        'id': action.action_id,
        'groupId': action.group_id,
        'name': action.name,
        'description': action.description,
        'hidden': action.hidden,
        'dynamic': action.dynamic,
        'emails': [{
            'name': email.name
        } for email in action.emails],
        'start_affects': [get_affect(affect) for affect in action.start_affects],
        'complete_affects': [get_affect(affect) for affect in action.complete_affects],
    } for action in action_list]


def get_affect(affect):
    if isinstance(affect, AffectTaskAffect):
        return {
            'type': 'complete' if affect.task == Task.COMPLETE else 'start',
            'action': f'{affect.action_id}-{affect.group_id}',
        }
    else:
        return {}


if __name__ == "__main__":
    app.run(debug=True)
