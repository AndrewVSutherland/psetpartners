# -*- coding: utf-8 -*-

__version__ = "0.0"
# append psycodict path to the import path, to use the submodule
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../psycodict"))
from psycodict.database import PostgresDatabase
from .config import Configuration
config = Configuration()
db = PostgresDatabase(config)
assert db

from .app import app
from .main import login_manager

login_manager.init_app(app)
