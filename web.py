import flask
import subprocess

from sheets import fetch_digraph

app = flask.Flask(__name__)

@app.route( '/' )
def stream():
    digraph = '\n'.join(fetch_digraph())
    run = subprocess.run(['dot', '-Tpng'], stdout=subprocess.PIPE, input=bytes(digraph, 'utf-8'))
    return flask.Response(run.stdout, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
