import flask
import subprocess
from database import generate_digraph_from_action_list

app = flask.Flask(__name__)


@app.route('/')
def stream():
    digraph = '\n'.join(generate_digraph_from_action_list())
    run = subprocess.run(['dot', '-Tsvg'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/svg+xml')


if __name__ == "__main__":
    app.run(debug=True)
