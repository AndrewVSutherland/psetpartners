import re, json
import httpagentparser
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
from .config import Configuration
from .token import read_timed_token
from datetime import datetime
from .app import app, livesite, debug_mode, under_construction, send_email, routes
from .student import (
    Student,
    Instructor,
    AnonymousUser,
    student_options,
    student_preferences,
    student_class_properties,
    strength_options,
    current_classes,
    is_current_instructor,
    is_instructor,
    is_student,
    is_admin,
    get_counts,
    class_groups,
    send_message,
    log_event,
    )
from .utils import (
    format_input_errmsg,
    show_input_errors,
    flash_info,
    flash_notify,
    flash_error,
    process_user_input,
    maxlength,
    short_weekdays,
    timezones,
    list_of_strings,
    kerb_re
)
from .test import sandbox_data


def is_safe_url(target):
    if debug_mode() and target.startswith('/'):
        print("Allowing target %s in debug mode" % target)
        return True
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
    full_name = session.get('displayname')
    try:
        s = Student(kerb, full_name) if session.get("affiliation") == "student" else Instructor(kerb, full_name, affiliation=session.get("affiliation"))
        return s
    except Exception as err:
        msg = "load_user failed for {0}: {1}{2!r}".format(kerb, type(err).__name__, err.args)
        log_event (current_user.kerb, 'load', status=-1, detail={'msg': msg})
        return None

login_manager.login_view = "login"
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

@app.route("/login", methods=["GET", "POST"])
def login():
    next = request.args.get('next')
    if next and not is_safe_url(next):
        return render_template("500.html", message="Unauthorized redirect."), 500
    if current_user.is_authenticated:
        next = request.args.get('next')
        if next:
            if not is_safe_url(next):
                return render_template("500.html", message="Unauthorized redirect."), 500
            else:
                return redirect(next)
        return redirect(url_for("index"))
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
        displayname = request.environ.get("HTTP_DISPLAYNAME", "")
    else:
        if request.method != "POST" or request.form.get("submit") != "login":
            return render_template("login.html", maxlength=maxlength, sandbox=sandbox_data(), next=next)
        kerb = request.form.get("kerb", "").lower()
        if not kerb_re.match(kerb):
            flash_error("Invalid user identifier <b>%s</b>." % kerb)
            return render_template("login.html", maxlength=maxlength, sandbox=sandbox_data(), next=next)
        if kerb == "staff":
            affiliation = "staff"
        elif kerb == "affiliate":
            affiliation = "affiliate"
        else:
            affiliation = "staff" if is_current_instructor(kerb) else "student"
        displayname = ""

    if not kerb or not affiliation:
        return render_template("500.html", message="Missing login credentials"), 500

    if displayname == "(null)":
        displayname = ""

    if affiliation == "student":
        user = Student(kerb, displayname)
    elif is_student(kerb):
        affiliation = "student"
        user = Student(kerb, displayname)
    elif affiliation == "staff":
        user = Instructor(kerb, displayname, affiliation)
    else:
        app.logger.info("authenticated user %s with affiliation %s was not granted access" % (kerb, affiliation))
        return render_template("denied.html"), 404
    session["kerb"] = kerb
    session["affiliation"] = affiliation
    session["displayname"] = displayname
    user.login()
    login_user(user, remember=False)
    agent = httpagentparser.detect(request.headers.get("User-Agent"))
    source = (agent['os'].get('name',"")+" ") if 'os' in agent else ""
    source += (agent['browser'].get('name') + " " + agent['browser'].get('version')) if 'browser' in agent else "?"
    s = ',student' if current_user.is_student else ''
    i = ',instructor' if current_user.is_instructor else ''
    site = "live site" if livesite() else "sandbox"
    app.logger.info("user %s logged in to %s from %s (affiliation=%s%s%s,full_name=%s)" % (kerb, site, source, affiliation, s, i, current_user.full_name))
    if next:
        return redirect(next)
    if current_user.is_admin:
        return redirect(url_for("admin"))
    return redirect(url_for("student")) if current_user.is_student else redirect(url_for("instructor"))

@app.route("/switchrole")
@login_required
def switch_role():
    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    if not current_user.dual_role:
        return redirect(url_for("index"))
    if current_user.is_student:
        user = Instructor(current_user.kerb, current_user.full_name, affiliation='student')
        session['affiliation'] = "staff"
        login_user(user, remember=False)
    elif current_user.is_instructor:
        user = Student(current_user.kerb, current_user.full_name)
        session['affiliation'] = "student"
        login_user(user, remember=False)
    else:
        return redirect(url_for("index"))
    return redirect(url_for("student")) if current_user.is_student else redirect(url_for("instructor"))

@app.route("/loginas/<kerb>")
@login_required
def loginas(kerb):
    if not current_user.is_authenticated or session.get("kerb") != current_user.kerb or not is_admin(current_user.kerb):
        logout_user()
        return redirect(url_for("index"))
    logout_user()
    session['affiliation'] = ''
    session['displayname'] = ''
    if is_student(kerb):
        session['affiliation'] = 'student'
    elif is_instructor(kerb):
        session['affiliation'] = 'staff'
    elif 'people' in Configuration().options:
        from .people import get_kerb_data

        c = Configuration().options['people']
        data = get_kerb_data(kerb, c['id'], c['secret'])
        if data:
            session['affiliation'] = data['affiliation']
            session['displayname'] = data['full_name']
    if not session['affiliation']:
        session['affiliation'] = 'affiliate'
    user = Student(kerb, session['displayname']) if session['affiliation'] == 'student' else Instructor(kerb, session['displayname'])
    session['kerb'] = kerb
    login_user(user, remember=False)
    if current_user.is_admin:
        return redirect(url_for("admin"))
    return redirect(url_for("student")) if current_user.is_student else redirect(url_for("instructor"))

@login_required
@app.route("/admin")
@app.route("/admin/<class_number>")
@login_required
def admin(class_number=''):
    from .dbwrapper import getdb, students_groups_in_class, count_rows, class_counts, count_students_in_classes
    from .student import student_row, student_row_cols, next_match_date
    from .utils import current_term, current_year

    if not current_user.is_authenticated or session.get("kerb") != current_user.kerb or not is_admin(current_user.kerb):
        app.logger.critical("Unauthorized access to admin/%s attempted by %s." % (class_number, current_user.kerb))
        return render_template("500.html", message="You are not authorized to perform this operation."), 500
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    db = getdb()
    user = Instructor(session['kerb'], session['displayname'])
    if not class_number:
        counts = class_counts('',current_year(),current_term())
        groups = 0
        depts = {}
        for k in counts:
            d = k.split('.')[0]
            if d not in depts:
                depts[d] = { 'classes': 0, 'students': 0, 'groups': 0 }
            depts[d]['classes'] += 1
            groups += counts[k]['groups']
            depts[d]['groups'] += counts[k]['groups']
        counts[''] = { 'classes': len(counts), 'students': count_students_in_classes(), 'groups': groups }
        for d in depts:
            depts[d]['students'] = count_students_in_classes(department=d)
            counts[d] = depts[d]
        return render_template(
            "admin.html",
            options=template_options(),
            maxlength=maxlength,
            ctx=session.pop("ctx",""),
            counts=counts,
            user=user,
        )
    else:
        classes = list(db.classes.search({'class_number': class_number, 'year': current_year(), 'term': current_term()},projection=3))
        if not classes:
            return render_template("404.html", message="Class %s not found for the current term" % class_number)
        for c in classes:
            c['students'] = sorted([student_row(s) for s in students_groups_in_class(c['id'], student_row_cols)])
            c['groups'] = count_rows('groups', {'class_id': c['id']})
            c['next_match_date'], c['full_match_date'] = next_match_date(c)
            c.pop('match_dates')
            c['instructor_names'] = []
            for k in c['instructor_kerbs']:
                r = db.students.lookup(k)
                if not r:
                    r = db.instructors.lookup(k)
                c['instructor_names'].append((r['preferred_name'] if r.get('preferred_name') else r.get('full_name',"")) if r else "")
        return render_template(
            "instructor.html",
            options=template_options(),
            maxlength=maxlength,
            ctx=session.pop("ctx",""),
            classes=classes,
            user=user,
        )

@app.route("/environ")
def environ():
    return "<br>".join(["%s = %s" % (key,request.environ[key]) for key in request.environ])

@app.route("/")
def index():
    session.pop('_flashes', None)
    if current_user.is_authenticated:
        if current_user.is_student:
            return redirect(url_for("student"))
        elif current_user.is_instructor:
            if current_user.is_admin:
                return redirect(url_for("admin"))
            return redirect(url_for("instructor"))
        else:
            return render_template("500.html", message="Only students and instructors are authorized to use this site."), 500        
    else:
        if livesite():
            return redirect(url_for("login"))
        else:
            return render_template("login.html", sandbox=sandbox_data(), maxlength=maxlength)
    assert False

@app.route("/test404")
def test404():
    return render_template("404.html", message="This is a test 404 message."), 404

@app.route("/test404s")
def test404s():
    return render_template("404.html", messages=["This is a test 404 message.", "This is another test 404 message."]), 404

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

@app.route("/testmessage/<kerb>")
@login_required
def testmessage(kerb):
    if current_user.is_admin:
        send_message(current_user.kerb, "test", "This is a test message from %s to %s" % (current_user.kerb, kerb))
        return "message sent."
    else:
        return "You are not authorized to perform this operation."

@app.route("/testlog")
def testlog():
    from .utils import domain

    msg = "Test message on %s (livesite = %s, under_construction = %s, debug = %s)" % (domain(), livesite(), under_construction(), debug_mode())
    app.logger.info(msg)
    return "The following message was just logged:\n\n"+msg

@app.route("/testenviron")
@login_required
def testenviron():
    r = ["%s = %s" %(k, request.environ[k]) for k in request.environ]
    return '<br>'.join(r)

allowed_copts = ["hours", "start", "style", "forum", "size", "commitment", "confidence", "status"]
allowed_gopts = ["group_name", "visibility", "hours", "preferences", "strengths", "members", "size", "max"]

@app.route("/_acknowledge")
@login_required
def acknoledge():
    msgid = request.args.get('msgid')
    return current_user.acknowledge(msgid)

@app.route("/_confirm_conduct")
@login_required
def confirm_conduct():
    try:
        current_user.confirm_conduct()
    except ValueError as err:
        app.logger.error("Error processing code of conduct confirmation from %s" % (current_user.kerb))
        flash_error("Error processing response: %s" % err)
    return redirect(url_for("student"))

@app.route("/_toggle")
@login_required
def update_toggle():
    toggle = request.args.get('name')
    state = request.args.get('value')
    return current_user.update_toggle(toggle, state)

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

@app.route("/accept/<token>")
@login_required
def accept_invite(token):
    from itsdangerous import BadSignature
    try:
        invite = read_timed_token(token, 'invite')
    except ValueError:
        flash_error("This invitation link has expired.  Please ask the sender to create a new invitation for you.")
        return redirect(url_for("index"))
    except BadSignature:
        flash_error("Invalid or corrupted invitation link.")
        return redirect(url_for("index"))
    if not current_user.is_student:
        app.logger.error("Error processing invitation to %s from %s to join group %s: %s" % (current_user.kerb, invite['kerb'], invite['group_id'], "User is not a student"))
        flash_error("Unable to process invitation: %s" % "you are not logged in as a student")
        return redirect(url_for("index"))
    try:
        current_user.accept_invite(invite)
    except ValueError as err:
        app.logger.error("Error processing invitation to %s from %s to join group %s: %s" % (current_user.kerb, invite['kerb'], invite['group_id'], err))
        flash_error("Unable to process invitation: %s" % err)
    return redirect(url_for("student"))

@app.route("/approve/<int:request_id>")
@login_required
def approve_request(request_id):
    if not current_user.is_student:
        app.logger.error("Error processing approve response from %s to request id %s: %s" % (current_user.kerb, request_id, "User is not a student"))
        flash_error("Error processing response: %s" % "you are not logged in as a student")
        return redirect(url_for("index"))
    try:
        msg = current_user.approve_request(request_id)
        flash_notify(msg)
    except ValueError as err:
        app.logger.error("Error processing approve response from %s to request id %s" % (current_user.kerb, request_id))
        flash_error("Error processing response: %s" % err)
    return redirect(url_for("student"))

@app.route("/deny/<int:request_id>")
@login_required
def deny_request(request_id):
    if not current_user.is_student:
        app.logger.error("Error processing deny response from %s to request id %s: %s" % (current_user.kerb, request_id, "User is not a student"))
        flash_error("Error processing response: %s" % "you are not logged in as a student")
        return redirect(url_for("index"))
    try:
        flash_notify(current_user.deny_request(request_id))
    except ValueError as err:
        app.logger.error("Error processing deny response from %s to request id %s" % (current_user.kerb, request_id))
        flash_error("Error processing response: %s" % err)
    return redirect(url_for("student"))

@app.route("/uncap/<int:group_id>")
@login_required
def uncap(group_id):
    if not current_user.is_student:
        app.logger.error("Error processing uncap response from %s for group id %s: %s" % (current_user.kerb, group_id, "User is not a student"))
        flash_error("Error processing response: %s" % "you are not logged in as a student")
        return redirect(url_for("index"))
    try:
        msg = current_user.uncap_group(group_id)
        flash_notify(msg)
    except ValueError as err:
        app.logger.error("Error processing uncap response from %s for group id %s" % (current_user.kerb, group_id))
        flash_error("Error processing response: %s" % err)
    return redirect(url_for("student"))

@app.route("/poolme/<class_number>")
@login_required
def poolme(class_number):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    try:
        flash_notify(current_user.poolme(class_number))
    except ValueError as err:
        msg = "Error adding you to match pool for <b>{2}</b>: {0}{1!r}".format(type(err).__name__, err.args, class_number)
        app.logger.error("Error processing poolme request for %s for student %s: %s" % (class_number, current_user.kerb, msg))
        log_event (current_user.kerb, 'poolme', status=-1, detail={'class_number': class_number, 'msg': msg})
        flash_error("We encountered an error while attempting to put in the match pool for <b>%s</b>: %s" % (class_number, msg))
    return redirect(url_for("student", class_number=class_number))

@app.route("/removeme/<class_number>")
@login_required
def removeme(class_number):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    try:
        flash_notify(current_user.removeme(class_number))
    except ValueError as err:
        msg = "Error removing you from <b>{2}</b>: {0}{1!r}".format(type(err).__name__, err.args, class_number)
        app.logger.error("Error processing removeme request for %s for student %s: %s" % (class_number, current_user.kerb, msg))
        log_event (current_user.kerb, 'removeme', status=-1, detail={'class_number': class_number, 'msg': msg})
        flash_error("We encountered an error while attempting to remove you from <b>%s</b>: %s" % (class_number, msg))
    return redirect(url_for("student"))

@app.route("/imgood/<class_number>")
@login_required
def imgood(class_number):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    log_event (current_user.kerb, 'imgood', detail={'class_number': class_number})
    flash_notify("Thanks!")
    return redirect(url_for("student", class_number=class_number))

@app.route("/regroupme/<class_number>")
@login_required
def regroupme(class_number):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    log_event (current_user.kerb, 'regroupme', detail={'class_number': class_number})
    return redirect(url_for("student", class_number=class_number, action="leave"))

@app.route("/student")
@app.route("/student/<class_number>")
@app.route("/student/<class_number>/<action>")
@login_required
def student(class_number='', action=''):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    if not current_user.conduct:
        return render_template("conduct.html", title="conduct", confirm=True)
    current_user.seen()
    current_user.flash_pending()
    if class_number:
        current_user.toggles['ct'] = class_number
        current_user.toggles['ht'] = 'partner-header'
        current_user._save_toggles
    return render_template(
        "student.html",
        options=template_options(),
        maxlength=maxlength,
        counts=get_counts([''] + current_user.classes, allowed_copts),
        groups={c:class_groups(c, allowed_gopts, visibility=2) for c in current_user.classes},
        action=action,
        ctx=session.pop("ctx",""),
    )

@app.route("/instructor")
@login_required
def instructor():
    if not current_user.is_authenticated or not current_user.is_instructor:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    current_user.seen()
    current_user.flash_pending()
    return render_template(
        "instructor.html",
        options=template_options(),
        maxlength=maxlength,
        classes=[current_user.class_data[c] for c in current_user.classes],
        ctx=session.pop("ctx",""),
    )

@app.route("/user/<kerb>")
def test_user(kerb):
    if livesite():
        return render_template("404.html", message="Page not found."), 404
    logout_user()
    session['affiliation'] = ''
    session['displayname'] = ''
    if is_instructor(kerb):
        session['affiliation'] = 'staff'
    else:
        session['affiliation'] = 'student'
    user = Student(kerb, session['displayname']) if session['affiliation'] == 'student' else Instructor(kerb, session['displayname'])
    session['kerb'] = kerb
    login_user(user, remember=False)
    if current_user.is_admin:
        return redirect(url_for("admin"))
    return redirect(url_for("student")) if current_user.is_student else redirect(url_for("instructor"))


@app.route("/activate/<class_id>")
@login_required
def activate(class_id):
    if not current_user.is_authenticated or not current_user.is_instructor:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    current_user.acknowledge()
    try:
        flash_notify(current_user.activate(class_id))
    except Exception as err:
        msg = "Error activing class {0}{1!r}".format(type(err).__name__, err.args)
        log_event (current_user.kerb, 'activate', status=-1, detail={'class_id': class_id, 'msg': msg})
        if debug_mode():
            raise
        flash_error(msg)
    return redirect(url_for("instructor"))

@app.route("/save/class", methods=["POST"])
@login_required
def save_class():
    raw_data = request.form
    details = httpagentparser.detect(request.headers.get("User-Agent"))
    details['operation'] = 'save_class'
    details['resolution'] = "%sx%s"% (raw_data.get("screen-width","?"), raw_data.get("screen-height","?"))
    log_event (current_user.kerb, 'submit', details)
    data = { col: val.strip() for col,val in raw_data.items() }
    try:
        class_id = int(data.pop("class_id"))
    except Exception as err:
        msg = "Error getting class_id: {0}{1!r}".format(type(err).__name__, err.args)
        log_event (current_user.kerb, 'update', status=-1, detail={'data': data, 'msg': msg})
        if debug_mode():
            raise
        flash_error(msg)
        return redirect(url_for("instructor"))

    current_user.acknowledge()
    try:
        flash_notify(current_user.update_class(class_id, data))
    except Exception as err:
        msg = "Error updating class: {0}{1!r}".format(type(err).__name__, err.args)
        log_event (current_user.kerb, 'update', status=-1, detail={'class_id': class_id, 'data': data, 'msg': msg})
        if debug_mode():
            raise
        flash_error(msg)
    return redirect(url_for("instructor"))


PREF_RE = re.compile(r"^s?pref-([a-z_]+)-(\d+)$")
PROP_RE = re.compile(r"([a-z_]+)-([1-9]\d*)$")

group_options = ['start', 'style', 'forum', 'size', 'editors', 'membership', 'description', 'link']

@app.route("/save/student", methods=["POST"])
@login_required
def save_student():
    raw_data = request.form
    session["ctx"] = { x[4:] : raw_data[x] for x in raw_data if x.startswith("ctx-") } # return ctx-XXX values to
    if not 'submit' in session["ctx"]:
        flash_error("Invalid operation, no submit value (please report this as a bug).")
    submit = [x for x in session["ctx"]["submit"].split(' ') if x];
    if not submit:
        flash_error("Unrecognized submit value, no changes made (please report this as a bug).")
        return redirect(url_for("student"))
    if submit[0] == "cancel":
        flash_info ("Changes discarded.") 
        return redirect(url_for("student"))
    details = httpagentparser.detect(request.headers.get("User-Agent"))
    details['operation'] = submit[0]
    details['resolution'] = "%sx%s"% (raw_data.get("screen-width","?"), raw_data.get("screen-height","?"))
    log_event (current_user.kerb, 'submit', details)
    if submit[0] == "save":
        # update the full_name supplied by Touchstone (in case this changes)
        if session.get("displayname",""):
            current_user.full_name = session["displayname"]
        # treat the decision to save changes as acknowledgement of all unread messages
        current_user.acknowledge()
        if not save_changes(raw_data):
            if submit != "save":
                flash_error("The action you requested was not performed.")
            return redirect(url_for("student"))
        submit = submit[1:]
    if not submit:
        return redirect(url_for("student"))
    if submit[0] == "join":
        try:
            gid = int(submit[1])
            flash_info(current_user.join(gid))
        except Exception as err:
            msg = "Error joining group: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'join', status=-1, detail={'group_id': gid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "leave":
        try:
            gid = int(submit[1])
            flash_info(current_user.leave(gid))
        except Exception as err:
            msg = "Error leaving group: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'leave', status=-1, detail={'group_id': gid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "pool":
        try:
            cid = int(submit[1])
            flash_info(current_user.pool(cid))
        except Exception as err:
            msg = "Error adding you to the match pool: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'pool', status=-1, detail={'class_id': cid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "unpool":
        try:
            cid = int(submit[1])
            flash_info(current_user.unpool(cid))
        except Exception as err:
            msg = "Error removing you from the match pool: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'unpool', status=-1, detail={'class_id': cid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "matchasap":
        try:
            gid = int(submit[1])
            flash_info(current_user.matchasap(gid))
        except Exception as err:
            msg = "Error submitting match me asap request: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'matchasap', status=-1, detail={'group_id': gid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "matchnow":
        try:
            gid = int(submit[1])
            flash_info(current_user.matchnow(gid))
        except Exception as err:
            msg = "Error submitting match me now request: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'matchnow', status=-1, detail={'group_id': gid, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "createprivate":
        try:
            cid = int(submit[1])
            flash_info(current_user.create_group (cid, {k: raw_data.get(k,'').strip() for k in group_options}, public=False))
        except Exception as err:
            msg = "Error creating private group: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'create', status=-1, detail={'class_id': cid, 'public': False, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "createpublic":
        try:
            cid = int(submit[1])
            flash_info(current_user.create_group (cid, {k: raw_data.get(k,'').strip() for k in group_options}, public=True))
        except Exception as err:
            msg = "Error creating public group: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'create', status=-1, detail={'class_id': cid, 'public': True, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    elif submit[0] == "editgroup":
        try:
            gid = int(submit[1])
            flash_info(current_user.edit_group (gid, {k: raw_data.get(k,'').strip() for k in group_options}))
        except Exception as err:
            msg = "Error editing group: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'edit', status=-1, detail={'group_id': gid, 'public': True, 'msg': msg})
            if debug_mode():
                raise
            flash_error(msg)
    else:
        flash_error("Unrecognized submit command: " + submit[0]);
    return redirect(url_for("student"))

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
                typ = "text" if col[0] == 'p' else "posint"
                try:
                    v[p] = process_user_input(val, p, typ)
                    if col[0] == 'p':
                        if v[p] and not [True for r in student_preferences[p] if r[0] == v[p]]:
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
                try:
                    v[p] = val.strip()
                    if v[p] and not [True for r in student_class_properties[p] if r[0] == v[p]]:
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
    # client should not be sending any unnecessary strengths, but remove them if present
    for i in range(num_classes+1):
        for k in list(sprefs[i]):
            if not k in prefs[i]:
                sprefs[i].pop(k)
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

@app.route("/survey")
@login_required
def survey():
    import datetime
    from .dbwrapper import getdb

    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    db = getdb()
    today = datetime.date.today()
    survey = db.surveys.lucky({'start':{'$lte':today},'end':{'$gte':today}},projection=3)
    if not survey:
        return render_template("thankyou.html", message="No surveys are currently active, but thanks for checking!")
    survey['response'] = db.survey_responses.lucky({'survey_id': survey['id'], 'kerb':current_user.kerb}, projection="response")
    log_event(current_user.kerb,"survey")
    return render_template(
        "survey.html",
        options=template_options(),
        maxlength=maxlength,
        survey=survey
    )

@app.route("/save/survey", methods=["POST"])
@login_required
def save_survey():
    import datetime
    from .dbwrapper import getdb

    r = {}
    r['response'] = request.form.to_dict()
    r['survey_id'] = r['response'].pop('survey_id')
    r['kerb'] = current_user.kerb
    r['timestamp'] = datetime.datetime.now()
    db = getdb()
    db.survey_responses.upsert({'survey_id': r['survey_id'],'kerb': r['kerb']}, r)
    log_event(current_user.kerb,"surveyed")
    return render_template("thankyou.html", message='Your responses have been recorded.  You can update them by revisiting the <a href="%s">survey link</a>.' % url_for("survey"))

@app.route("/logout")
@login_required
def logout():
    session.clear()
    logout_user()
    if not livesite():
        resp = make_response(redirect(url_for("index")))
    else:
        resp = make_response(render_template("thankyou.html",message="You have been logged out."))
    resp.set_cookie('sessionID','',expires=0)
    return resp

@app.route("/sitemap")
@login_required
def sitemap():
    """
    Listing all routes
    """
    if not current_user.is_authenticated or session.get("kerb") != current_user.kerb or not is_admin(current_user.kerb):
        app.logger.critical("Unauthorized sitemap attempted by %s." % current_user.kerb)
        return render_template("500.html", message="You are not authorized to perform this operation."), 500
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><a href="{0}">{1}</a></li>'.format(url, endpoint)
                if url is not None
                else "<li>{0}</li>".format(endpoint)
                for url, endpoint in routes()
            ]
        )
        + "</ul>"
    )
