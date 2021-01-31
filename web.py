import subprocess
from functools import wraps
from flask import request, abort, render_template, Flask, Response
from graph import (
    generate_digraph_from_action_list,
    generate_digraph_from_group,
    build_action_list,
)
from resware_model import build_models
from settings import ACTION_LIST_DEF_ID, WEB_TOKEN

app = Flask(__name__)


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get("Authorization", "") != WEB_TOKEN:
            abort(401)
        return f(*args, **kwargs)

    return decorated_function


def svg(digraph):
    run = subprocess.run(
        ["dot", "-Tsvg"], stdout=subprocess.PIPE, input=bytes(digraph, "utf-8")
    )
    return run.stdout


def hack_graphviz_svg_for_embed(svg_bytes):
    svg_str = svg_bytes.decode("utf-8")
    svg_str = svg_str[svg_str.index("<title>") :]
    return '<svg width="100%" id="graph"><g>' + svg_str


def svg_response(digraph):
    return Response(svg(digraph), mimetype="image/svg+xml")


@app.route("/")
@auth_required
def index():
    _, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    return render_template("index.html", groups=alist.groups)


@app.route("/everything.svg")
@auth_required
def everything_svg():
    _, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    digraph = generate_digraph_from_action_list(alist)
    return svg_response(digraph)


@app.route("/everything")
@auth_required
def everything():
    _, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    digraph = generate_digraph_from_action_list(alist)
    svg_str = hack_graphviz_svg_for_embed(svg(digraph))
    return render_template("graph.html", title="Everything!", svg=svg_str)


@app.route("/groups/<int:group_id>.svg")
@auth_required
def group_svg(group_id):
    ctx, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    group = ctx.groups[group_id]
    digraph = generate_digraph_from_group(alist, group)
    return svg_response(digraph)


@app.route("/groups/<int:group_id>")
@auth_required
def group(group_id):
    ctx, alist = build_action_list(build_models(), ACTION_LIST_DEF_ID)
    group = ctx.groups[group_id]
    digraph = generate_digraph_from_group(alist, group)
    svg_str = hack_graphviz_svg_for_embed(svg(digraph))
    return render_template("graph.html", title=group.name, svg=svg_str)


if __name__ == "__main__":
    app.run(debug=True)
