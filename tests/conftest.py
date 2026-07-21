"""Make the plugin's shared scripts importable from tests."""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "plugins", "youtube-toolkit", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
