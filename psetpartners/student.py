import re
from flask import request
from psetpartners import db
from flask_login import UserMixin, AnonymousUserMixin
from pytz import timezone, UnknownTimeZoneError
from psetpartners.utils import (
    DEFAULT_TIMEZONE_NAME,
    DEFAULT_TIMEZONE,
    current_year,
    current_term,
    )

preference_types = {
    "departments_affinity": "posint",
    "year_affinity": "posint",
    "gender_affinity": "posint",
    "group_size": "posint",
    "forum": "text",
    "start": "posint",
    "together": "posint",
    }

CLASS_NUMBER_RE = re.compile(r"^(\d+).(\d+)([A-Z]*)")
COURSE_NUMBER_RE = re.compile(r"^(\d*)([A-Z]*)")

def class_number_key(s):
    r = CLASS_NUMBER_RE.match(s)
    return 260000*int(r.group(1)) + 26*int(r.group(2)) + ((ord(r.group(3)[0])-ord('A')) if r.group(3) != '' else 0)

def course_number_key(s):
    r = COURSE_NUMBER_RE.match(s)
    if r.group(1) == '':
        return 25*26*26 + 26*26*(ord(r.group(2)[0])-ord('A')) + 26*(ord(r.group(2)[1])-ord('A')) + ord(r.group(2)[2])-ord('A')
    return 26*int(r.group(1)) + ((ord(r.group(2)[0])-ord('A')) if r.group(2) != '' else 0)

def current_classes(year=current_year(), term=current_term()):
    classes = [(r["class_number"], r["class_name"]) for r in db.classes.search({"year": year, "term": term}, projection=["class_number", "class_name"])]
    return sorted(classes, key = lambda x: class_number_key(x[0]))

def departments():
    departments = [(r["course_number"], r["course_name"]) for r  in db.departments.search({}, projection=["course_number", "course_name"])]
    return sorted(departments, key = lambda x: course_number_key(x[0]))

def student_class_data(id,include_groups=False):
    # TODO: Use a join here (but there is no point in doing this until the schema stabilizes)
    classes = list(db.classlist.search({"student_id":id, "year": current_year(), "term": current_term()},
        projection=["class_id", "preferences", "strengths"]))
    for r in classes:
        r.update(db.classes.lucky({"id":r["class_id"]},projection=["class_number", "class_name", "homepage", "pset_dates", "instructor_names"]))
        if include_groups:
            group_id = db.grouplist.lucky({"class_id":r["class_id"],"student_id":id},projection="group_id")
            if group_id is not None:
                r["group"] = db.groups.lucky({"id": group_id}, projection=["id", "group_name", "visibility", "preferences", "strengths"])
    return { r["class_number"]: r for r in classes }

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
            self.timezone = DEFAULT_TIMEZONE_NAME
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
        self.class_data = student_class_data(self.id)
        self.classes = sorted(list(self.class_data), key=class_number_key)

    @property
    def tz(self):
        if not self.timezone or self.timezone == DEFAULT_TIMEZONE_NAME:
            return timezone(DEFAULT_TIMEZONE)
        try:
            return timezone(self.timezone)
        except UnknownTimeZoneError:
            return timezone(DEFAULT_TIMEZONE)

    def save(self):
        db.students.update({"kerb": self.kerb}, {col: getattr(self, col, None) for col in db.students.search_cols})
        if len(set(self.classes)) < len(self.classes):
            raise ValueError("Duplicates in class list %s" % self.classes)
        # TODO: put all of this in a transaction
        q = {"student_id":self.id, "year": current_year(), "term": current_term()}
        S = []
        for class_number in self.classes:
            query = {"class_number": class_number, "year": current_year(), "term": current_term()}
            class_id = db.classes.lucky(query, projection="id")
            if class_id is None:
                raise ValueError("Class %s is not listed in the pset partners list of classes for this term." % class_number)
            r = q.copy()
            r["class_id"] = class_id
            r["preferences"] = self.class_data[class_number]["preferences"] if class_number in self.class_data else None
            r["strengths"] = self.class_data[class_number]["strengths"] if class_number in self.class_data else None
            S.append(r)
        S = sorted(S, key=lambda x: x["class_id"])
        T = sorted(db.classlist.search(q), key=lambda x: x["class_id"])
        if S != T:
            db.classlist.delete(q)
            if S:
                print(S)
                db.classlist.insert_many(S)
            print("Updated classlist")

class AnonymousStudent(AnonymousUserMixin):
    # This mainly exists so that login page works   
    @property
    def tz(self):
        return timezone("UTC")
