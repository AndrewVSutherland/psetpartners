# This file is made up of selected bits copied from researchseminars.org's codebase.  It should be factored out at some point.

import pytz, datetime, logging
import re, ast
from collections.abc import Iterable
from markupsafe import Markup, escape
from flask import flash, render_template, request
from flask_login import current_user
from urllib.parse import urlparse

DEFAULT_TIMEZONE = 'America/New_York'
DEFAULT_TIMEZONE_NAME = 'MIT'
DEFAULT_TIMEZONE_PRETTY = 'MIT time'
MAX_STATUS = 6

MAX_SHORT_NAME_LEN = 40 # used for preferred name and group names
MAX_LONG_NAME_LEN = 60 # used for class names
MAX_ID_LEN = 16 # used for kerbs and course numbers
MAX_TEXT_LEN = 256
MAX_URL_LEN = 256

maxlength = {
    'class_name': MAX_LONG_NAME_LEN,
    'class_number': MAX_ID_LEN,
    'classes': 8,
    'departments': 3,
    'description': MAX_TEXT_LEN,
    'group_name' : MAX_SHORT_NAME_LEN,
    'homepage': MAX_URL_LEN,
    'link': MAX_URL_LEN,
    'kerb': MAX_ID_LEN,
    'instructor_kerbs': 16,
    'preferred_name' : MAX_SHORT_NAME_LEN,
    'preferred_pronouns': MAX_SHORT_NAME_LEN,
}

term_options = ["IAP", "spring", "summer", "fall"]
term_ends = [(1,22), (6,1), (8,20), (12,20)] # (month,day) pairs marking end of term

short_weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
posint_re_string = r"[1-9][0-9]*"
posint_re = re.compile(posint_re_string)
posint_range_re_string = posint_re_string + "-" + posint_re_string
posint_range_re = re.compile(posint_range_re_string)
daytime_re_string = r"\d{1,4}|\d{1,2}:\d\d|"
daytime_re = re.compile(daytime_re_string)
dash_re = re.compile(r'[\u002D\u058A\u05BE\u1400\u1806\u2010-\u2015\u2E17\u2E1A\u2E3A\u2E3B\u2E40\u301C\u3030\u30A0\uFE31\uFE32\uFE58\uFE63\uFF0D]')
class_name_re = re.compile(r"[a-zA-Z0-9 ,.;:?!&/@#'()\-]+")
kerb_re = re.compile(r"^[a-z][a-z0-9_]+$")

# null_logger used as default for verbose logginng
def null_logger():
    logger = logging.getLogger("null")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
    return logger

def domain():
    return urlparse(request.url).netloc

def valid_url(x):
    if not (x.startswith("http://") or x.startswith("https://")):
        return False
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False

def current_year():
    """Returns the current/upcoming calendar year (switches to next calendar year after the end of the fall term)"""
    now = datetime.datetime.now()
    today = (now.month, now.day)
    return datetime.datetime.now().year + (0 if today <= term_ends[-1] else 1)

def current_term():
    """Returns the current/upcoming term"""
    now = datetime.datetime.now()
    today = (now.month, now.day)
    for i in range(len(term_ends)):
        if today <= term_ends[i]:
            return i
    return 0

def current_term_start_date():
    now = datetime.datetime.now()
    today = (now.month, now.day)
    if today <= term_ends[0]:
        return datetime.date(now.year-1, term_ends[-1][0], term_ends[-1][1]+1)
    else:
        t = current_term()
        return datetime.date(now.year, term_ends[t-1][0], term_ends[t-1][1]+1)

def current_term_end_date():
    now = datetime.datetime.now()
    today = (now.month, now.day)
    if today > term_ends[-1]:
        return datetime.date(now.year+1, term_ends[-1][0], term_ends[0][1])
    else:
        t = current_term()
        return datetime.date(now.year, term_ends[t][0], term_ends[t][1])

def default_match_dates():
    s = current_term_start_date()
    e = current_term_end_date()
    s += datetime.timedelta(days=(4-s.weekday())%7)
    w = datetime.timedelta(days=7)
    s += w
    return [s+i*w for i in range(15) if s+i*w < e]

def current_term_pretty():
    return term_options[current_term()] + " " + str(current_year())

def cleanse_dashes(s):
    # replace unicode variants of dashes (which users might cut-and-paste) with ascii dashes
    return '-'.join(re.split(dash_re,s))

def validate_class_name(s):
    return class_name_re.fullmatch(s) and len(s) > 3 and len(s) <= MAX_LONG_NAME_LEN

#TODO: handle strings encoding lists of strings that may contain commas
def list_of_strings(inp):
    if inp is None:
        return []
    if isinstance(inp, str):
        inp = inp.strip()
        if not inp:
            return []
        # if there are any quotes present, use literal_eval
        if "'" in inp or '"' in inp:
            if inp[0] != "[":
                inp = "[" + inp + "]"
            return ast.literal_eval(inp)
        if len(inp) == 1:
            return ["",""] if inp == "," else [inp]
        if inp[0] == "[" and inp[-1] == "]":
            inp = inp[1:-1].strip();
        if not inp:
            return []
        if not "," in inp:
            return [inp]
        return [elt.strip() for elt in inp.split(",")]
    if isinstance(inp, Iterable):
        inp = [elt for elt in inp]
    raise ValueError("Unrecognized input, expected a list of strings")

def naive_utcoffset(tz):
    if isinstance(tz, str):
        if tz == DEFAULT_TIMEZONE_NAME:
            tz = DEFAULT_TIMEZONE
        tz = pytz.timezone(tz)
    for h in range(10):
        try:
            return tz.utcoffset(datetime.datetime.now() + datetime.timedelta(hours=h))
        except (
            pytz.exceptions.NonExistentTimeError,
            pytz.exceptions.AmbiguousTimeError,
        ):
            pass

def hours_from_default(tz):
    if not tz:
        return 0
    delta = int(naive_utcoffset(tz).total_seconds()) - int(naive_utcoffset(DEFAULT_TIMEZONE).total_seconds())
    hours, remainder = divmod(abs(delta), 3600)
    if remainder > 1800:
        hours += 1
    return hours if delta >= 0 else -hours

def pretty_timezone(tz, dest="selecter", base_name='UTC', base_timezone='UTC'):
    delta = int(naive_utcoffset(tz).total_seconds()) - int(naive_utcoffset(base_timezone).total_seconds())
    hours, remainder = divmod(abs(delta), 3600)
    minutes, seconds = divmod(remainder, 60)
    if dest == "selecter":  # used in time zone selecters
        if delta < 0:
            diff = "-{:02d}:{:02d}".format(hours, minutes)
        else:
            diff = "+{:02d}:{:02d}".format(hours, minutes)
        return "({}{}) {}".format(base_name, diff, tz)
    else:
        tz = str(tz).replace("_", " ")
        if minutes == 0:
            diff = "{}".format(hours)
        else:
            diff = "{}:{:02d}".format(hours, minutes)
        if delta < 0:
            diff = "-" + diff
        else:
            diff = "+" + diff
        return "{} ({} {})".format(tz, base_name, diff)

timezones = [(DEFAULT_TIMEZONE_NAME, DEFAULT_TIMEZONE_PRETTY)] + [
    (v, pretty_timezone(v, base_name=DEFAULT_TIMEZONE_NAME, base_timezone=DEFAULT_TIMEZONE)) for v in sorted(pytz.common_timezones, key=naive_utcoffset)
]

def format_errmsg(errmsg, *args):
    return Markup((errmsg % tuple("<i><b>%s</b></i>" % escape(x) for x in args)))

def format_input_errmsg(err, inp, col):
    return format_errmsg('Unable to process input "%s" for property %s because %s', inp, col, err)

def flash_info(msg):
    flash(msg, "info")

def flash_notify(msg):
    # don't display blank notifications
    if not msg:
        return
    if msg[:6].lower() == "error:":
        flash_error(msg[6:])
    else:
        flash(msg, "notify")

def flash_instruct(msg):
    flash(msg, "instruct")

def flash_announce(msg):
    flash(msg, "announce")

def flash_warning(msg):
    flash(msg, "warning")

def flash_error(msg):
    from .app import app

    app.logger.error("flashing error to user %s: %s" %(current_user.kerb,msg))
    flash(msg, "error")

def show_input_errors(errmsgs):
    assert errmsgs
    for msg in errmsgs:
        flash_error(msg)
    return render_template("inputerror.html", title="input error")

def process_user_input(inp, col, typ, tz=None, falseblankbool=False, zeroblankint=False):
    """
    INPUT:

    - ``inp`` -- unsanitized input, as a string (or None)
    - ''col'' -- column name (names ending in ''link'', ''page'', ''time'', ''email'' get special handling
    - ``typ`` -- a Postgres type, as a string
    """
    assert isinstance(inp, str)
    inp = inp.strip()
    if typ == "boolean":
        if not inp:
            return False if falseblankbool else None
        if inp in ["yes", "true", "y", "t", True]:
            return True
        elif inp in ["no", "false", "n", "f", False]:
            return False
        raise ValueError("Invalid boolean")
    elif typ == "text":
        if col.endswith("timezone"):
            return inp if (inp == DEFAULT_TIMEZONE_NAME or pytz.timezone(inp)) else ""
        if col in maxlength and len(inp) > maxlength[col]:
            raise ValueError("Input exceeds maximum length permitted")
        # should sanitize somehow?
        return "\n".join(inp.splitlines())
    elif typ == "posint":
        if posint_re.fullmatch(inp):
            return int(inp)
        raise ValueError("Invalid positive integer")
    elif typ in ["int", "smallint", "bigint", "integer"]:
        if not inp:
            return 0 if zeroblankint else None
        return int(inp)
    elif typ == "text[]":
        res = list_of_strings(inp)
        if col in maxlength and len(res) > maxlength[col]:
            raise ValueError("Input exceeds maximum length permitted")
        return res
    else:
        raise ValueError("Unrecognized type %s" % typ)
