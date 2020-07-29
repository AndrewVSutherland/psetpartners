
from flask import request
from psetpartners import db
from flask_login import UserMixin, AnonymousUserMixin
from pytz import timezone, UnknownTimeZoneError
from psetpartners.utils import DEFAULT_TIMEZONE

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
            print("creating new user record for "+kerb)
            db.students.insert_many([{"kerb": kerb, "preferred_name": kerb}])
            data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        else:
            print("loaded user record for "+kerb)
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
        print(self.__dict__)

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
