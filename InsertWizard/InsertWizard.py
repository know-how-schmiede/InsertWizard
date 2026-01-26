import os
import sys

# Ensure the add-in root is on sys.path so absolute imports work in Fusion's loader.
ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if ADDIN_DIR in sys.path:
    sys.path.remove(ADDIN_DIR)
sys.path.insert(0, ADDIN_DIR)

import commands
from lib import fusionAddInUtils as futil


def run(context):
    try:
        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.start()

    except:
        futil.handle_error('run')


def stop(context):
    try:
        # Remove all of the event handlers your app has created
        futil.clear_handlers()

        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.stop()

    except:
        futil.handle_error('stop')
