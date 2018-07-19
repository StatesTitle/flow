import os

from dotenv import load_dotenv, find_dotenv


def load_dotenv_if_exists(filename):
    dotenv = find_dotenv(filename)
    if dotenv != '':
        load_dotenv(dotenv)


# If .env.local exists, update os.environ with keys and values from it if they aren't already set
load_dotenv_if_exists('.env.local')

# Update os.environ with keys and values from .env if they aren't already set and .env exists. We
# exclude .env with .slugignore from Heroku, so this should only be present locally and in CI
load_dotenv_if_exists('.env')

# ResWare Direct Database Connection Settings
RESWARE_DATABASE_SERVER = os.getenv('RESWARE_DATABASE_SERVER')
RESWARE_DATABASE_PORT = os.getenv('RESWARE_DATABASE_PORT')

#
# ResWare database settings
RESWARE_DATABASE_USER = os.getenv('RESWARE_DATABASE_USER')
RESWARE_DATABASE_PASSWORD = os.getenv('RESWARE_DATABASE_PASSWORD')
RESWARE_DATABASE_NAME = os.getenv('RESWARE_DATABASE_NAME')

SSH_TUNNEL_ENABLED = os.getenv('SSH_TUNNEL_ENABLED', "0") == '1'
SSH_SERVER_HOST = os.getenv('SSH_SERVER_HOST')
SSH_SERVER_PORT = int(os.getenv('SSH_SERVER_PORT', '22'))
SSH_USERNAME = os.getenv('SSH_USERNAME')
SSH_PRIVATE_KEY = os.getenv('SSH_PRIVATE_KEY')
SSH_REMOTE_BIND_ADDRESS = os.getenv('SSH_REMOTE_BIND_ADDRESS')
SSH_REMOTE_BIND_PORT = int(os.getenv('SSH_REMOTE_BIND_PORT', '1433'))

# Action List To Graph
ACTION_LIST_DEF_ID = int(os.getenv('ACTION_LIST_DEF_ID', 0))
