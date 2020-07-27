
from flask import request
from psetpartners import db
from flask_login import UserMixin, AnonymousUserMixin
from pytz import UTC, all_timezones, timezone, UnknownTimeZoneError

preference_types = {
    "gender_affinity": "posint",
    "year_affinity": "posint",
    "group_size": "posint_range",
    "forum": "text",
    "start": "posint",
    "together": "posint",
    }

class Student(UserMixin):
    properties = sorted(db.students.col_type) + ["id"]
    def __init__(self, kerb):
        self.kerb = kerb
        self._authenticated = True # for now auto authenticate, eventually use Touchstone
        data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        if data is None:
            db.students.insert_many([{"kerb": kerb}])
            data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        self.__dict__.update(data)
        if self.timezone is None:
            self.timezone = request.cookies.get("browser_timezone", "UTC")
            print(self.timezone)
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

    def get_id(self):
        return self.kerb

    @property
    def tz(self):
        try:
            return timezone(self.timezone)
        except UnknownTimeZoneError:
            return timezone("UTC")

    def save(self):
        db.students.update({"kerb": self.kerb}, {col: getattr(self, col, None) for col in db.students.search_cols})

class AnonymousStudent(AnonymousUserMixin):
    # This mainly exists so that login page works
    @property
    def tz(self):
        return timezone("UTC")

    def get_id(self):
        return ""
