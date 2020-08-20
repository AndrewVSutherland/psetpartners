import re
from psetpartners import app
from psetpartners.getdb import getdb
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

commitment_options = [
    (1, "I'm still shopping and/or not registered"),
    (2, "Other courses might be a higher priority"),
    (3, "This course is a top priority for me"),
    ]

confidence_options = [
    (1, "This will be all new for me"),
    (2, "I have seen some of this material before"),
    (3, "I am quite comfortable with this material"),
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

commitment_affinity_options = [
    (1, "someone else with my level of commitment"),
    (2, "only students with my level of commitment"),
    ]

confidence_affinity_options = [
    (1, "someone else at my comfort level"),
    (2, "only students at my comfort level"),
    (3, "a diversity of comfort levels"),
    ]

student_preferences = {
    'start': { 'type': "posint", 'options': start_options },
    'together': { 'type': "posint", 'options': together_options },
    'forum': { 'type': "text", 'options': forum_options },
    'size': { 'type': "posint", 'options': size_options },
    'departments_affinity': { 'type': "posint", 'options': departments_affinity_options },
    'year_affinity': { 'type': "posint", 'options': year_affinity_options },
    'gender_affinity': { 'type': "posint", 'options': gender_affinity_options },
    'commitment_affinity': { 'type': "posint", 'options': commitment_affinity_options },
    'confidence_affinity': { 'type': "posint", 'options': confidence_affinity_options },
}

student_affinities = [ 'departments', 'year', 'gender' ]
student_class_affinities = [ 'commitment', 'confidence' ]

student_class_properties = {
    "commitment" : { 'type': "posint", 'options': commitment_options },
    "confidence" : { 'type': "posint", 'options': confidence_options },
}

CLASS_NUMBER_RE = re.compile(r"^(\d+).(S?)(\d+)([A-Z]*)")
COURSE_NUMBER_RE = re.compile(r"^(\d*)([A-Z]*)")

def course_number_key(s):
    r = COURSE_NUMBER_RE.match(s)
    if r.group(1) == '':
        return 27*27*27 + 27*27*(ord(r.group(2)[0])-ord('A')+1) + 27*(ord(r.group(2)[1])-ord('A')+1) + ord(r.group(2)[2])-ord('A')+1
    return 27*int(r.group(1)) + ((ord(r.group(2)[0])-ord('A')+1) if r.group(2) != '' else 0)

def current_classes(year=current_year(), term=current_term()):
    db = getdb()
    classes = [(r['class_number'], r['class_name']) for r in db.classes.search({'year': year, 'term': term}, projection=['class_number', 'class_name'])]
    return sorted(classes)

def departments():
    db = getdb()
    departments = [(r['course_number'], r['course_name']) for r  in db.departments.search({}, projection=['course_number', 'course_name'])]
    return sorted(departments, key = lambda x: course_number_key(x[0]))

def cleanse_student_data(data):
    kerb = data.get('kerb', "")
    if not data.get('preferred_name'):
        data['preferred_name'] = kerb
    for col in student_options:
        if data.get(col):
            if not data[col] in [r[0] for r in student_options[col]]:
                app.logger.warning("Ignoring unknown %s %s for student %s"%(col,data[col],data,kerb))
                data.col = None # None will get set later
    if data['preferences'] is None:
        data['preferences'] = {}
    if data['strengths'] is None:
        data['strengths'] = {}
    for pref in list(data["preferences"]):
        if not pref in student_preferences:
            app.logger.warning("Ignoring unknown preference %s for student %s"%(pref,kerb))
            data['preferences'].pop(pref)
        else:
            if not data['preferences'][pref]:
                data['preferences'].pop(pref)
            elif not data["preferences"][pref] in [r[0] for r in student_preferences[pref]["options"]]:
                app.logger.warning("Ignoring invalid preference %s = %s for student %s"%(pref,data["preferences"][pref],kerb))
                data['preferences'].pop(pref)
    for pref in list(data['strengths']):
        if not pref in data['preferences']:
            data['strengths'].pop(pref)
        else:
           if data['strengths'][pref] < 1 or data['strengths'][pref] > len(strength_options):
                data['strengths'][pref] = default_strength
    for pref in data['preferences']:
        if not pref in data['strengths']:
            data['strengths'][pref] = default_strength

class Student(UserMixin):
    def __init__(self, kerb=None):
        self._db = getdb()
        if not kerb:
            raise ValueError("kerb required to create new student")
        data = self._db.students.lucky({"kerb":kerb}, projection=3)
        if data is None:
            data = { col: None for col in self._db.students.col_type }
            data["kerb"] = kerb
            data["id"] = -1
            data["new"] = True
        else:
            data["new"] = False
        self._authenticated = True
        cleanse_student_data(data)
        self.__dict__.update(data)
        assert self.kerb
        if self.hours is None:
            self.hours = [[False for j in range(24)] for i in range(7)]
        for col, typ in self._db.students.col_type.items():
            if getattr(self, col, None) is None:
                if typ == "text":
                    setattr(self, col, "")
                if typ == "jsonb":
                    setattr(self, col, {})
                if typ.endswith("[]"):
                    setattr(self, col, [])
        self.class_data = self.student_class_data()
        self.classes = sorted(list(self.class_data))
        assert self.kerb

    @property
    def col_type(self):
        return self._db.students.col_type

    @property
    def tz(self):
        if not getattr(self,'timezone',"") or self.timezone == DEFAULT_TIMEZONE_NAME:
            return timezone(DEFAULT_TIMEZONE)
        try:
            return timezone(self.timezone)
        except UnknownTimeZoneError:
            return timezone(DEFAULT_TIMEZONE)

    @property
    def is_authenticated(self):
        return getattr(self, '_authenticated', None)

    @property
    def is_anonymous(self):
        return False if getattr(self, 'kerb', "") else True

    @property
    def get_id(self):
        return lambda: getattr(self, 'kerb', None)

    def save(self):
        # TODO: put all of this in a transaction
        if self.new:
            assert self._db.students.lookup(self.kerb) is None
            rec = {col: getattr(self, col, None) for col in self._db.students.search_cols if col != "id"}
            self._db.students.insert_many([rec])
            self.id = rec["id"]
        else:
            self._db.students.update({"id": self.id, "kerb": self.kerb}, {col: getattr(self, col, None) for col in self._db.students.search_cols})
        if len(set(self.classes)) < len(self.classes):
            raise ValueError("Duplicates in class list %s" % self.classes)
        q = {'student_id':self.id, 'year': current_year(), 'term': current_term()}
        S = []
        for class_number in self.classes:
            query = { 'class_number': class_number, 'year': current_year(), 'term': current_term()}
            class_id = self._db.classes.lucky(query, projection='id')
            if class_id is None:
                raise ValueError("Class %s is not listed in the pset partners list of classes for this term." % class_number)
            r = q.copy()
            r['class_id'] = class_id
            r['properties'] = self.class_data[class_number].get('properties',None)
            if class_number in self.class_data and any([self.class_data[class_number]['preferences'] != self.preferences,
                self.class_data[class_number]["strengths"] != self.strengths]):
                r['preferences'] = self.class_data[class_number]['preferences']
                r['strengths'] = self.class_data[class_number]['strengths']
            else:
                r['preferences'] = None
                r['strengths'] = None
            S.append(r)
        S = sorted(S, key=lambda x: x['class_id'])
        T = sorted(self._db.classlist.search(q), key=lambda x: x['class_id'])
        if S != T:
            self._db.classlist.delete(q)
            if S:
                self._db.classlist.insert_many(S)

    def student_class_data(self, year=current_year(), term=current_term()):
        # TODO: Use a join here (but there is no point in doing this until the schema stabilizes)
        class_data = {}
        classes = self._db.classlist.search(
            { 'student_id': self.id, "year": year, 'term': term},
            projection=['class_id', 'properties', 'preferences', 'strengths'],
            )
        for r in classes:
            r.update(self._db.classes.lucky({"id": r['class_id']}, projection=['class_number']))
            if not r['preferences']:
                r['preferences'] = self.preferences
                r['strengths'] = self.strengths
            class_data[r["class_number"]] = r
        return class_data

class AnonymousStudent(AnonymousUserMixin):
    # This mainly exists so that login page works   
    @property
    def tz(self):
        return timezone("UTC")

    @property
    def is_authenticated(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return True

    @property
    def get_id(self):
        return None

def generate_test_population(num_students=300,max_classes=6):
    """ generates a random student population for testing (destorys existing test data) """
    from random import randint
    from psetpartners import db
    from psetpartners.utils import timezones
    pronouns = { 'female': 'she/her', 'male': 'he/him', 'non-binary': 'they/them' }

    def rand(x):
        return x[randint(0,len(x)-1)]

    choice = input("Are you sure? This will destroy the existing test database? [y/n] ").lower()
    if not choice or choice[0] != 'y':
        print("No changes made.")
        return
    db.test_students.delete({})
    db.test_groups.delete({})
    db.test_classlist.delete({})
    db.test_grouplist.delete({})
    print("Deleted all records in test_students, test_groups, test_classlist, and test_grouplist.")
    year, term = current_year(), current_term()
    S = []
    for n in range(num_students):
        s = { 'kerb': "test%03d" % n }
        firstname = db.names.random()
        name = db.math_adjectives.random({'firstletter': firstname[0]}).capitalize() + " " + firstname.capitalize()
        s['preferred_name'] = s['full_name'] = name
        departments = [db.departments.random()]
        if randint(0,2) == 2:
            departments.append(db.departments.random({'course_number':{'$ne':departments[0]}}))
        s['departments'] = departments
        s['year'] = rand(year_options)[0] if randint(0,4) else None
        s['gender'] = db.names.lookup(firstname,projection="gender") if randint(0,1) else None
        if s['gender']:
            if randint(0,1):
                s['preferred_pronouns'] = pronouns[s['gender']]
            else:
                if randint(0,2) == 0:
                    s['preferred_pronouns'] = "they/them"
        s['location'] = 'near' if randint(0,3) == 0 else rand(location_options)[0]
        s['timezone'] = DEFAULT_TIMEZONE if s['location'] == 'near' else rand(timezones)[0]
        hours = [[False for j in range(24)] for i in range(7)]
        for i in range(7):
            start = randint(0,23)
            end = randint(start+1,24)
            for j in range(start,end):
                hours[i][j] = True
        s['hours'] = hours
        prefs, strengths = {}, {}
        for p in student_preferences:
            if not p.endswith("_affinity"):
                if randint(0,1):
                    prefs[p] = rand(student_preferences[p]['options'])[0]
                    strengths[p] = randint(1,5)
            else:
                q = p.split('_')[0]
                if q in student_affinities and s[q]:
                    prefs[p] = rand(student_preferences[p]['options'])[0]
                    strengths[p] = randint(1,5)
        s['preferences'] = prefs
        s['strengths'] = strengths
        S.append(s)
        # TODO: There seems to be a bug in insert_many, if you comment out the line below and uncomment the next line
        # the student records will be inserted but they will all have preferred_pronouns set to None
        # and occasionally there will be a key_error inside insert_many on the preferred_pronouns column
        db.test_students.insert_many([s])
    # db.test_students.insert_many(S)
    S = []
    for s in db.test_students.search(projection=3):
        student_id = s["id"]
        classes = [db.classes.random({'year': year, 'term': term}, projection='id')]
        for m in range(2,max_classes):
            if randint(0,2) == 2:
                break;
            classes.append(db.classes.random({'year': year, 'term': term}, projection='id'))
        for i in range(len(classes)):
            prefs, strengths, props = {}, {}, {}
            for p in student_class_properties:
                if randint(0,1):
                    props[p] = rand(student_class_properties[p]['options'])[0]
                    strengths[p] = randint(1,5)
                    if randint(0,1):
                        pa = p + "_affinity"
                        prefs[pa] = rand(student_preferences[pa]['options'])[0]
                        strengths[pa] = randint(1,5)
            for p in student_preferences:
                if not p.endswith("_affinity"):
                    if p in s['preferences']:
                        if randint(0,2):
                            prefs[p] = s['preferences'][p]
                            strengths[p] = s['strengths'][p]
                        else:
                            prefs[p] = rand(student_preferences[p]['options'])[0]
                            strengths[p] = randint(1,5)
                    elif randint(0,2) == 0:
                        prefs[p] = rand(student_preferences[p]['options'])[0]
                        strengths[p] = randint(1,5)
            for p in student_affinities:
                pa = p + "_affinity"
                if pa in s['preferences'] and randint(0,2):
                    prefs[p] = s['preferences'][pa]
                    strengths[p] = s['strengths'][pa]
                elif randint(0,2) == 0:
                    prefs[pa] = rand(student_preferences[pa]['options'])[0]
                    strengths[pa] = randint(1,5)
            c = {'year': year, 'term': term, 'student_id': student_id, 'class_id': classes[i], 'preferences': prefs, 'strengths': strengths, 'properties': props}
            S.append(c)
    db.test_classlist.insert_many(S)
    S = []
    for class_id in db.classes.search({'year': year, 'term': term}, projection='id'):
        n = len(list(db.test_classlist.search({'class_id':class_id},projection='id')))
        print(n)
        for i in range(n//10):
            name = db.plural_nouns.random()
            name = db.positive_adjectives.random({'firstletter':name[0]}).capitalize() + " " + name.capitalize()
            g = {"class_id": class_id, "group_name": name, "visibility":2}
            if not g in S:
                S.append(g)
    if ( S ):
        db.test_groups.insert_many(S)
        S = []
        for g in db.test_groups.search(projection=3):
            n = 0
            group_id, class_id = g["id"], g["class_id"]
            while True:
                student_id = rand(list(db.test_classlist.search({'class_id': class_id},projection="student_id")))
                if not student_id in [r['student_id'] for r in S if r['class_id'] == class_id]:
                    S.append({'class_id': class_id, 'student_id': student_id, 'group_id': group_id})
                    n = n + 1
                if randint(0,2) == 0:
                    break
            if ( n == 0 ):
                db.test_groups.delete({'id': group_id})
        db.test_grouplist.insert_many(S)
