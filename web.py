import subprocess
from functools import wraps
from flask import request, abort, render_template, Flask, Response
from graph import generate_digraph_from_action_list, generate_digraph_from_group, build_action_list
from resware_model import build_models
from settings import ACTION_LIST_DEF_ID, WEB_TOKEN

app = Flask(__name__)


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('Authorization', '') != WEB_TOKEN:
            abort(401)
        return f(*args, **kwargs)

    return decorated_function


def graph(digraph):
    run = subprocess.run(['dot', '-Tsvg'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return Response(run.stdout, mimetype='image/svg+xml')


@app.route('/')
@auth_required
def index():
    _, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    return render_template('index.html', groups=alist.groups)


@app.route('/everything.svg')
@auth_required
def everything():
    _, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    digraph = generate_digraph_from_action_list(alist)
    return graph(digraph)


@app.route('/groups/<int:group_id>.svg')
@auth_required
def group(group_id):
    ctx, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    group = ctx.groups[group_id]
    digraph = generate_digraph_from_group(alist, group)
    return graph(digraph)


if __name__ == "__main__":
    app.run(debug=True)