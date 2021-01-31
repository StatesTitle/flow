import os

from dotenv import load_dotenv, find_dotenv


def load_dotenv_if_exists(filename):
    dotenv = find_dotenv(filename)
    if dotenv != "":
        load_dotenv(dotenv)


# If .env.local exists, update os.environ with keys and values from it if they aren't already set
load_dotenv_if_exists(".env.local")

# Update os.environ with keys and values from .env if they aren't already set and .env exists. We
# exclude .env with .slugignore from Heroku, so this should only be present locally and in CI
load_dotenv_if_exists(".env")

#
# ResWare database settings
RESWARE_DATABASE_SERVER = os.getenv("RESWARE_DATABASE_SERVER")
RESWARE_DATABASE_PORT = os.getenv("RESWARE_DATABASE_PORT")
RESWARE_DATABASE_USER = os.getenv("RESWARE_DATABASE_USER")
RESWARE_DATABASE_PASSWORD = os.getenv("RESWARE_DATABASE_PASSWORD")
RESWARE_DATABASE_NAME = os.getenv("RESWARE_DATABASE_NAME")

# Action List To Graph
ACTION_LIST_DEF_ID = int(os.getenv("ACTION_LIST_DEF_ID", 0))

WEB_TOKEN = os.getenv("WEB_TOKEN")
