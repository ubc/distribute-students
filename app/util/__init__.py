print(" ██╗   ██╗██████╗  ██████╗")
print(" ██║   ██║██╔══██╗██╔════╝")
print(" ██║   ██║██████╔╝██║     ")
print(" ██║   ██║██╔══██╗██║     ")
print(" ╚██████╔╝██████╔╝╚██████╗")
print("  ╚═════╝ ╚═════╝  ╚═════╝")

import os

# load the logging configuration
import logging
from logging.config import fileConfig
fileConfig('config/logging.ini')

# make default logfile
from datetime import datetime
root = logging.getLogger()
fh = logging.FileHandler(datetime.now().strftime('logs/%Y-%m-%d.log'))
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
root.addHandler(fh)

# load the config file
_ENV = os.environ.get("ENV")

# create Canvas instance
from util.api.canvas import CanvasInstance
_canvas = None
def get_canvas_instance():
    global _canvas
    if not _canvas:
        _canvas = CanvasInstance()
    return _canvas
