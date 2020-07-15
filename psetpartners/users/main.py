
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
from .pwdmanager import Student
from psetpartners.utils import (
    timezones,
    format_input_errmsg,
    show_input_errors,
    process_user_input,
)

login_page = Blueprint("user", __name__, template_folder="template")
login_manager = LoginManager()

@login_manager.user_loader
def load_user(kerb):
    return Student(kerb)

login_manager.login_view = "user.info"

@login_page.route("/login", methods=["POST"])
def login():
    identifier = request.form["identifier"]
    user = Student(identifier=identifier)
    if user._authenticated:
        # For now, no password check; just check that they're in the database.
        # The following sets current_user = user
        login_user(user, remember=True)
        if user.preferred_name:
            flash(Markup("Hello %s, your login was successful!" % user.preferred_name))
        else:
            flash(Markup("Hello, your login was successful!"))
        return redirect(request.form.get("next") or url_for(".info"))
    else:
        flash(Markup("Unknown user.  Please register!"))

@login_page.route("/info")
def info():
    if current_user.is_authenticated:
        title = "Profile"
    else:
        title = "Login"
    return render_template(
        "user-info.html",
        next=request.args.get("next", ""),
        title=title,
        timezones=timezones,
    )

@login_page.route("/set_info", methods=["POST"])
@login_required
def set_info():
    errmsgs = []
    data = {}
    # Need to do data validation
    for col, val in request.form.items():
        try:
            typ = db.students.col_type[col]
            data[col] = process_user_input(val, col, typ)
        except Exception as err:
            errmsgs.append(format_input_errmsg(err, val, col))
    if errmsgs:
        return show_input_errors(errmsgs)
    for k, v in data.items():
        setattr(current_user, k, v)
    if current_user.save():
        flash(Markup("Your information/preferences have been recorded"))
    return redirect(url_for(".info"))

@login_page.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        identifier = request.form["identifier"]
        # Add passwords later
        if db.students.exists({"identifier", identifier}):
            flash_error("The identifier '%s' is already registered!", identifier)
            return make_response(render_template("register.html", title="Register", identifier=identifier))
        # Should maybe abstract this
        db.students.insert_many([{"identifier": identifier}])
        user = Student(identifier=identifier)
        login_user(user, remember=True)
        flash(Markup("You have been registered for PsetPartners!"))
        return redirect(url_for(".info"))
    return render_template("register.html", title="Register", identifier="")

@login_page.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(Markup("You are now logged out.  Have a nice day!"))
    return redirect(url_for(".info"))
