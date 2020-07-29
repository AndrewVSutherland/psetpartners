# -*- coding: utf-8 -*-
from __future__ import absolute_import

from psetpartners.app import app

from . import main
from .main import login_manager

login_manager.init_app(app)

assert main
