import re, json
from urllib.parse import urlparse, urljoin
from flask import (
    make_response,
    render_template,
    url_for,
    redirect,
    request,
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
from .app import app, livesite, debug_mode, under_construction, send_email
from .student import (
    Student,
    Instructor,
    AnonymousUser,
    student_options,
    student_preferences,
    student_class_properties,
    strength_options,
    current_classes,
    is_instructor,
    is_admin,
    get_counts,
    class_groups,
    )
from .utils import (
    format_input_errmsg,
    show_input_errors,
    flash_info,
    flash_announce ,
    flash_instruct,
    flash_error,
    process_user_input,
    maxlength,
    short_weekdays,
    timezones,
    list_of_strings,
)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme == "https" and ref_url.netloc == test_url.netloc

login_manager = LoginManager()

@login_manager.user_loader
def load_user(kerb):
    if not kerb:
        return AnonymousUser()
    if session.get("kerb") != kerb or not session.get("affiliation") in ["student","staff","affiliate"]:
        return None
    if session.get("affiliation") == "affiliate":
        return AnonymousUser()
    try:
        s = Student(kerb) if session.get("affiliation") == "student" else Instructor(kerb)
        return s
    except:
        app.logger.warning("load_user failed on kerb=%s" % kerb)
        return None

login_manager.login_view = "student"
login_manager.session_protection = "strong" # Important, this prevents session cookies from being stolen by a rogue
login_manager.anonymous_user = AnonymousUser

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

KERB_RE = re.compile(r"^[a-z0-9][a-z0-9][a-z0-9]+$")

@app.route("/login", methods=["GET", "POST"])
def login():
    if livesite():
        if request.method != "GET":
            return render_template("500.html", message="Invalid login method"), 500
        eppn = request.environ.get("HTTP_EPPN", "")
        affiliation = request.environ.get("HTTP_AFFILIATION", "")
        if not eppn.endswith("@mit.edu") or not affiliation.endswith("@mit.edu"):
            if eppn or affiliation:
                app.logger.error("Failed login with eppn=%s and affiliation=%s" % (eppn, affiliation))
            return render_template("500.html", message="Touchstone authentication invalid."), 500
        kerb = eppn.split("@")[0]
        affiliation = affiliation.split("@")[0]
    else:
        if request.method != "POST" or request.form.get("submit") != "login":
            return render_template("500.html", message="Invalid login method"), 500
        kerb = request.form.get("kerb", "").lower()
        if not KERB_RE.match(kerb):
            flash_error("Invalid user identifier <b>%s</b> (must be alpha-numeric and at least three letters long)." % kerb)
            return render_template("login.html", maxlength=maxlength)
        affiliation = "staff" if is_instructor(kerb) else "student"

    if not kerb or not affiliation:
        return render_template("500.html", message="Missing login credentials"), 500

    # We don't currently use next, but we might later, so let's validate now
    next = request.args.get('next')
    if next and not is_safe_url(next):
        return render_template("500.html", message="Unauthorized redirect."), 500

    if affiliation == "student":
        user = Student(kerb)
    elif affiliation == "staff":
        user = Instructor(kerb)
    else:
        return render_template("500.html", message="Only students and instructors are authorized to use this site."), 500
    session["kerb"] = kerb
    session["affiliation"] = affiliation
    login_user(user, remember=False)
    app.logger.info("user %s logged in to %s (affiliation=%s,is_student=%s,is_instructor=%s)" %
        (kerb,"live site" if livesite() else "sandbox",affiliation,current_user.is_student,current_user.is_instructor))
    return redirect(url_for(".student")) if current_user.is_student else redirect(url_for(".instructor"))

@app.route("/loginas/<kerb>")
@login_required
def loginas(kerb):
    if not current_user.is_authenticated or session.get("kerb") != current_user.kerb or not is_admin(current_user.kerb):
        app.logger.critical("Unauthorized loginas/%s attempted by %s." % (kerb, current_user.kerb))
        return render_template("500.html", message="You are not authorized to perform this operation."), 500
    logout_user()
    user = Instructor(kerb) if is_instructor(kerb) else Student(kerb)
    session["kerb"] = kerb
    session["affiliation"] = "student" if user.is_student else "staff"
    login_user(user, remember=False)
    return redirect(url_for(".student")) if current_user.is_student else redirect(url_for(".instructor"))

@app.route("/environ")
def environ():
    return "<br>".join(["%s = %s" % (key,request.environ[key]) for key in request.environ])

@app.route("/")
def index():
    session.pop('_flashes', None)
    if current_user.is_authenticated:
        if current_user.is_student:
            return redirect(url_for(".student"))
        elif current_user.is_instructor:
            return redirect(url_for(".instructor"))
        else:
            return render_template("500.html", message="Only students and instructors are authorized to use this site."), 500        
    else:
        if livesite():
            return redirect(url_for(".login"))
        else:
            return render_template("login.html", maxlength=maxlength)
    assert False

@app.route("/test404")
def test404():
    return render_template("404.html", message="Thie is a test 404 message."), 404

@app.route("/test404s")
def test404s():
    return render_template("404.html", messages=["Thie is a test 404 message.", "This is another test 404 message."]), 404

@app.route("/test500")
def test500():
    app.logger.error("test500")
    return render_template("500.html", message="This is a test 500 message",), 500

@app.route("/test503")
def test503():
    app.logger.error("test503")
    return render_template("503.html", message="Thie is a test 503 message"), 503

@app.route("/testemail")
@login_required
def testemal():
    from .config import Configuration
    if len(Configuration().options['email']['password']) < 16:
        return "No can do, you are either running in a test installation or using a weak password."
    if current_user.is_admin:
        send_email(current_user.kerb + "@mit.edu", "Test email from psetpartners", "This is a test message from psetparenters.")
        return "email sent."
    else:
        return "You are not authorized to perform this operation."

@app.route("/testlog")
def testlog():
    from .utils import domain

    msg = "Test message on %s (livesite = %s, under_construction = %s, debug = %s)" % (domain(), livesite(), under_construction(), debug_mode())
    app.logger.info(msg)
    return "The following message was just logged:\n\n"+msg

allowed_copts = ["hours", "start", "together", "forum", "size", "commitment", "confidence"]
allowed_gopts = ["group_name", "visibility", "hours", "preferences", "strengths", "members", "max"]

@app.route("/_counts")
@login_required
def counts():
    classes = request.args.get('classes',"").split(",")
    copts = [x for x in request.args.get('opts',"").split(",") if x and x in allowed_copts]
    return json.dumps({'counts': get_counts(classes, copts if copts else allowed_copts)})

@app.route("/_groups")
@login_required
def groups():
    classes = request.args.get('classes',"").split(",")
    gopts = [x for x in request.args.get('opts',"").split(",") if x and x in allowed_gopts]
    return json.dumps({'groups': {c: class_groups(c, gopts if gopts else allowed_gopts) for c in classes}})

@app.route("/_counts_groups")
@login_required
def counts_groups():
    classes = request.args.get('classes',"").split(",")
    copts = [x for x in request.args.get('opts',"").split(",") if x and x in allowed_copts]
    gopts = [x for x in request.args.get('opts',"").split(",") if x and x in allowed_gopts]
    return json.dumps({'counts': get_counts(classes, copts if copts else allowed_copts),
                       'groups': {c: class_groups(c, gopts if gopts else allowed_gopts) for c in classes}})


@app.route("/student")
def student(context={}):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if current_user.new:
        flash_announce("""
Welcome to pset partners!
To get started, first enter your preferred name and any other personal details you care to share.
Then select your location and timezone, the math classes you are taking this term, and indicate your hours of availability.
You can then set preferences if you wish (none are required), both generally and for each class individually.
Then click the "Partners" tab and click through your classes to see what your options are.
            """)
        flash_instruct('Text or boxes drawn in MIT colors are clickable.  Try clicking the "Partners" tab SE of the time grid!')
    return render_template(
        "student.html",
        options=template_options(),
        maxlength=maxlength,
        counts=get_counts([''] + current_user.classes, allowed_copts),
        groups={c:class_groups(c, allowed_gopts, visibility=2) for c in current_user.classes},
        ctx=session.pop("ctx",""),
    )

@app.route("/instructor")
def instructor(context={}):
    if not current_user.is_authenticated or not current_user.is_instructor:
        return redirect(url_for("index"))
    return render_template(
        "instructor.html",
        options=template_options(),
        maxlength=maxlength,
        ctx=session.pop("ctx",""),
    )

PREF_RE = re.compile(r"^s?pref-([a-z_]+)-(\d+)$")
PROP_RE = re.compile(r"([a-z_]+)-([1-9]\d*)$")

@app.route("/save/student", methods=["POST"])
@login_required
def save_student():
    raw_data = request.form
    session["ctx"] = { x[4:] : raw_data[x] for x in raw_data if x.startswith("ctx-") } # return ctx-XXX values to
    submit = [x for x in raw_data.get("submit").split(' ') if x];
    if not submit:
        flash_error("Unrecognized submit command, no changes made.")
        return redirect(url_for(".studnet"))
    if submit[0] == "cancel":
        flash_info ("Changes discarded.") 
        return redirect(url_for(".student"))
    if submit[0] == "save":
        if not save_changes(raw_data):
            if submit != "save":
                flash_error("The action you requested was not performed.")
            return redirect(url_for(".student"))
        submit = submit[1:]
    if not submit:
        return redirect(url_for(".student"))    
    if submit[0] == "join":
        try:
            flash_info(current_user.join(int(submit[1])))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error joining group: {0}{1!r}".format(type(err).__name__, err.args))
    elif submit[0] == "leave":
        try:
            flash_info(current_user.leave(int(submit[1])))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error leaving group: {0}{1!r}".format(type(err).__name__, err.args))
    elif submit[0] == "pool":
        try:
            flash_info(current_user.pool(int(submit[1])))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error adding you to the match pool for {0}: {1}{2!r}".format(submit[1], type(err).__name__, err.args))
    elif submit[0] == "match":
        try:
            flash_info(current_user.match(int(submit[1])))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error submitting match request for {0}:  {1}{2!r}".format(submit[1], type(err).__name__, err.args))
    elif submit[0] == "createprivate":
        try:
            flash_info(current_user.create_group (int(submit[1]), public=False))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error submitting match request for {0}:  {1}{2!r}".format(submit[1], type(err).__name__, err.args))
    elif submit[0] == "createpublic":
        try:
            flash_info(current_user.create_group (int(submit[1]), public=True))
        except Exception as err:
            if debug_mode():
                raise
            flash_error("Error submitting match request for {0}:  {1}{2!r}".format(submit[1], type(err).__name__, err.args))
    else:
        flash_error("Unrecognized submit command.")
    return redirect(url_for(".student"))

def save_changes(raw_data):
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
    data["hours"] = [False for i in range(168)]
    for i in range(7):
        for j in range(24):
            if raw_data.get("hours-%d-%d"%(i,j),False):
                data["hours"][24*i+j] = True

    # TODO: validate data values, not just type (data from form should be fine)
    for col, val in raw_data.items():
        if col.startswith('hours-'):
            continue;
        if col in current_user.col_type:
            try:
                typ = current_user.col_type[col]
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
                if i < 0 or i >= 7 or j < 0 or j >= 24:
                    raise ValueError("Day or hour out of range")
                data["hours"][24*i+j] = True
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))
        # There should never be any errors coming from the form but if there are, return the first one
        if errmsgs:
            for msg in errmsgs:
                flash_error(msg)
            return False;
    data["preferences"] = prefs[0]
    data["strengths"] = sprefs[0]
    for k, v in data.items():
        setattr(current_user, k, v)
    current_user.class_data = { data["classes"][i]: { "properties": props[i+1], "preferences": prefs[i+1], "strengths": sprefs[i+1]} for i in range(num_classes) }
    try:
       flash_info(current_user.save())
    except Exception as err:
        flash_error("Error saving changes: %s" % err)
        return False
    return True

@app.route("/logout")
@login_required
def logout():
    logout_user()
    if not livesite():
        resp = make_response(redirect(url_for(".index")))
    else:
        resp = make_response(render_template("goodbye.html"))
    resp.set_cookie('sessionID','',expires=0)
    return resp
