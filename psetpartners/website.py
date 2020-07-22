# -*- coding: utf-8 -*-


# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

from .app import app, set_running  # So that we can set it running below

from psetpartners import db
assert db
from . import users

def main():
    from .config import Configuration

    flask_options = Configuration().get_flask()

    if "profiler" in flask_options and flask_options["profiler"]:
        from werkzeug.contrib.profiler import ProfilerMiddleware

        app.wsgi_app = ProfilerMiddleware(
            app.wsgi_app, restrictions=[30], sort_by=("cumulative", "time", "calls")
        )
        del flask_options["profiler"]

    set_running()
    app.run(**flask_options)
