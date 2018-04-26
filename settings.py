import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ResWare Database Connection Settings
RESWARE_DATABASE_SERVER = os.getenv('RESWARE_DATABASE_SERVER')
RESWARE_DATABASE_PORT = os.getenv('RESWARE_DATABASE_PORT')
RESWARE_DATABASE_USER = os.getenv('RESWARE_DATABASE_USER')
RESWARE_DATABASE_PASSWORD = os.getenv('RESWARE_DATABASE_PASSWORD')
RESWARE_DATABASE_NAME = os.getenv('RESWARE_DATABASE_NAME')

# Action List To Graph
ACTION_LIST_DEF_ID = int(os.getenv('ACTION_LIST_DEF_ID', 0))

# Display Triggers in Graph
INCLUDE_TRIGGERS = bool(int(os.getenv('INCLUDE_TRIGGERS', 0)))
