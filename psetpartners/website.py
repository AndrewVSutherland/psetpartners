# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import logging
from .app import app
from .config import Configuration
from . import main
assert main
from . import db
assert db

def main():
    logger = logging.getLogger("psetpartners")
    logger.setLevel(logging.INFO)
    logfile = Configuration().get_logging()["logfile"]
    ch = logging.FileHandler(logfile)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("""%(asctime)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n  %(message)s"""))
    logger.addHandler(ch)
    app.logger.info("Website starting.")

    flask_options = Configuration().get_flask()

    if "profiler" in flask_options and flask_options["profiler"]:
        from werkzeug.contrib.profiler import ProfilerMiddleware

        app.wsgi_app = ProfilerMiddleware(
            app.wsgi_app, restrictions=[30], sort_by=("cumulative", "time", "calls")
        )
        del flask_options["profiler"]

    app.run(**flask_options)
    app.logger.info("Website shutdown.")
