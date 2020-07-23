# -*- coding: utf-8 -*-

from __future__ import absolute_import
from .main import login_page, login_manager

from psetpartners.app import app
#from lmfdb.logger import make_logger

login_manager.init_app(app)

app.register_blueprint(login_page, url_prefix="/user")

#users_logger = make_logger("user", hl=True)
