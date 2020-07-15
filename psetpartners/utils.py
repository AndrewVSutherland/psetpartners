# This file is made up of selected bits copied from researchseminars.org's codebase.  It should be factored out at some point.


import pytz
from datetime import datetime, timedelta
from markupsafe import Markup, escape
from flask import flash, render_template
from dateutil.parser import parse as parse_time
from flask_login import current_user

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

def pretty_timezone(tz, dest="selecter"):
    foo = int(naive_utcoffset(tz).total_seconds())
    hours, remainder = divmod(abs(foo), 3600)
    minutes, seconds = divmod(remainder, 60)
    if dest == "selecter":  # used in time zone selecters
        if foo < 0:
            diff = "-{:02d}:{:02d}".format(hours, minutes)
        else:
            diff = "+{:02d}:{:02d}".format(hours, minutes)
        return "(UTC {}) {}".format(diff, tz)
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
        if dest == "browse":  # used on browse page by filters
            return "{} (now UTC {})".format(tz, diff)
        else:
            return "{} (UTC {})".format(tz, diff)

timezones = [
    (v, pretty_timezone(v)) for v in sorted(pytz.common_timezones, key=naive_utcoffset)
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

def flash_error(errmsg, *args):
    """ flash errmsg in red with args in black; errmsg may contain markup, including latex math mode"""
    flash(Markup("Error: " + (errmsg % tuple("<span style='color:black'>%s</span>" % escape(x) for x in args))), "error")

def show_input_errors(errmsgs):
    """ Flashes a list of specific user input error messages then displays a generic message telling the user to fix the problems and resubmit. """
    assert errmsgs
    for msg in errmsgs:
        flash(msg, "error")
    return render_template("inputerror.html", messages=errmsgs)

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

maxlength = {} # TODO: add max length values for user input

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
