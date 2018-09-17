# flow
Converts a title insurance workflow from ResWare's db into Graphviz's dot language and renders it with [Graphviz](https://graphviz.gitlab.io/).

* [database.py](database.py) connects to a SQL Server database, either directly or through an SSH
  tunnel
* [resware_model.py](resware_model.py) loads ResWare's ActionList information from its db
* [graph.py](graph.py) turns the ResWare information loaded in resware_model into a connected graph
  and converts that to dot
* [web.py](web.py) Loads the graph from the db, converts it to SVG with dot, and serves that as a web page

## Develop

All instructions below assume Mac. For other platforms, installing equivalent packages should work

1. `brew install graphviz`
1.  Install `freetds`

	Workaround for issues with [pymssql](https://github.com/pymssql/pymssql/issues/432#issuecomment-376534685) install

    ```
        brew install freetds@0.91
        brew link --force freetds@0.91
    ```
1. Setup a Python 3 virtualenv: `virtualenv -ppython3 venv`
1. Activate the virtualenv: `. venv/bin/activate`
1. Install Cython `pip install cython` (this is required as a workaround for a bug in pip's dependency resolution, see https://www.pivotaltracker.com/story/show/160182896)
1. Install the Python requirements in the virtualenv: `pip install -r requirements.txt`
1. Update the RESWARE_DATABASE keys in .env to point to your ResWare database and set
   ACTION_LIST_DEF_ID to the id of the action list you want to graph
1. Run `gunicorn --reload web:app` and go to localhost:8000 to see the output

You can also run `python graph.py` to produce the dot output from the database.  You can pipe the output to graphviz to produce an image e.g. `python graph.py | dot -Tpng -oflow.png` and then open flow.png.

## Deploy

This app will run directly on Heroku. To set it up:

1. Add `https://github.com/heroku/heroku-buildpack-apt.git`, `https://github.com/weibeld/heroku-buildpack-graphviz.git`, and `heroku/python` as buildpacks to your app in that order.
1. Setup the keys in .env in the Heroku config for the app i.e. add your database and ssh tunnel
   configuration along with the action list you want to view and the token to prevent random viewers.
1. `heroku git:remote -a st-flow` in a clone of this repo substituting your app name.

After that you can

1. `git push heroku master` from this repo to deploy the latest

## Formatting
```
./venv/bin/yapf --parallel --in-place [filename]
```

## Enhancements

* Distinguish Affect Start/Complete Types (Color, Shape?)
* Support Affect Group Dependencies
