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
    is_instructor,
    is_whitelisted,
    is_admin,
    get_counts,
    class_groups,
    send_message,
    sandbox_message,
    log_event,
    )
from .utils import (
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
        s = Student(kerb, full_name) if session.get("affiliation") == "student" else Instructor(kerb, full_name)
        return s
    except:
        app.logger.warning("load_user failed on kerb=%s" % kerb)
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

KERB_RE = re.compile(r"^[a-z0-9][a-z0-9][a-z0-9]+$")

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
        return redirect(url_for('.index'))
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
            return render_template("login.html", maxlength=maxlength, sandbox_message=sandbox_message(), next=next)
        kerb = request.form.get("kerb", "").lower()
        if not KERB_RE.match(kerb):
            flash_error("Invalid user identifier <b>%s</b> (must be alpha-numeric and at least three letters long)." % kerb)
            return render_template("login.html", maxlength=maxlength, sandbox_message=sandbox_message(), next=next)
        if kerb == "staff":
            affiliation = "staff"
        elif kerb == "affiliate":
            affiliation = "affiliate"
        else:
            affiliation = "staff" if is_instructor(kerb) else "student"
        displayname = ""

    if not kerb or not affiliation:
        return render_template("500.html", message="Missing login credentials"), 500

    if affiliation == "student":
        user = Student(kerb, displayname)
    elif is_whitelisted(kerb, displayname):
        affiliation = "student"
        user = Student(kerb, displayname)
    elif affiliation == "staff":
        user = Instructor(kerb, displayname)
    else:
        app.logger.info("authenticated user %s with affiliation %s was not granted access" % (kerb, affiliation))
        return render_template("denied.html"), 404
    session["kerb"] = kerb
    session["affiliation"] = affiliation
    session["displayname"] = displayname
    user.login()
    login_user(user, remember=False)
    app.logger.info("user %s logged in to %s (affiliation=%s,is_student=%s,is_instructor=%s,full_name=%s)" %
        (kerb,"live site" if livesite() else "sandbox",affiliation,current_user.is_student,current_user.is_instructor,current_user.full_name))
    if next:
        return redirect(next)
    return redirect(url_for(".student")) if current_user.is_student else redirect(url_for(".instructor"))

@app.route("/loginas/<kerb>")
@login_required
def loginas(kerb):
    if not current_user.is_authenticated or session.get("kerb") != current_user.kerb or not is_admin(current_user.kerb):
        app.logger.critical("Unauthorized loginas/%s attempted by %s." % (kerb, current_user.kerb))
        return render_template("500.html", message="You are not authorized to perform this operation."), 500
    logout_user()
    if livesite():
        if 'people' in Configuration().options:
            from .people import get_kerb_data

            c = Configuration().options['people']
            data = get_kerb_data(kerb, c['id'], c['secret'])
            if data:
                session['affiliation'] = "student"
                session['displayname'] = data['full_name']
    displayname = session['displayname']
    user = Instructor(kerb, displayname) if is_instructor(kerb) else Student(kerb, displayname)
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
            return render_template("login.html", sandbox_message=sandbox_message(), maxlength=maxlength)
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

allowed_copts = ["hours", "start", "style", "forum", "size", "commitment", "confidence"]
allowed_gopts = ["group_name", "visibility", "hours", "preferences", "strengths", "members", "max"]


@app.route("/_acknowledge")
@login_required
def acknoledge():
    msgid = request.args.get('msgid')
    return current_user.acknowledge(msgid)

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
        return redirect(url_for(".student"))
    except BadSignature:
        flash_error("Invalid or corrupted invitation link.")
        return redirect(url_for(".student"))
    try:
        current_user.accept_invite(invite)
    except Exception as err:
        app.logger.error("Error processing invitation to %s from %s to join %s" % (current_user.kerb, invite['kerb'], invite['group_id']))
        flash_error("Unable to process invitation: %s" % err)
    return redirect(url_for(".student"))

@app.route("/poolme")
@login_required
def poolme():
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    try:
        current_user.poolme()
    except Exception as err:
        app.logger.error("Error processing poolme request for student %s" % current_user.kerb)
        flash_error("We encountered an error while attempting to put in the match pool: %s" % err)
    return redirect(url_for(".student"))

@app.route("/student")
@login_required
def student(context={}):
    if not current_user.is_authenticated or not current_user.is_student:
        return redirect(url_for("index"))
    if not livesite() and current_user.stale_login:
        return redirect(url_for("logout"))
    current_user.seen()
    current_user.flash_pending()
    return render_template(
        "student.html",
        options=template_options(),
        maxlength=maxlength,
        counts=get_counts([''] + current_user.classes, allowed_copts),
        groups={c:class_groups(c, allowed_gopts, visibility=2) for c in current_user.classes},
        ctx=session.pop("ctx",""),
    )

@app.route("/instructor")
@login_required
def instructor(context={}):
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
        ctx=session.pop("ctx",""),
    )

PREF_RE = re.compile(r"^s?pref-([a-z_]+)-(\d+)$")
PROP_RE = re.compile(r"([a-z_]+)-([1-9]\d*)$")

group_options = ['start', 'style', 'forum', 'size', 'editors', 'open']

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
        return redirect(url_for(".student"))
    if submit[0] == "cancel":
        flash_info ("Changes discarded.") 
        return redirect(url_for(".student"))
    if submit[0] == "save":
        # update the full_name supplied by Touchstone (in case this changes)
        if session.get("displayname",""):
            current_user.full_name = session["displayname"]
        if not save_changes(raw_data):
            if submit != "save":
                flash_error("The action you requested was not performed.")
            return redirect(url_for(".student"))
        submit = submit[1:]
    if not submit:
        return redirect(url_for(".student"))
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
    elif submit[0] == "match":
        try:
            cid = int(submit[1])
            flash_info(current_user.match(cid))
        except Exception as err:
            msg = "Error submitting match request: {0}{1!r}".format(type(err).__name__, err.args)
            log_event (current_user.kerb, 'match', status=-1, detail={'class_id': cid, 'msg': msg})
            if debug_mode():
                raise
            flash_error()
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
    print(raw_data)
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

@app.route("/logout")
@login_required
def logout():
    session.clear()
    logout_user()
    if not livesite():
        resp = make_response(redirect(url_for(".index")))
    else:
        resp = make_response(render_template("goodbye.html"))
    resp.set_cookie('sessionID','',expires=0)
    return resp

@app.route("/sitemap")
@login_required
def sitemap():
    """
    Listing all routes
    """
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
