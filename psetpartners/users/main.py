
from flask import (
    render_template,
    Blueprint,
    url_for,
    redirect,
    request,
    flash,
)
from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
    LoginManager,
)
from datetime import datetime
from markupsafe import Markup
from psetpartners import db
from .student import Student, AnonymousStudent, preference_types
from psetpartners.utils import (
    timezones,
    format_input_errmsg,
    show_input_errors,
    process_user_input,
    maxlength,
    short_weekdays,
    daytime_minutes,
    gender_options,
    year_options,
    location_options,
    gender_affinity_options,
    year_affinity_options,
    strength_options,
    forum_options,
    start_options,
    together_options,
)
from psetpartners.app import app

login_page = Blueprint("user", __name__, template_folder="templates")
login_manager = LoginManager()

@login_manager.user_loader
def load_user(kerb):
    return Student(kerb)

login_manager.login_view = "user.info"

login_manager.anonymous_user = AnonymousStudent

def info_options():
    return {'year': year_options,
            'year_affinity': year_affinity_options,
            'gender': gender_options,
            'gender_affinity': gender_affinity_options,
            'strength': strength_options,
            'forum': forum_options,
            'start': start_options,
            'together': together_options,
            'location': location_options,
            'timezones' : timezones,
            'weekday' : short_weekdays,
            }

# globally define user properties and username
@app.context_processor
def ctx_proc_userdata():
    userdata = {
        "user": current_user,
        "usertime": datetime.now(tz=current_user.tz),
    }
    return userdata

@login_page.route("/login", methods=["POST"])
def login():
    identifier = request.form["identifier"]
    user = Student(kerb=identifier)
    # For now, no password check
    # The following sets current_user = user
    login_user(user, remember=True)
    if user.preferred_names:
        flash(Markup("Hello %s, your login was successful!" % user.preferred_name))
    else:
        flash(Markup("Hello, your login was successful!"))
    return redirect(request.form.get("next") or url_for(".info"))

@login_page.route("/info")
def info():
    if current_user.is_authenticated:
        title = "Pset Partners"
    else:
        title = "Login"
    return render_template(
        "user-info.html",
        next=request.args.get("next", ""),
        title=title,
        options=info_options(),
        maxlength={"time_slots":12},
    )

@login_page.route("/set_info", methods=["POST"])
@login_required
def set_info():
    errmsgs = []
    prefs = {}
    sprefs = {}
    data = {"preferences": prefs, "strengths": sprefs}
    raw_data = request.form
    n = int(raw_data.get("num_slots"))
    tz = current_user.tz
    data["weekdays"], data["time_slots"] = [], []
    for i in range(n):
        weekday = daytimes = None
        try:
            col = "weekday" + str(i)
            val = raw_data.get(col, "")
            weekday = process_user_input(val, col, "weekday_number", tz)
            col = "time_slot" + str(i)
            val = raw_data.get(col, "")
            daytimes = process_user_input(val, col, "daytimes", tz)
        except Exception as err:  # should only be ValueError's but let's be cautious
            errmsgs.append(format_input_errmsg(err, val, col))
            raise
        if weekday is not None and daytimes is not None:
            data["weekdays"].append(weekday)
            data["time_slots"].append(daytimes)
    if len(data["weekdays"]) > 1:
        x = sorted(
            list(zip(data["weekdays"], data["time_slots"])),
            key=lambda t: t[0] * 24 * 60 + daytime_minutes(t[1].split("-")[0]),
        )
        data["weekdays"], data["time_slots"] = [t[0] for t in x], [t[1] for t in x]
    # Need to do data validation
    for col, val in request.form.items():
        if col in db.students.col_type:
            try:
                typ = db.students.col_type[col]
                data[col] = process_user_input(val, col, typ)
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        elif col.startswith("pref_"):
            col = col[5:]
            try:
                typ = preference_types[col]
                prefs[col] = process_user_input(val, col, typ)
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
    if "group_size" in prefs and prefs["group_size"][1] <= 1:
        errmsgs.append("Invalid group size, maximum must be greater than one!")
    for col, val in request.form.items():
        if col.startswith("spref_") and col[6:] in prefs:
            col = col[6:]
            try:
                sprefs[col] = process_user_input(val, col, "posint")
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
    if errmsgs:
        return show_input_errors(errmsgs)
    for k, v in data.items():
        setattr(current_user, k, v)
    if current_user.save():
        flash(Markup("Your information/preferences have been updated"))
    return redirect(url_for(".info"))

@login_page.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(Markup("You are now logged out.  Have a nice day!"))
    return redirect(url_for(".info"))
