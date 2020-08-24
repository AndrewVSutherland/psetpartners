# -*- coding: utf-8 -*-
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import os
import sys
import argparse
import secrets
from psycodict.config import Configuration as _Configuration

root_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

def abs_path(filename):
    return os.path.relpath(os.path.join(root_path, filename), os.getcwd())

def get_secret_key():
    secret_key_file = abs_path("secret_key")
    if not os.path.exists(secret_key_file):
        with open(secret_key_file, "w") as F:
            # generate a random ASCII string
            F.write(secrets.token_urlsafe(32))
    with open(secret_key_file) as F:
        return F.read()

class Configuration(_Configuration):
    def __init__(self, writeargstofile=False):
        default_config_file = abs_path("config.ini")
        default_secrets_file = abs_path("secrets.ini")

        parser = argparse.ArgumentParser(description="psetpartners")
        parser.add_argument(
            "-c",
            "--config-file",
            dest="config_file",
            metavar="FILE",
            help="configuration file [default: %(default)s]",
            default=default_config_file,
        )
        parser.add_argument(
            "-s",
            "--secrets-file",
            dest="secrets_file",
            metavar="SECRETS",
            help="secrets file [default: %(default)s]",
            default=default_secrets_file,
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            dest="web_debug",
            help="enable debug mode",
            default=False,
        )

        parser.add_argument(
            "-p",
            "--port",
            dest="web_port",
            metavar="PORT",
            help="the psetpartners server will be running on PORT [default: %(default)d]",
            type=int,
            default=37779,
        )
        parser.add_argument(
            "-b",
            "--bind_ip",
            dest="web_host",
            metavar="HOST",
            help="the psetpartners server will be listening to HOST [default: %(default)s]",
            default="127.0.0.1",
        )

        logginggroup = parser.add_argument_group("Logging options:")
        logginggroup.add_argument(
            "--logfile",
            help="logfile for flask [default: %(default)s]",
            dest="logging_logfile",
            metavar="FILE",
            default="flasklog",
        )

        logginggroup.add_argument(
            "--logfocus", help="name of a logger to focus on", default=argparse.SUPPRESS
        )

        logginggroup.add_argument(
            "--slowcutoff",
            dest="logging_slowcutoff",
            metavar="SLOWCUTOFF",
            help="threshold to log slow queries [default: %(default)s]",
            default=0.1,
            type=float,
        )

        logginggroup.add_argument(
            "--slowlogfile",
            help="logfile for slow queries [default: %(default)s]",
            dest="logging_slowlogfile",
            metavar="FILE",
            default="slow_queries.log",
        )

        # PostgresSQL options
        postgresqlgroup = parser.add_argument_group("PostgreSQL options")
        postgresqlgroup.add_argument(
            "--postgresql-host",
            dest="postgresql_host",
            metavar="HOST",
            help="PostgreSQL server host or socket directory [default: %(default)s]",
            default="127.0.0.1",
        )
        postgresqlgroup.add_argument(
            "--postgresql-port",
            dest="postgresql_port",
            metavar="PORT",
            type=int,
            help="PostgreSQL server port [default: %(default)d]",
            default=5432,
        )

        postgresqlgroup.add_argument(
            "--postgresql-user",
            dest="postgresql_user",
            metavar="USER",
            help="PostgreSQL username [default: %(default)s]",
            default="psetpartners",
        )

        postgresqlgroup.add_argument(
            "--postgresql-pass",
            dest="postgresql_password",
            metavar="PASS",
            help="PostgreSQL password [default: %(default)s]",
            default="", # Need to provide in secrets file instead
        )

        postgresqlgroup.add_argument(
            "--postgresql-dbname",
            dest="postgresql_dbname",
            metavar="DBNAME",
            help="PostgreSQL database name [default: %(default)s]",
            default="psetpartners",
        )

        emailgroup = parser.add_argument_group("emailing options:")
        emailgroup.add_argument(
            "--email-pass",
            dest="email_password",
            metavar="PASS",
            help="email account password [default: %(default)s]",
            default="", # Need to provide in secrets file instead
        )

        # undocumented options
        parser.add_argument(
            "--enable-profiler",
            dest="web_profiler",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        # undocumented flask options
        parser.add_argument(
            "--enable-reloader",
            dest="web_use_reloader",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--disable-reloader",
            dest="web_use_reloader",
            help=argparse.SUPPRESS,
            action="store_false",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--enable-debugger",
            dest="web_use_debugger",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--disable-debugger",
            dest="web_use_debugger",
            help=argparse.SUPPRESS,
            action="store_false",
            default=argparse.SUPPRESS,
        )
        writeargstofile = writeargstofile or os.path.split(sys.argv[0])[-1] == "start-psetpartners.py"
        _Configuration.__init__(self, parser, writeargstofile=writeargstofile)

    def get_flask(self):
        return dict(self.options["web"])

    def get_logging(self):
        return dict(self.options["logging"])

