# This file is made up of selected bits copied from researchseminars.org's codebase.  It should be factored out at some point.

import pytz
import re, ast
from collections.abc import Iterable
from datetime import time as maketime
from datetime import datetime, timedelta
from markupsafe import Markup, escape
from flask import flash, render_template
from dateutil.parser import parse as parse_time
from flask_login import current_user

DEFAULT_TIMEZONE = 'America/New_York'
DEFAULT_TIMEZONE_NAME = 'MIT'
DEFAULT_TIMEZONE_PRETTY = 'MIT time'

MAX_SHORT_NAME_LEN = 48 # used for preferred name and group names
MAX_LONG_NAME_LEN = 96 # used for class names
MAX_ID_LEN = 16 # used for kerbs and course numbers
MAX_TEXT_LEN = 256
MAX_URL_LEN = 256

maxlength = {
    'class_name': MAX_LONG_NAME_LEN,
    'class_number': MAX_ID_LEN,
    'classes': 8,
    'departments': 4,
    'description': MAX_TEXT_LEN,
    'group_name' : MAX_SHORT_NAME_LEN,
    'homepage': MAX_URL_LEN,
    'instructor_names': 4,
    'instructor_name' : MAX_SHORT_NAME_LEN,
    'kerb': MAX_ID_LEN,
    'instructor_kerbs': 4,
    'instructor_kerb' : MAX_SHORT_NAME_LEN,
    'preferred_name' : MAX_SHORT_NAME_LEN,
    'preferred_pronouns': MAX_SHORT_NAME_LEN,
}

term_options = ["IAP", "spring", "summer", "fall"]

short_weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
posint_re_string = r"[1-9][0-9]*"
posint_re = re.compile(posint_re_string)
posint_range_re_string = posint_re_string + "-" + posint_re_string
posint_range_re = re.compile(posint_range_re_string)
daytime_re_string = r"\d{1,4}|\d{1,2}:\d\d|"
daytime_re = re.compile(daytime_re_string)
dash_re = re.compile(r'[\u002D\u058A\u05BE\u1400\u1806\u2010-\u2015\u2E17\u2E1A\u2E3A\u2E3B\u2E40\u301C\u3030\u30A0\uFE31\uFE32\uFE58\uFE63\uFF0D]')

def current_year():
    return datetime.now().year

def current_term():
    """ Returns the current/upcoming term, which is currently always 1 (spring) or 3 (fall)"""
    return 1 if datetime.now().month < 6 else 3

def current_term_pretty():
    return term_options[current_term()] + " " + str(current_year())

def current_upcoming():
    return "current" if datetime.now().month in [2,3,4,5,9,10,11,12] else "upcoming"

def localize_time(t, newtz=None):
    """
    Takes a time or datetime object and adds in a timezone if not already present.
    """
    if t.tzinfo is None:
        if newtz is None:
            newtz = current_user.tz
        return newtz.localize(t)
    else:
        return t

def cleanse_dashes(s):
    # replace unicode variants of dashes (which users might cut-and-paste) with ascii dashes
    return '-'.join(re.split(dash_re,s))

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
        if not "," in inp:
            return [inp]
        return [elt.strip() for elt in inp.split(",")]
    if isinstance(inp, Iterable):
        inp = [elt for elt in inp]
    raise ValueError("Unrecognized input, expected a list of strings")

def validate_daytime(s):
    if not daytime_re.fullmatch(s):
        return None
    if len(s) <= 2:
        h, m = int(s), 0
    elif not ":" in s:
        h, m = int(s[:-2]), int(s[-2:])
    else:
        t = s.split(":")
        h, m = int(t[0]), int(t[1])
    return "%02d:%02d" % (h, m) if (0 <= h < 24) and (0 <= m <= 59) else None

def validate_daytimes(s):
    t = s.split('-')
    if len(t) != 2:
        return None
    start, end = validate_daytime(t[0].strip()), validate_daytime(t[1].strip())
    if start is None or end is None:
        return None
    return start + "-" + end

def daytime_minutes(s):
    t = s.split(":")
    return 60 * int(t[0]) + int(t[1])


def daytimes_start_minutes(s):
    return daytime_minutes(s.split('-')[0])

def midnight(date, tz):
    return localize_time(datetime.combine(date, maketime()), tz)

def weekstart(date, tz):
    t = midnight(date,tz)
    return t - timedelta(days=1)*t.weekday()

def date_and_daytime_to_time(date, s, tz):
    d = localize_time(datetime.combine(date, maketime()), tz)
    m = timedelta(minutes=1)
    return d + m * daytime_minutes(s)

def date_and_daytimes_to_times(date, s, tz):
    d = localize_time(datetime.combine(date, maketime()), tz)
    m = timedelta(minutes=1)
    t = s.split("-")
    start = d + m * daytime_minutes(t[0])
    end = d + m * daytime_minutes(t[1])
    if end < start:
        end += timedelta(days=1)
    return start, end

def naive_utcoffset(tz):
    if isinstance(tz, str):
        tz = pytz.timezone(tz)
    for h in range(10):
        try:
            return tz.utcoffset(datetime.now() + timedelta(hours=h))
        except (
            pytz.exceptions.NonExistentTimeError,
            pytz.exceptions.AmbiguousTimeError,
        ):
            pass

def pretty_timezone(tz, dest="selecter", base_name='UTC', base_timezone='UTC'):
    foo = int(naive_utcoffset(tz).total_seconds()) - int(naive_utcoffset(base_timezone).total_seconds())
    foo 
    hours, remainder = divmod(abs(foo), 3600)
    minutes, seconds = divmod(remainder, 60)
    if dest == "selecter":  # used in time zone selecters
        if foo < 0:
            diff = "-{:02d}:{:02d}".format(hours, minutes)
        else:
            diff = "+{:02d}:{:02d}".format(hours, minutes)
        return "({} {}) {}".format(base_name, diff, tz)
    else:
        tz = str(tz).replace("_", " ")
        if minutes == 0:
            diff = "{}".format(hours)
        else:
            diff = "{}:{:02d}".format(hours, minutes)
        if foo < 0:
            diff = "-" + diff
        else:
            diff = "+" + diff
        return "{} ({} {})".format(tz, base_name, diff)

timezones = [(DEFAULT_TIMEZONE_NAME, DEFAULT_TIMEZONE_PRETTY)] + [
    (v, pretty_timezone(v, base_name=DEFAULT_TIMEZONE_NAME, base_timezone=DEFAULT_TIMEZONE)) for v in sorted(pytz.common_timezones, key=naive_utcoffset)
]

def format_errmsg(errmsg, *args):
    return Markup(
        "Error: "
        + (
            errmsg
            % tuple("<span style='color:black'>%s</span>" % escape(x) for x in args)
        )
    )

def format_input_errmsg(err, inp, col):
    return format_errmsg(
        "Unable to process input %s for property %s: {0}".format(err),
        '"' + str(inp) + '"',
        col,
    )

def flash_info(msg):
    flash(msg, "info")

def flash_warning(msg):
    flash(msg, "warning")

def flash_error(msg):
    flash(msg, "error")

def show_input_errors(errmsgs):
    """ Flashes a list of specific user input error messages then displays a generic message telling the user to fix the problems and resubmit. """
    assert errmsgs
    for msg in errmsgs:
        flash_error(msg)
    return render_template("inputerror.html", messages=errmsgs)

def process_user_input(inp, col, typ, tz=None, falseblankbool=False, zeroblankint=False):
    """
    INPUT:

    - ``inp`` -- unsanitized input, as a string (or None)
    - ''col'' -- column name (names ending in ''link'', ''page'', ''time'', ''email'' get special handling
    - ``typ`` -- a Postgres type, as a string
    """
    assert isinstance(inp, str)
    inp = inp.strip()
    if col in maxlength and len(inp) > maxlength[col]:
        raise ValueError("Input exceeds maximum length permitted")
    if typ == "time":
        # Note that parse_time, when passed a time with no date, returns
        # a datetime object with the date set to today.  This could cause different
        # relative orders around daylight savings time, so we store all times
        # as datetimes on Jan 1, 2020.
        if inp.isdigit():
            inp += ":00"  # treat numbers as times not dates
        t = parse_time(inp)
        t = t.replace(year=2020, month=1, day=1)
        assert tz is not None
        return localize_time(t, tz)
    elif typ == "timestamp with time zone":
        assert tz is not None
        return localize_time(parse_time(inp), tz)
    elif typ == "daytimes":
        inp = cleanse_dashes(inp)
        res = validate_daytimes(inp)
        if res is None:
            raise ValueError("Invalid times of day, expected format is hh:mm-hh:mm")
        return res
    elif typ == "weekday_number":
        res = int(inp)
        if res < 0 or res >= 7:
            raise ValueError("Invalid day of week, must be an integer in [0,6]")
        return res
    elif typ == "date":
        return parse_time(inp).date()
    elif typ == "boolean":
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
        # should sanitize somehow?
        return "\n".join(inp.splitlines())
    elif typ == "posint":
        if posint_re.fullmatch(inp):
            return int(inp)
        raise ValueError("Invalid positive integer")
    elif typ == "posint_range":
        if posint_re.fullmatch(inp):
            return [int(inp),int(inp)]
        if posint_range_re.fullmatch(inp):
            res = [int(n) for n in inp.split("-")]
            if res[0] > res[1]:
                raise ValueError("Invalid range of positive integers")
            return res
        raise ValueError
    elif typ in ["int", "smallint", "bigint", "integer"]:
        if not inp:
            return 0 if zeroblankint else None
        return int(inp)
    elif typ == "text[]":
        return list_of_strings(inp)
    else:
        raise ValueError("Unrecognized type %s" % typ)
