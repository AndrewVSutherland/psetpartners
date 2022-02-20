# -*- coding: utf-8 -*-
import os
import time
import logging
import getpass
import datetime

from .config import Configuration

from flask_mail import Mail, Message

from flask import (
    Flask,
    render_template,
    request,
    make_response,
    url_for,
    current_app,
    session
)
from .utils import (
    current_term,
    current_year,
    current_term_pretty,
    domain,
    )

############################
#         Main app         #
############################

app = Flask(__name__, static_url_path="", static_folder="static",)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# IMPORTANT: the lines below ensure security of cookies
# The check for the username is to allow non-https connections when running local for development
if getpass.getuser() == 'psetpartners':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_DURATION=datetime.timedelta(days=1),
    )

mail_settings = {
    "MAIL_SERVER": Configuration().options['email']['host'],
    "MAIL_PORT":  Configuration().options['email']['port'],
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": Configuration().options['email']['username'],
    "MAIL_PASSWORD": Configuration().options['email']['password'],
}

email_sender = Configuration().options['email']['username'] + '@' + Configuration().options['email']['domain']
email_bcc = Configuration().options['email'].get('bcc')

app.config.update(mail_settings)
mail = Mail(app)

@app.before_first_request
def setup():
    formatter = logging.Formatter("""%(asctime)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n  %(message)s""")

    logger = logging.getLogger("psetpartners")
    logger.setLevel(logging.INFO)
    logfile = Configuration().get_logging()["logfile"]
    ch = logging.FileHandler(logfile)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

############################
# App attribute functions  #
############################

def livesite():
    try:
        return ( domain() == "psetpartners.mit.edu" )
    except Exception:
        return False

def debug_mode():
    from flask import current_app

    return current_app.debug

def under_construction():
    return False
    # return livesite()

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
    data["DEBUG"] = debug_mode()
    data["domain"] = domain()
    data["current_term"] = current_term()
    data["current_year"] = current_year()
    data["current_term_pretty"] = current_term_pretty()
    data["livesite"] = livesite()
    data["under_construction"] = under_construction()
    return data

##############################
#    Redirects and errors    #
##############################

def timestamp():
    return "[%s UTC]" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

@app.errorhandler(404)
def not_found_404(error):
    app.logger.info("%s 404 error for URL %s by user %s: %s" % (timestamp(), request.url, session.get("kerb","[unknown]"), error.description))
    messages = (
        error.description if isinstance(error.description, (list, tuple)) else (error.description,)
    )
    return render_template("404.html", title="page not found", messages=messages), 404

@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s by user %s: %s" % (timestamp(), request.url, session.get("kerb","[unknown]"), error.args))
    return render_template("500.html"), 500

@app.errorhandler(503)
def not_found_503(error):
    return render_template("503.html"), 503


##############################
#       Top-level pages      #
##############################

@app.route("/health")
@app.route("/alive")
def alive():
    msg = 'psetpartners is alive and well at "%s", which %s the live site' % (domain(), "is" if livesite() else "is not")
    app.logger.info(msg)
    return msg

@app.route("/about")
def about():
    return render_template("about.html", title="about")

@app.route("/acknowledgments")
def acknowledgment():
    return render_template("acknowledgments.html", title="acknowledgments")

@app.route("/contact")
def contact():
    return render_template("contact.html", title="contact")

@app.route("/conduct")
def conduct():
    return render_template("conduct.html", title="conduct")

@app.route("/faq")
def faq():
    return render_template("faq.html", title="FAQ")

@app.route("/barf")
def barf():
    raise ValueError("You made me barf!")

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

##############################
#           Mail             #
##############################

def send_email(to, subject, message, cc=[]):
    from html2text import html2text
    from .dbwrapper import get_forcelive

    if isinstance(to,str):
        to = [to]
    bcc = email_bcc
    if isinstance(bcc,str):
        bcc = [bcc.strip()]

    if (not get_forcelive() and not livesite()) or under_construction():
        if email_bcc is None or not email_bcc.strip():
            return
        subject += " [%s, should have been sent to %s]" % ('live' if livesite() else 'test', to)
        to = bcc
        bcc = []
        cc = []
    else:
        if get_forcelive():
            print("forcing live email!")

    app.logger.info("%s sending email from %s to %s..." % (timestamp(), email_sender, to))
    mail.send(
        Message(
            subject=subject,
            html=message,
            body=html2text(message),
            sender=email_sender,
            recipients=to,
            cc=cc,
            bcc=bcc,
        )
    )
