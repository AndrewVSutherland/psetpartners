# -*- coding: utf-8 -*-
import os
import time
import logging

from flask import (
    Flask,
    render_template,
    request,
    make_response,
    url_for,
    current_app,
)
from psetpartners.utils import (
    current_upcoming,
    current_term_pretty,
    domain,
    )

############################
#         Main app         #
############################

app = Flask(__name__, static_url_path="", static_folder="static",)

@app.before_first_request
def setup():
    from .config import Configuration
    formatter = logging.Formatter("""%(asctime)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n  %(message)s""")

    logger = logging.getLogger("psetpartners")
    logger.setLevel(logging.INFO)
    logfile = Configuration().get_logging()["logfile"]
    ch = logging.FileHandler(logfile)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    app.logger.info("pset partners restarted")

############################
# App attribute functions  #
############################

def is_livesite():
    return ( domain() == "psetpartners.mit.du" )

def is_debug_mode():
    from flask import current_app

    return current_app.debug

app.is_running = False

def set_running():
    app.is_running = True

def is_running():
    return app.is_running

def under_construction():
    return is_livesite() # TODO: change this line when we go live

############################
# Global app configuration #
############################

# disable cache temporarily
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# If the debug toolbar is installed then use it
if app.debug:
    try:
        from flask_debugtoolbar import DebugToolbarExtension
        app.config["SECRET_KEY"] = """shh, it's a secret"""
        toolbar = DebugToolbarExtension(app)
    except ImportError:
        pass

# secret key, necessary for sessions and tokens
# sessions are in turn necessary for users to login
from .config import get_secret_key
app.secret_key = get_secret_key()

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True

# enable break and continue in jinja loops
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
app.jinja_env.add_extension("jinja2.ext.do")

@app.template_filter("blanknone")
def blanknone(x):
    return "" if x is None else str(x)

# the following context processor inserts
#  * empty info={} dict variable
@app.context_processor
def ctx_proc_userdata():
    # insert an empty info={} as default
    # set the body class to some default, blueprints should
    # overwrite it with their name, using @<blueprint_object>.context_processor
    # see http://flask.pocoo.org/docs/api/?highlight=context_processor#flask.Blueprint.context_processor
    data = {"info": {} }
    data["meta_description"] = r"Welcome to psetpartners, a tool for finding others to help work on problem sets!"
    data["LINK_EXT"] = lambda a, b: '<a href="%s" target="_blank">%s</a>' % (b, a)
    data["DEBUG"] = is_debug_mode()
    data["domain"] = domain()
    data["current_upcoming"] = current_upcoming()
    data["current_term_pretty"] = current_term_pretty()
    data["livesite"] = is_livesite()
    data["under_construction"] = under_construction()
    return data

##############################
#    Redirects and errors    #
##############################

def timestamp():
    return "[%s UTC]" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

@app.errorhandler(404)
def not_found_404(error):
    app.logger.info("%s 404 error for URL %s %s" % (timestamp(), request.url, error.description))
    messages = (
        error.description if isinstance(error.description, (list, tuple)) else (error.description,)
    )
    return render_template("404.html", title="page not found", messages=messages), 404

@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s %s" % (timestamp(), request.url, error.args))
    return render_template("500.html", title="error"), 500

@app.errorhandler(503)
def not_found_503(error):
    return render_template("503.html"), 503


##############################
#       Top-level pages      #
##############################

@app.route("/health")
@app.route("/alive")
def alive():
    msg = "psetpartners is alive and well at %s" % domain()
    app.logger.info(msg)
    return msg

@app.route("/acknowledgments")
def acknowledgment():
    return render_template("acknowledgments.html", title="acknowledgments")

@app.route("/contact")
def contact():
    return render_template("contact.html", title="contact")

@app.route("/robots.txt")
def robots_txt():
    if "psetpartners" in request.url_root.lower():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    return "User-agent: *\nDisallow: / \n"

@app.route("/humans.txt")
def humans_txt():
    return render_template("acknowledgments.html", title="acknowledgments")

def routes():
    """
    Returns all routes
    """
    links = []
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if "GET" in rule.methods:  # and has_no_empty_params(rule):
            try:
                url = url_for(rule.endpoint, **(rule.defaults or {}))
            except Exception:
                url = None
            links.append((url, str(rule)))
    return sorted(links, key=lambda elt: elt[1])

@app.route("/sitemap")
def sitemap():
    """
    Listing all routes
    """
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><a href="{0}">{1}</a></li>'.format(url, endpoint)
                if url is not None
                else "<li>{0}</li>".format(endpoint)
                for url, endpoint in routes()
            ]
        )
        + "</ul>"
    )

##############################
#       CSS Styling          #
##############################

@app.route("/style.css")
def css():
    response = make_response(render_template("style.css"))
    response.headers["Content-type"] = "text/css"
    # don't cache css file, if in debug mode.
    if current_app.debug:
        response.headers["Cache-Control"] = "no-cache, no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=600"
    return response

