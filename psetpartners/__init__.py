# -*- coding: utf-8 -*-

__version__ = "0.1"

from psycodict.database import PostgresDatabase
from .config import Configuration
config = Configuration()
print(config.options["postgresql"])
db = PostgresDatabase(config)
assert db

from .app import app, start_logging
from .main import login_manager

start_logging()
login_manager.init_app(app)
