
from flask import request
from psetpartners import db
from flask_login import UserMixin, AnonymousUserMixin
from pytz import UTC, all_timezones, timezone, UnknownTimeZoneError


class Student(UserMixin):
    properties = sorted(db.students.col_type) + ["id"]
    preference_types = { # omit weekdays and time_slots since those are handled separately
        "collaborate": "text",
        "group_min": "smallint",
        "group_max": "smallint",
        "start": "text",
        "together": "text",
    }
    def __init__(self, kerb):
        self.kerb = kerb
        data = db.students.lucky({"kerb":kerb}, projection=Student.properties)
        if data is None:
            db.students.insert_many([{"kerb": kerb}])
            self.timezone = None
            self.preferences = None
        else:
            self.__dict__.update(data)
            self._authenticated = True
        if self.timezone is None:
            self.timezone = request.cookies.get("browser_timezone", "UTC")
        if self.preferences is None:
            self.preferences = {
                "weekdays": [],
                "time_slots": [],
            }
        for col, typ in db.students.col_type.items():
            if typ == "text" and getattr(self, col, None) is None:
                setattr(self, col, "")

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
