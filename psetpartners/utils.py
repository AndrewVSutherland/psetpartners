# This file is made up of selected bits copied from researchseminars.org's codebase.  It should be factored out at some point.


import pytz
import re
from collections.abc import Iterable
from datetime import time as maketime
from datetime import datetime, timedelta
from markupsafe import Markup, escape
from flask import flash, render_template
from dateutil.parser import parse as parse_time
from flask_login import current_user

DEFAULT_TIMEZONE = 'America/New_York'
DEFAULT_TIMEZONE_PREFIX = 'MIT'
DEFAULT_TIMEZONE_PRETTY = 'MIT time'

strength_options = ["", "nice to have", "weakly preferred", "preferred", "strongly preferred", "required"]
term_options = ["IAP", "spring", "summer", "fall"]

gender_options = [
    ("female", "female"),
    ("male", "male"),
    ("non-binary", "non-binary"),
    ]

gender_affinity_options = [
    (1, "someone else with my gender identity"),
    (2, "only students with my gender identity"),
    ]

year_affinity_options = [
    (1, "someone else in my year"),
    (2, "only students in my year"),
    ]

year_options = [
    (1, "first year"),
    (2, "sophomore"),
    (3, "junior"),
    (4, "senior or super senior"),
    (5, "graduate student"),
    ]

forum_options = [
    ("text", "text (e.g. Slack or Zulip)"),
    ("video", "video (e.g. Zoom)"),
    ("in-person", "in person"),
    ]

start_options = [
    (6, "shortly after the problem set is posted"),
    (4, "3-4 days before the pset is due"),
    (2, "1-2 days before the pset is due"),
    ]

together_options = [
    (1, "solve the problems together"),
    (2, "discuss strategies, work together if stuck"),
    (3, "work independently but check answers"),
    ]

group_size_options = [
    (2, "2 students"),
    (3, "3-4 students"),
    (5, "5-8 students"),
    (8, "more than 8 students"),
    ]

location_options = [
    ("near", "on campus or near MIT"),
    ("far", "not hear MIT"),
    #("baker", "Baker House"),
    #("buron-conner", "Burton Conner House"),
    #("east", "East Campus"),
    #("macgregor", "MacGregor House"),
    #("maseeh", "Maseeh Hall"),
    #("mccormick", "McCormick Hall"),
    #("new", "New House"),    
    #("next", "Next House"),
    #("random", "Random Hall"),
    #("simmons", "Simmons Hall"),
    #("epsilontheta", "Epsilon Theta"),
    #("fenway", "Fenway House"),
    #("pika", "pika"),
    #("student", "Student House"),
    #("wilg", "WILG"),
    #("amherst", "70 Amherst Street"),
    #("ashdown", "Ashdown House"),
    #("edgerton", "Edgerton House"),
    #("tower4", "Graduate Tower at Site 4"),
    #("sidneypacific", "Sidney-Pacific"),
    #("tang", "Tang Hall"),
    #("warehouse", "The Warehous"),
    #("westgate", "Westgate"),    
    ]

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
    """ Returns the current term (0,1,2,3,4) to be used when listing courses add (possibly before the term starts) """
    t = datetime.now()
    if t.month == 1:
        return 0 if t.day <= 15 else 1 # IAP or spring
    if t.month < 6:
        return 1 # spring
    if t.month < 7 or (t.month==7 and t.day<25):
        return 2 # summer
    if t.month < 12:
        return 3 # fall
    return 3 if t.day <= 15 else 0 # fall or IAP

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
    # replace unicode variants of dashes (which users might cut-and-paste in) with ascii dashes
    return '-'.join(re.split(dash_re,s))

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

MAX_SHORT_NAME_LEN = 48 # used for preferred name and group names
MAX_LONG_NAME_LEN = 96 # used for class names
MAX_ID_LEN = 16 # used for kerbs and course numbers
MAX_TEXT_LEN = 256
MAX_URL_LEN = 256

maxlength = {
    'class_name': MAX_LONG_NAME_LEN,
    'class_number': MAX_ID_LEN,
    'classes': 6,
    'description': MAX_TEXT_LEN,
    'group_name' : MAX_SHORT_NAME_LEN,
    'homepage': MAX_URL_LEN,
    'instructor_name' : MAX_SHORT_NAME_LEN,
    'kerb': MAX_ID_LEN,
    'instructor_kerb' : MAX_SHORT_NAME_LEN,
    'preferred_name' : MAX_SHORT_NAME_LEN,
    'preferred_pronouns': MAX_SHORT_NAME_LEN,
}

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

def pretty_timezone(tz, dest="selecter", base_prefix='UTC', base_timezone='UTC'):
    foo = int(naive_utcoffset(tz).total_seconds()) - int(naive_utcoffset(base_timezone).total_seconds())
    foo 
    hours, remainder = divmod(abs(foo), 3600)
    minutes, seconds = divmod(remainder, 60)
    if dest == "selecter":  # used in time zone selecters
        if foo < 0:
            diff = "-{:02d}:{:02d}".format(hours, minutes)
        else:
            diff = "+{:02d}:{:02d}".format(hours, minutes)
        return "({} {}) {}".format(base_prefix, diff, tz)
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
        return "{} ({} {})".format(tz, base_prefix, diff)

timezones = [('', DEFAULT_TIMEZONE_PRETTY)] + [
    (v, pretty_timezone(v, base_prefix=DEFAULT_TIMEZONE_PREFIX, base_timezone=DEFAULT_TIMEZONE)) for v in sorted(pytz.common_timezones, key=naive_utcoffset)
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

def process_user_input(inp, col, typ, tz=None):
    """
    INPUT:

    - ``inp`` -- unsanitized input, as a string (or None)
    - ''col'' -- column name (names ending in ''link'', ''page'', ''time'', ''email'' get special handling
    - ``typ`` -- a Postgres type, as a string
    """
    if inp and isinstance(inp, str):
        inp = inp.strip()
    if inp == "":
        return False if typ == "boolean" else ("" if typ == "text" else None)
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
        if inp in ["yes", "true", "y", "t", True]:
            return True
        elif inp in ["no", "false", "n", "f", False]:
            return False
        raise ValueError("Invalid boolean")
    elif typ == "text":
        if col.endswith("timezone"):
            return inp if pytz.timezone(inp) else ""
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
        return int(inp)
    elif typ == "text[]":
        if inp == "":
            return []
        elif isinstance(inp, str):
            if inp[0] == "[" and inp[-1] == "]":
                res = [elt.strip().strip("'") for elt in inp[1:-1].split(",")]
                if res == [""]:  # was an empty array
                    return []
                else:
                    return res
            else:
                return [inp]
        elif isinstance(inp, Iterable):
            return [str(x) for x in inp]
        else:
            raise ValueError("Unrecognized input")
    else:
        raise ValueError("Unrecognized type %s" % typ)
