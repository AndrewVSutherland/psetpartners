import re
from flask import (
    make_response,
    render_template,
    url_for,
    redirect,
    request,
    flash,
    session,
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
    student_class_properties,
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
    timezones,
    list_of_strings,
)

login_manager = LoginManager()

@login_manager.user_loader
def load_user(kerb):
    try:
        return Student(kerb=kerb)
    except:
        app.logger.warning("load_user failed on kerb=%s" % kerb)
        return None

login_manager.login_view = "student"

login_manager.anonymous_user = AnonymousStudent

# Don't include options in static/options.js used only in javascript
def template_options():
    return { 'weekday' : short_weekdays, 'strength': strength_options, 'classes' : current_classes(), 'timezones': timezones }

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
    raw_data = request.form
    if raw_data.get("submit") == "register":
        new = True
    elif raw_data.get("submit") == "login":
        new = False
    else:
        return render_template("404.html", title="page not found", messages=["Unknown submit data in post"]), 404
    kerb = raw_data["kerb"]
    try:
        user = Student(kerb=kerb,new=new)
    except Exception:
        resp = make_response(redirect(url_for(".student"), 301))
        resp.set_cookie('sessionID', '', expires=0)
        if new:
            flash_error("An unexpected error occurred, unable to create student record for kerberos id <b>%s</b>." % kerb)
            return resp
        else:
            flash_error("No existing record found for kerberos id <b>%s</b>.  Please register if you are a new user." % kerb)
            return resp

    # For now, no password check
    # The following sets current_user = user
    login_user(user, remember=True)
    app.logger.info("user %s logged in" % kerb)
    return redirect(url_for(".student"), 301)

@app.route("/")
def index():
    session.pop('_flashes', None)
    return redirect(url_for(".student"), 301)

@app.route("/test404")
def test404():
    return render_template("404.html",title="test 404 page",message="Thie is a test 404 message.")

@app.route("/test404s")
def test404s():
    return render_template("404.html",title="test 404 page",messages=["Thie is a test 404 message.", "This is another test 404 message."])

@app.route("/test500")
def test500():
    app.logger.error("test500")
    return render_template("500.html",title="test 500 page",)

@app.route("/test503")
def test503():
    app.logger.error("test503")
    return render_template("503.html",title="test 503 page",message="Thie is a test message")

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

PREF_RE = re.compile(r"^s?pref-([a-z_]+)-(\d+)$")
PROP_RE = re.compile(r"([a-z_]+)-([1-9]\d*)$")

@app.route("/save/student", methods=["POST"])
@login_required
def save_student():
    raw_data = request.form
    if raw_data.get("submit") == "cancel":
        return redirect(url_for(".student"), 301)
    errmsgs = []
    data = {}
    try:
        data["classes"] = [x for x in list_of_strings(raw_data.get("classes","[]")) if x]
    except Exception as err:
        return show_input_errors([format_input_errmsg(err, raw_data.get("classes","[]"), "classes")])
    num_classes = len(data["classes"])
    prefs = [ {} for i in range(num_classes+1) ]
    sprefs = [ {} for i in range(num_classes+1) ]
    props = [ {} for i in range(num_classes+1) ]
    data["hours"] = [[False for j in range(24)] for i in range(7)]
    for i in range(7):
        for j in range(24):
            if raw_data.get("cb-hours-%d-%d"%(i,j),False):
                data["hours"][i][j] = True

    # TODO: validate data values, not just type (data from form should be fine)
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
            p, n = t[1], int(t[2])
            if p in student_preferences and n <= num_classes:
                v = prefs[n] if col[0] == 'p' else sprefs[n]
                typ = student_preferences[p]["type"] if col[0] == 'p' else "posint"
                try:
                    v[p] = process_user_input(val, p, typ)
                    if col[0] == 'p':
                        if v[p] and not [True for r in student_preferences[p]["options"] if r[0] == v[p]]:
                            raise ValueError("Invalid option")
                    else:
                        if v[p] > len(strength_options):
                            raise ValueError("Invalid strength")
                except Exception as err:
                    errmsgs.append(format_input_errmsg(err, val, col))
        elif PROP_RE.match(col) and val.strip():
            t = col.split('-')
            p, n = t[0], int(t[1])
            if p in student_class_properties and n > 0 and n <= num_classes:
                v = props[n]
                typ = student_class_properties[p]["type"]
                try:
                    v[p] = process_user_input(val, p, "posint")
                    if v[p] and not [True for r in student_class_properties[p]["options"] if r[0] == v[p]]:
                        raise ValueError("Invalid option")
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
    data["preferences"] = prefs[0]
    data["strengths"] = sprefs[0]
    for k, v in data.items():
        setattr(current_user, k, v)
    current_user.class_data = { data["classes"][i]: { "properties": props[i+1], "preferences": prefs[i+1], "strengths": sprefs[i+1]} for i in range(num_classes) }
    current_user.save()
    try:
       #current_user.save()
       flash_info ("Changes saved.") 
    except Exception as err:
        flash_error("Error saving changes: %s" % err)
    return redirect(url_for(".student"), 301)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for(".student"), 301)
