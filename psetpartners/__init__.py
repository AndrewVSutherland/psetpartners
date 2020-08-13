# -*- coding: utf-8 -*-

__version__ = "0.0"

from psycodict.database import PostgresDatabase
from .config import Configuration
config = Configuration()
db = PostgresDatabase(config)
assert db

from .app import app
from .main import login_manager

login_manager.init_app(app)
