# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

from . import main
assert main
from . import db
assert db

def main():
    from .app import app
    from .config import Configuration

    flask_options = Configuration().get_flask()

    if "profiler" in flask_options and flask_options["profiler"]:
        from werkzeug.contrib.profiler import ProfilerMiddleware

        app.wsgi_app = ProfilerMiddleware(
            app.wsgi_app, restrictions=[30], sort_by=("cumulative", "time", "calls")
        )
        del flask_options["profiler"]

    app.run(**flask_options)
