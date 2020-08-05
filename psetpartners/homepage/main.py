import re
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
from psetpartners.student import (
    Student,
    AnonymousStudent,
    preference_types,
    current_classes,
    )
from psetpartners.utils import (
    format_input_errmsg,
    show_input_errors,
    flash_info,
    flash_error,
    process_user_input,
    maxlength,
    short_weekdays,
    term_options,
    list_of_strings,
)

login_manager = LoginManager()

@login_manager.user_loader
def load_user(kerb):
    return Student(kerb)

login_manager.login_view = "user.info"

login_manager.anonymous_user = AnonymousStudent

# Don't include options in static/options.js used only in javascript
def info_options():
    return {'term' : term_options,
            'weekday' : short_weekdays,
            'classes' : current_classes(),
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
    return redirect(request.form.get("next") or url_for(".info"))

@app.route("/info")
def info():
    title = "" if current_user.is_authenticated else "login"
    print("user.classes = %s" % current_user.classes);
    print("user.class_data = %s" % current_user.class_data);
    return render_template(
        "user-info.html",
        next=request.args.get("next", ""),
        title=title,
        options=info_options(),
        maxlength=maxlength,
    )

PREF_RE = re.compile(r"^s?pref-([a-z_]*)-(\d+)$")

@app.route("/set_info", methods=["POST"])
@login_required
def set_info():
    raw_data = request.form
    if raw_data.get("submit") == "cancel":
        return redirect(url_for(".info"), 301)
    errmsgs = []
    print("raw_data: %s" % dict(raw_data))
    prefs = [ {} for i in range(len(current_user.classes)+1) ]
    sprefs = [ {} for i in range(len(current_user.classes)+1) ]
    data = {"preferences": prefs[0], "strengths": sprefs[0]}
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
        elif PREF_RE.match(col) and val.strip():
            t = col.split('-')
            if t[1] in preference_types:
                n = int(t[2])
                p = prefs[n] if col[0] == 'p' else sprefs[n]
                try:
                    typ = preference_types[t[1]] if col[0] == 'p' else "posint"
                    p[t[1]] = process_user_input(val, t[1], typ)
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
    for i in range(len(current_user.classes)):
        current_user.class_data[current_user.classes[i]]["preferences"] = prefs[i+1]
        current_user.class_data[current_user.classes[i]]["strengths"] = sprefs[i+1]
    data["classes"] = list_of_strings(raw_data.get("classes",[]))
    print("data: %s" % data)
    for k, v in data.items():
        setattr(current_user, k, v)
    current_user.save()
    try:
       #current_user.save()
       flash_info ("Changes saved.") 
    except Exception as err:
        flash_error("Error saving changes: %s" % err)

    return redirect(url_for(".info"), 301)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(Markup("You are now logged out.  Have a nice day!"))
    return redirect(url_for(".info"), 301)
