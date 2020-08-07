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

strength_options = ["no preference", "nice to have", "weakly preferred", "preferred", "strongly preferred", "required"]
default_strength = "preferred" # only relevant when preference is set to non-emtpy/non-zero value

# Note that these also appear in static/options.js, you need to update both
year_options = [
    (1, "first year"),
    (2, "sophomore"),
    (3, "junior"),
    (4, "senior or super senior"),
    (5, "graduate student"),
    ]

gender_options = [
    ("female", "female"),
    ("male", "male"),
    ("non-binary", "non-binary"),
    ]

location_options = [
    ("near", "on campus or near MIT"),
    ("far", "not hear MIT"),
    #("baker", "Baker House"),
    #("buron-conner", "Burton Conner House"),
    #("east", "East Campus"),
    #("macgregor", "MacGregor House"),
    #("maseeh", "Maseeh Hall"),
    #("mccormick", "McCormick Hall"),
    #("new", "New House"),    
    #("next", "Next House"),
    #("random", "Random Hall"),
    #("simmons", "Simmons Hall"),
    #("epsilontheta", "Epsilon Theta"),
    #("fenway", "Fenway House"),
    #("pika", "pika"),
    #("student", "Student House"),
    #("wilg", "WILG"),
    #("amherst", "70 Amherst Street"),
    #("ashdown", "Ashdown House"),
    #("edgerton", "Edgerton House"),
    #("tower4", "Graduate Tower at Site 4"),
    #("sidneypacific", "Sidney-Pacific"),
    #("tang", "Tang Hall"),
    #("warehouse", "The Warehous"),
    #("westgate", "Westgate"),    
    ]

student_options = {
    "year" : year_options,
    "gender": gender_options,
    "location": location_options,
}

start_options = [
    (6, "shortly after the problem set is posted"),
    (4, "3-4 days before the pset is due"),
    (2, "1-2 days before the pset is due"),
    ]

together_options = [
    (1, "solve the problems together"),
    (2, "discuss strategies, work together if stuck"),
    (3, "work independently but check answers"),
    ]

forum_options = [
    ("text", "text (e.g. Slack or Zulip)"),
    ("video", "video (e.g. Zoom)"),
    ("in-person", "in person"),
    ]

size_options = [
    (2, "2 students"),
    (3, "3-4 students"),
    (5, "5-8 students"),
    (8, "more than 8 students"),
    ]

departments_affinity_options = [
    (1, "someone else in one of my departments"),
    (2, "only students in one of my departments"),
    (3, "students in many departments"),
    ]

year_affinity_options = [
    (1, "someone else in my year"),
    (2, "only students in my year"),
    (3, "students in multiple years"),
    ]

gender_affinity_options = [
    (1, "someone else with my gender identity"),
    (2, "only students with my gender identity"),
    (3, "a diversity of gender identities"),
    ]

student_preferences = {
    "start": { "type": "posint", "options": start_options },
    "together": { "type": "posint", "options": together_options },
    "forum": { "type": "text", "options": forum_options },
    "size": { "type": "posint", "options": size_options },
    "departments_affinity": { "type": "posint", "options": departments_affinity_options },
    "year_affinity": { "type": "posint", "options": year_affinity_options },
    "gender_affinity": { "type": "posint", "options": gender_affinity_options },
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

def cleanse_student_data(data):
    kerb = data.get("kerb","")
    if not data.get("preferred_name"):
        data["preferred_name"] = kerb
    for col in student_options:
        if data.get(col):
            if not data[col] in [r[0] for r in student_options[col]]:
                print("Ignoring unknown %s %s for student %s"%(col,data[col],data,kerb))
                data.col = None # None will get set later
    if data["preferences"] is None:
        data["preferences"] = {}
    if data["strengths"] is None:
        data["strengths"] = {}
    for pref in list(data["preferences"]):
        if not pref in student_preferences:
            print("Ignoring unknown preference %s for student %s"%(pref,kerb))
            data["preferences"].pop(pref)
        else:
            if not data["preferences"][pref]:
                data["preferences"].pop(pref)
            elif not data["preferences"][pref] in [r[0] for r in student_preferences[pref]["options"]]:
                print("Ignoring invalid preference %s = %s for student %s"%(pref,data["preferences"][pref],kerb))
                data["preferences"].pop(pref)
    for pref in list(data["strengths"]):
        if not pref in data["preferences"]:
            data["strengths"].pop(pref)
        else:
           if data["strengths"][pref] < 1 or data["strengths"][pref] > len(strength_options):
                data["strengths"][pref] = default_strength
    for pref in data["preferences"]:
        if not pref in data["strengths"]:
            data["strengths"][pref] = default_strength

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
        cleanse_student_data(data)
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
        self.class_data = self.student_class_data()
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
            if class_number in self.class_data and any([self.class_data[class_number]["preferences"] != self.preferences,
                self.class_data[class_number]["strengths"] != self.strengths]):
                r["preferences"] = self.class_data[class_number]["preferences"]
                r["strengths"] = self.class_data[class_number]["strengths"]
            else:
                r["preferences"] = None
                r["strengths"] = None
            S.append(r)
        S = sorted(S, key=lambda x: x["class_id"])
        T = sorted(db.classlist.search(q), key=lambda x: x["class_id"])
        if S != T:
            db.classlist.delete(q)
            if S:
                print("Updating classlist with %s" % S)
                db.classlist.insert_many(S)
            print("Updated classlist")

    def student_class_data(self, year=current_year(), term=current_term(), include_groups=False):
        # TODO: Use a join here (but there is no point in doing this until the schema stabilizes)
        class_data = {}
        for r in db.classlist.search({"student_id":self.id, "year": year, "term": term}, projection=["class_id", "preferences", "strengths"]):
            r.update(db.classes.lucky({"id":r["class_id"]},projection=["class_number", "class_name", "homepage", "pset_dates", "instructor_names"]))
            if not r["preferences"]:
                r["preferences"] = self.preferences
                r["strengths"] = self.strengths
            if include_groups:
                group_id = db.grouplist.lucky({"class_id":r["class_id"],"student_id":id},projection="group_id")
                if group_id is not None:
                    r["group"] = db.groups.lucky({"id": group_id}, projection=["id", "group_name", "visibility", "preferences", "strengths"])
            class_data[r["class_number"]] = r
        return class_data

class AnonymousStudent(AnonymousUserMixin):
    # This mainly exists so that login page works   
    @property
    def tz(self):
        return timezone("UTC")
