from flask import (
    render_template,
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
from psetpartners.app import app
from psetpartners.student import Student, AnonymousStudent, preference_types
from psetpartners.group import class_options
from psetpartners.utils import (
    timezones,
    format_input_errmsg,
    show_input_errors,
    process_user_input,
    maxlength,
    short_weekdays,
    gender_options,
    year_options,
    location_options,
    gender_affinity_options,
    year_affinity_options,
    group_size_options,
    strength_options,
    forum_options,
    start_options,
    together_options,
)

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
            'group_size': group_size_options,
            'strength': strength_options,
            'forum': forum_options,
            'start': start_options,
            'together': together_options,
            'location': location_options,
            'timezones' : timezones,
            'weekday' : short_weekdays,
            'classes' : class_options(),
            }

# globally define user properties and username
@app.context_processor
def ctx_proc_userdata():
    userdata = {
        "user": current_user,
        "usertime": datetime.now(tz=current_user.tz),
    }
    return userdata

@app.route("/login", methods=["POST"])
def login():
    identifier = request.form["identifier"]
    user = Student(kerb=identifier)
    # For now, no password check
    # The following sets current_user = user
    login_user(user, remember=True)
    if user.preferred_name:
        flash(Markup("Hello %s, your login was successful!" % user.preferred_name))
    else:
        flash(Markup("Hello, your login was successful!"))
    return redirect(request.form.get("next") or url_for(".info"))

@app.route("/info")
def info():
    if current_user.is_authenticated:
        title = "pset partners"
    else:
        title = "Login"
    return render_template(
        "user-info.html",
        next=request.args.get("next", ""),
        title=title,
        options=info_options(),
        maxlength=maxlength,
    )

@app.route("/test", methods=['GET', 'POST'])
def test():
    return jsonify({'reply':'hi there'})

@app.route("/set_info", methods=["POST"])
@login_required
def set_info():
    errmsgs = []
    prefs = {}
    sprefs = {}
    data = {"preferences": prefs, "strengths": sprefs}
    raw_data = request.form
    data["hours"] = [[False for j in range(24)] for i in range(7)]
    for i in range(7):
        for j in range(24):
            if raw_data.get("check-hours-%d-%d"%(i,j),False):
                data["hours"][i][j] = True

    # Need to do data validation
    for col, val in raw_data.items():
        if col in db.students.col_type:
            try:
                typ = db.students.col_type[col]
                data[col] = process_user_input(val, col, typ)
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        elif col.startswith("pref_") and val.strip():
            col = col[5:]
            try:
                typ = preference_types[col]
                prefs[col] = process_user_input(val, col, typ)
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        elif col.startswith("spref_"):
            col = col[6:]
            try:
                sprefs[col] = process_user_input(val, col, "posint")
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        elif col.startswith("hours-"):
            try:
                i,j = (int(x) for x in col[6:].split("-"))
                data["hours"][i][j] = True
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
    # There should never be any errors coming from the form
    if errmsgs:
        return show_input_errors(errmsgs)
    for k, v in data.items():
        setattr(current_user, k, v)
    if current_user.save():
        flash(Markup("Your information/preferences have been updated"))
    return redirect(url_for(".info"))

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(Markup("You are now logged out.  Have a nice day!"))
    return redirect(url_for(".info"))
