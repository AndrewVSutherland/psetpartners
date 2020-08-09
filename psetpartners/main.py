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
    student_options,
    student_preferences,
    strength_options,
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
def template_options():
    return {'term' : term_options,
            'strength' : strength_options,
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
    return redirect(request.form.get("next") or url_for(".student"))

@app.route("/")
def index():
    return student()

@app.route("/student")
def student():
    title = "" if current_user.is_authenticated else "login"
    return render_template(
        "student.html",
        next=request.args.get("next", ""),
        title=title,
        options=template_options(),
        maxlength=maxlength,
    )

PREF_RE = re.compile(r"^s?pref-([a-z_]*)-(\d+)$")

@app.route("/save/student", methods=["POST"])
@login_required
def save_student():
    raw_data = request.form
    if raw_data.get("submit") == "cancel":
        return redirect(url_for(".student"), 301)
    errmsgs = []
    print("raw_data: %s" % dict(raw_data))
    prefs = [ {} for i in range(len(current_user.classes)+1) ]
    sprefs = [ {} for i in range(len(current_user.classes)+1) ]
    data = {"preferences": prefs[0], "strengths": sprefs[0]}
    data["hours"] = [[False for j in range(24)] for i in range(7)]
    for i in range(7):
        for j in range(24):
            if raw_data.get("cb-hours-%d-%d"%(i,j),False):
                data["hours"][i][j] = True

    # TODO: validate data values, not just type
    for col, val in raw_data.items():
        if col in db.students.col_type:
            try:
                typ = db.students.col_type[col]
                data[col] = process_user_input(val, col, typ)
                if col in student_options and data[col] and not [True for r in student_options[col] if r[0] == data[col]]:
                    raise ValueError("Invalid option")
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        elif PREF_RE.match(col) and val.strip():
            t = col.split('-')
            if t[1] in student_preferences:
                p = t[1]
                n = int(t[2])
                v = prefs[n] if col[0] == 'p' else sprefs[n]
                try:
                    typ = student_preferences[p]["type"] if col[0] == 'p' else "posint"
                    v[p] = process_user_input(val, p, typ)
                    if col[0] == 'p':
                        if v[p] and not [True for r in student_preferences[p]["options"] if r[0] == v[p]]:
                            print("v[%s]=%s, opts=%s"%(p,v[p],[r[0] for r in student_preferences[p]["options"]]))
                            raise ValueError("Invalid option")
                    else:
                        if v[p] > len(strength_options):
                            raise ValueError("Invalid strength")
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

    return redirect(url_for(".student"), 301)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(Markup("You are now logged out.  Have a nice day!"))
    return redirect(url_for(".student"), 301)
