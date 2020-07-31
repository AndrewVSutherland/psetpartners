from flask import request
from psetpartners import db
from flask_login import UserMixin, AnonymousUserMixin
from pytz import timezone, UnknownTimeZoneError
from psetpartners.utils import DEFAULT_TIMEZONE
from psetpartners.group import class_number_key

preference_types = {
    "gender_affinity": "posint",
    "year_affinity": "posint",
    "group_size": "posint",
    "forum": "text",
    "start": "posint",
    "together": "posint",
    }

class Student(UserMixin):
    properties = sorted(db.students.col_type) + ["id"]
    def __init__(self, kerb):
        self.kerb = kerb
        if kerb:
            print("automatically authenticated user "+kerb)
            self._authenticated = True # for now auto authenticate, eventually use Touchstone
        data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        if data is None:
            db.students.insert_many([{"kerb": kerb, "preferred_name": kerb}])
            data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        else:
            if not data.get("preferred_name"):
                data["preferred_name"] = kerb
        self.__dict__.update(data)
        if self.timezone is None:
            self.timezone = request.cookies.get("browser_timezone", DEFAULT_TIMEZONE)
        if self.timezone == DEFAULT_TIMEZONE:
            self.timezone = ""
        if self.hours is None:
            self.hours = [[False for j in range(24)] for i in range(7)]
        for col, typ in db.students.col_type.items():
            if getattr(self, col, None) is None:
                if typ == "text":
                    setattr(self, col, "")
                if typ == "jsonb":
                    setattr(self, col, {})
                if typ.endswith("[]"):
                    setattr(self, col, [])
        # Set default preference strengths (will be ignored if preference not specified)
        for col in preference_types:
            if not col in self.strengths:
                self.strengths[col] = 3
        # TODO: Use a join here (but there is no point in doing this until the schema stabilizes)
        classes = list(db.classlist.search({"student_id":self.id},projection=["class_id", "preferences", "strengths"]))
        # we should really be using a join here
        for r in classes:
            r.update(db.classes.lucky({"id":r["class_id"]},projection=["class_number", "class_name", "homepage", "pset_dates", "instructor_names"]))
            group_id = db.grouplist.lucky({"class_id":r["class_id"],"student_id":self.id},projection="group_id")
            if group_id is not None:
                r["group"] = db.groups.lucky({"id": group_id}, projection=["id", "group_name", "visibility", "preferences", "strengths"])
        self.classes = sorted(classes, key=lambda x: class_number_key(x["class_number"]))

    def get_id(self):
        return self.kerb

    @property
    def tz(self):
        if not self.timezone:
            return timezone(DEFAULT_TIMEZONE)
        try:
            return timezone(self.timezone)
        except UnknownTimeZoneError:
            return timezone(DEFAULT_TIMEZONE)

    def save(self):
        db.students.update({"kerb": self.kerb}, {col: getattr(self, col, None) for col in db.students.search_cols})

class AnonymousStudent(AnonymousUserMixin):
    # This mainly exists so that login page works   
    @property
    def tz(self):
        return timezone("UTC")

    def get_id(self):
        return ""
