import flask
import subprocess
from graph import generate_digraph_from_action_list, build_action_list
from resware_model import build_models
from settings import ACTION_LIST_DEF_ID

app = flask.Flask(__name__)


@app.route('/')
def stream():
    alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    digraph = '\n'.join(generate_digraph_from_action_list(alist))
    run = subprocess.run(['dot', '-Tsvg'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/svg+xml')


if __name__ == "__main__":
    app.run(debug=True)
