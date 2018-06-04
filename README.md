# flow
Converts a title insurance workflow from ResWare's db into Graphviz's dot language and renders it with [Graphviz](https://graphviz.gitlab.io/).

* [deps.py](deps.py) builds a dependency tree and creates Graphviz digraphs from it
* [web.py](web.py) uses database.py to get a dependency graph, renders it with Graphviz, and returns it over the web using flask
* [database.py](database.py) queries a local ResWare database to generate dependency graph

## Develop

1. `brew install graphviz`
1.  Install `freetds`

	Workaround for issues with [pymssql](https://github.com/pymssql/pymssql/issues/432#issuecomment-376534685) install

    ```
        brew install freetds@0.91
        brew link --force freetds@0.91
    ```
1. Create a virtualenv and `pip install -f requirements.txt`
1. Run `gunicorn --reload web:app` and go to localhost:8000 to see the output

You can also run `python deps.py` to produce a digraph of the hand-built state in there python, or to generate a digraph from a local [ResWare database](https://github.com/StatesTitle/docs/blob/master/resware-mssql/README.md), run `python database.py` (note `.env` configs should be set).

In using deps.py or database.py, you can pipe the output to graphviz to produce an image e.g. `python deps.py | dot -Tpng -oflow.png` to create flow.png.

## Deploy

1. `heroku git:remote -a st-flow` in a clone of this repo
1. `git push heroku master`

That will deploy the code on your master to the st-flow app in Heroku ([site](https://st-flow.herokuapp.com/)). Note: Heroku doesn't have access to ResWare's db, so this doesn't work yet


## Formatting
```
./venv/bin/yapf --parallel --in-place [filename]
```

## Enhancements

* Investigate self-referential nodes
* Distinguish Affect Start/Complete Types (Color, Shape?)
* Support Affect Group Dependencies
