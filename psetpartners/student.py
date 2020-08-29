import re
from . import app
from .app import debug_mode
from .dbwrapper import getdb, students_in_class, students_in_group, count_rows
from flask import url_for
from flask_login import UserMixin, AnonymousUserMixin
from pytz import timezone, UnknownTimeZoneError
from .utils import (
    DEFAULT_TIMEZONE_NAME,
    DEFAULT_TIMEZONE,
    current_year,
    current_term,
    hours_from_default,
    flash_announce
    )
from .token import generate_timed_token
from .group import generate_group_name
from psycodict import DelayCommit

strength_options = ["no preference", "nice to have", "weakly preferred", "preferred", "strongly preferred", "required"]
default_strength = "preferred" # only relevant when preference is set to non-emtpy/non-zero value

welcome = """
<b>Welcome to pset partners!</b>
To begin, enter your preferred name and any other personal details you care to share.
Then select your location, timezone, the math classes you are taking this term, and your hours of availability
(include hours of partial availability).  You can then explore your options for finding pset partners using
the Preferences and Partners buttons.
"""


# Note that these also appear in static/options.js, you need to update both!

departments_options = [
  ( '1', 'Civil and Environmental Engineering'),
  ( '2', 'Mechanical Engineering'),
  ( '3', 'Materials Science and Engineering'),
  ( '4', 'Architecture'),
  ( '5', 'Chemistry'),
  ( '6', 'EECS'),
  ( '7', 'Biology'),
  ( '8', 'Physics'),
  ( '9', 'Brain and Cognitive Sciences'),
  ( '10', 'Chemical Engineering'),
  ( '11', 'Urban Studies and Planning'),
  ( '12', 'EAPS'),
  ( '14', 'Economics'),
  ( '15', 'Management'),
  ( '16', 'Aeronautics and Astronautics'),
  ( '17', 'Political Science'),
  ( '18', 'Mathematics'),
  ( '20', 'Biological Engineering'),
  ( '21', 'Humanities'),
  ( '21A', 'Anthropology'),
  ( '21E/21S', 'Humanities + Eng./Science'),
  ( '21G', 'Global Studies and Languages'),
  ( '21H', 'History'),
  ( '21L', 'Literature'),
  ( '21M', 'Music and Theater Arts'),
  ( '22', 'Nuclear Science and Engineering'),
  ( '24', 'Linguistics and Philosophy'),
  ( 'CMS/21W', 'Comp. Media Studies/Writing'),
  ( 'IDS', 'Data, Systems, and Society'),
  ( 'IMES', 'Medical Engineering and Science'),
  ( 'MAS', 'Media Arts and Sciences'),
  ( 'STS', 'Science, Technology, and Society'),
  ];

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

countable_options = [
    'hours', 'departments', 'year', 'gender', 'location', 'timezone',
    'start', 'together', 'forum', 'size', 'commitment', 'confidence',
    'departments_affinity', 'year_affinity', 'gender_affinity', 'commitment_affinity', 'confidence_affinity',
]

def default_value(typ):
    if typ.endswith('[]'):
        return []
    if typ == "text":
        return ""
    if typ == "jsonb":
        return {}
    return None

CLASS_NUMBER_RE = re.compile(r"^(\d+).(S?)(\d+)([A-Z]*)")
COURSE_NUMBER_RE = re.compile(r"^(\d*)([A-Z]*)")

def _str(s):
    return str(s) if s is not None else ""

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

def is_instructor(kerb):
    db = getdb()
    return db.classes.lucky({'year':current_year(),'term':current_term(),'instructor_kerbs':{'$contains':kerb}},projection="class_number")

def is_admin(kerb):
    db = getdb()
    return db.admins.lucky({'kerb': kerb})

def send_message(sender, recipient, typ, content):
    db = getdb()
    db.messages.insert_many([{'sender_kerb': sender, 'recipient_kerb': recipient, 'type': typ, 'content': content}])

def next_match_date(class_id):
    import datetime

    db = getdb()
    match_dates = db.classes.lucky({'id': class_id}, projection='match_dates')
    if match_dates:
        today = datetime.datetime.now().date()
        match_dates = [d for d in match_dates if d > today]
        if match_dates:
            return match_dates[0].strftime("%b %-d")
    return ""

def max_size_from_prefs(prefs):
    if not 'size' in prefs:
        return None
    bigger = [o[0] for o in size_options if o[0] > prefs['size']]
    if not bigger:
        return None
    return bigger[0]-1

def student_counts(iter, opts):
    counts = { opt: {} for opt in opts if opt in countable_options and not opt in ['hours' 'departments'] }
    count_hours = 'hours' in opts
    count_departments = 'departments' in opts
    if count_hours:
        hours = [0 for i in range(168)]
    if count_departments:
        departments = {}
    pref_opts = [ opt for opt in counts if opt in student_preferences ]
    prop_opts = [ opt for opt in counts if opt in student_class_properties ]
    base_opts = [ opt for opt in counts if opt not in pref_opts and opt not in prop_opts ]
    n = 0
    for r in iter:
        if count_hours:
            off = hours_from_default(r['timezone']) if r['timezone'] else 0
            for i in range(168):
                hours[(i-off) % 168] += 1 if r['hours'][i] else 0
        for opt in base_opts:
            val = str(r.get(opt,""))
            counts[opt][val] = (counts[opt][val]+1) if val in counts[opt] else 1
        for opt in pref_opts:
            val = str(r['preferences'].get(opt,"")) if r.get('preferences') else ""
            counts[opt][val] = (counts[opt][val]+1) if val in counts[opt] else 1
        for opt in prop_opts:
            val = str(r['properties'].get(opt,"")) if r.get('properties') else ""
            counts[opt][val] = (counts[opt][val]+1) if val in counts[opt] else 1
        if count_departments:
            for dept in r.get('departments',[]):
                departments[dept] = departments[dept]+1 if dept in departments else 1
        n += 1
    if count_hours:
        counts['hours'] = hours
    if count_departments:
        counts['departments'] = departments
    counts["students"] = n
    return counts

def group_visibility_counts(class_number, year=current_year(), term=current_term()):
    db = getdb()
    vcounts = {}
    if class_number:
        for v in db.groups.search({'year': year, 'term': term, 'class_number': class_number},projection="visibility"):
            vcounts[v] = vcounts[v]+1 if v in vcounts else 1
    else:
        for v in db.groups.search({'year': year, 'term': term},projection="visibility"):
            vcounts[v] = vcounts[v]+1 if v in vcounts else 1
    return vcounts

def get_counts(classes, opts, year=current_year(), term=current_term()):
    db = getdb();
    counts = {}
    if '' in classes:
        counts[''] = student_counts(db.students.search(), opts)
        counts['']['classes'] = count_rows('classes', {'year': year, 'term': term})
        counts['']['students_classes'] = count_rows('classlist', {'year': year, 'term': term})
        counts['']['groups'] = count_rows('groups', {'year': year, 'term': term})
        counts['']['students_groups'] = count_rows('grouplist', {'year': year, 'term': term})
        counts['']['visibility'] = group_visibility_counts('')
    for c in classes:
        if c:
            cid = db.classes.lucky({'class_number': c, 'year': year, 'term': term}, projection="id")
            counts[c] = student_counts(students_in_class(cid), opts)
            counts[c]['groups'] = count_rows('groups',{'class_id': cid})
            counts[c]['students_groups'] = count_rows('grouplist', {'class_id': cid})
            counts[c]['next_match_date'] = next_match_date(cid)
            counts[c]['visibility'] = group_visibility_counts(c, year=year, term=term)
            counts[c]['class_id'] = cid
    return counts

def class_groups(class_number, opts, year=current_year(), term=current_term(), visibility=None, instructor_view=False):
    db = getdb()
    G = []
    mv = 0 if instructor_view else 2
    for g in db.groups.search({'class_number': class_number, 'year': year, 'term': term, 'visibility' : {'$gte': mv} }, projection=['id']+[o for o in opts if o in db.groups.col_type]):
        members = list(students_in_group(g['id']))
        n = len(members)
        p = [_str(g['preferences'].get(k,"")) for k in ["start", "together", "forum"]] if g.get('preferences') else ["", "", ""]
        r = [str(g['id']), g['group_name'], p[0], p[1], p[2], str(n), _str(g.get("max","")), _str(g.get("visibility",0))]
        if 'members' in opts and (g['visibility'] == 3 or instructor_view):
            r.append(sorted([[_str(s.get(k,"")) for k in ['preferred_name','preferred_pronouns','year','kerb']] for s in members]))
        G.append(r)
    return sorted(G,key=lambda x: x[0])

def cleanse_student_data(data):
    kerb = data.get('kerb', "")
    for col in student_options:
        if data.get(col):
            if not data[col] in [r[0] for r in student_options[col]]:
                app.logger.warning("Ignoring unknown %s %s for student %s"%(col,data[col],data,kerb))
                data.col = None # None will get set later
    if data['preferences'] is None:
        data['preferences'] = {}
    if data['strengths'] is None:
        data['strengths'] = {}
    if data['toggles'] is None:
        data['toggles'] = {}
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
    def __init__(self, kerb):
        if not kerb:
            raise ValueError("kerb required to create new student")
        self._db = getdb()
        data = self._db.students.lucky({"kerb":kerb}, projection=3)
        if data is None:
            data = { col: None for col in self._db.students.col_type }
            data["kerb"] = kerb
            data["id"] = -1
            data["new"] = True
            if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
                send_message("", kerb, "welcome", welcome)
        else:
            data["new"] = False
        cleanse_student_data(data)
        self.__dict__.update(data)
        assert self.kerb
        if self.hours is None:
            self.hours = [False for i in range(168)]
        for col, typ in self._db.students.col_type.items():
            if getattr(self, col, None) is None:
                setattr(self, col, default_value(typ))
        self._reload()
        assert self.kerb

    @property
    def is_student(self):
        return True

    @property
    def is_instructor(self):
        return False

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
        return True if getattr(self, 'kerb', "") else False

    @property
    def is_admin(self):
        return self.kerb and is_admin(self.kerb)

    @property
    def is_anonymous(self):
        return False if getattr(self, 'kerb', "") else True

    @property
    def get_id(self):
        return lambda: getattr(self, 'kerb', None)

    def send_message(self, msg, sender_kerb=None):
        r = {'content': msg, 'recipient_kerb': self.kerb}
        if sender_kerb:
            r['sender_kerb'] = sender_kerb
        self._db.messages.insert_many([r])

    def flash_pending(self):
        for msg in self._db.messages.search({'recipient_kerb': self.kerb, 'read': None}, projection=3):
            flash_announce("%s:%s" % (msg['id'], msg['content']))

    def acknowledge(self, msgid):
        self._db.messages.update({'id': msgid},{'read':True})
        return "ok"

    def save(self):
        with DelayCommit(self):
            return self._save()

    def join(self, group_id):
        with DelayCommit(self):
            return self._join(group_id)

    def leave(self, group_id):
        with DelayCommit(self):
            return self._leave(group_id)

    def pool(self, class_id):
        with DelayCommit(self):
            return self._pool(class_id)

    def match(self, class_id):
        with DelayCommit(self):
            return self._match(class_id)

    def create_group(self, group_id, public=True):
        with DelayCommit(self):
            return self._create_group(group_id, public=public)

    def accept_invite(self, invite):
        sid = self._db.students.lookup(invite['kerb'], projection='id')
        if sid is None:
            raise ValueError("Unknown student.")
        g = self._db.groups.lucky({'id': invite['group_id']}, projection=3)
        if g is None:
            raise ValueError("Group not found.")
        if not self._db.grouplist.lucky({'group_id': g['id'], 'student_id': sid}, projection="id"):
            raise ValueError("The student who created the invitation is no longer a member of the group.")
        if g['year'] != current_year() or g['term'] != current_term():
            raise ValueError("This invitation is from a previous term.")
        gid = self._db.grouplist.lucky({'class_number': g['class_number'], 'year': g['year'], 'term': g['term'], 'student_id': self.id}, projection='group_id')
        if gid is not None:
            if gid != g['id']:
                raise ValueError("You are currently a mamber of a different group in %s\n.  To accept this invitation you need to leave your current group first." % g['class_number'])
        if not g['class_number'] in self.classes:
            self.classes.append(g['class_number'])
            with DelayCommit(self):
                self._save()
        if gid == g['id']:
            self.send_message("You are already a member of the group %s in %s.  Welcome back!" % (g['group_name'], g['class_number']))
        else:
            self.join(g['id'])
            self.send_message("Welcome to the group %s in %s!" % (g['group_name'], g['class_number']))
        self.update_toggle('ct', g['class_number'])
        self.update_toggle('ht', 'partner-header')

    def update_toggle(self, name, value):
        if not name:
            return "no"
        if self.toggles.get(name) == value:
            return "ok"
        print("updated toggle " + name + " to " + value);
        self.toggles[name] = value;
        self._db.students.update({'id': self.id}, {'toggles': self.toggles}, resort=False)
        return "ok"

    def _reload(self):
        """ This function should be called after any updates to classlist or grouplist related this student """
        self.class_data = self._class_data()
        self.classes = sorted(list(self.class_data))
        self.group_data = self._group_data()
        self.groups = sorted(list(self.group_data))

    def _save(self):
        if self.new:
            assert self._db.students.lookup(self.kerb) is None
            rec = {col: getattr(self, col, None) for col in self._db.students.search_cols if col != "id"}
            self._db.students.insert_many([rec], resort=False)
            self.id = rec["id"]
        else:
            self._db.students.update({"id": self.id, "kerb": self.kerb}, {col: getattr(self, col, None) for col in self._db.students.search_cols}, resort=False)
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
            r['class_number'] = class_number
            r['properties'], r['preferences'], r['strengths'] = {}, {}, {}
            # if user was just added to the class (e.g. via an invitation) we may not have any class_data for it
            if class_number in self.class_data:
                r['properties'] = self.class_data[class_number].get('properties', {})
                if self.class_data[class_number].get('preferences') is not None and any([self.class_data[class_number]['preferences'] != self.preferences, self.class_data[class_number]["strengths"] != self.strengths]):
                    r['preferences'] = self.class_data[class_number]['preferences']
                    r['strengths'] = self.class_data[class_number]['strengths']
            S.append(r)
        S = sorted(S, key=lambda x: x['class_id'])
        T = sorted(self._db.classlist.search(q), key=lambda x: x['class_id'])
        if S != T:
            self._db.classlist.delete(q, resort=False)
            if S:
                self._db.classlist.insert_many(S, resort=False)
        self._reload()
        return "Changes saved!"

    def _join(self, group_id):
        g = self._db.groups.lucky({'id': group_id}, projection=['class_id', 'class_number', 'year', 'term', 'group_name'])
        if not g:
            app.logger.warning("User %s attempted to join non-existent group %s" % (self.kerb, group_id))
            raise ValueError("Group not found in database")
        c = g['class_number']
        if not c in self.classes:
            app.logger.warning("User %s attempted to join group %s in class %s not in their class list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in any of your classes for this term")
        if c in self.groups:
            app.logger.warning("User %s attempted to join group %s in class %s but is already a member of group %s" % (self.kerb, group_id, c, self.group_data[c]['id']))
            raise ValueError("You are already a mamber of the group %s in class %s, you must leave that group before joining a new one." % (self.group_data[c]['group_name'], c))
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 1}, resort=False)
        r = { k: g[k] for k in  ['class_number', 'year', 'term']}
        r['group_id'], r['student_id'], r['kerb'] = group_id, self.id, self.kerb
        self._db.grouplist.insert_many([r], resort=False)
        self._reload()
        return "Welcome to %s!" % g['group_name']

    def _leave(self, group_id):
        g = self._db.groups.lucky({'id': group_id})
        if not g:
            app.logger.warning("User %s attempted to leave non-existent group %s" % (self.kerb, group_id))
            raise ValueError("Group not found in database.")
        c = g['class_number']
        if not c in self.classes:
            app.logger.warning("User %s attempted to leave group %s in class %s not in their class list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in any of your classes for this term.")
        if not c in self.groups:
            app.logger.warning("User %s attempted to leave group %s in class %s not in their group list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in your list of groups for this term.")
        self._db.grouplist.delete({'group_id': group_id, 'student_id': self.id}, resort=False)
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 0}, resort=False)
        msg = "You have been removed from the group %s in %s." % (g['group_name'], c)
        if not self._db.grouplist.lucky({'group_id': group_id}, projection="id"):
            self._db.groups.delete({'id': group_id}, resort=False)
            self._reload()
            msg += " You were the only member of this group, so it has been disbanded."
        self._reload()
        return msg

    def _pool(self, class_id):
        c = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id}, "class_number")
        if not c:
            app.logger.warning("User %s attempted to join the pool for non-existent class %s" % (self.kerb, class_id))
            raise ValueError("Class not found in database.")
        if not c in self.classes:
            app.logger.warning("User %s attempted to join the pool for class %s not in their class list" % (self.kerb, class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c in self.groups:
            app.logger.warning("User %s attempted to join the pool for class %s but is already a member of group %s in that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are currrently a member of the group %s in %s, you must leave that group before joining the match pool." % (self.group_data[c]['group_name'], c))
        if self.class_data[c]['status'] == 4:
            raise ValueError("We are already working on a match for you in %s, please be patient." % c)
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 2}, resort=False)
        d = next_match_date(class_id)
        self._reload()
        return "You are now in the match pool for %s and will be matched on %s." %(c, d)

    def _match(self, class_id):
        c = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id}, projection="class_number")
        if not c:
            raise ValueError("Class not found in database.")
        if not c in self.classes:
            app.logger.warning("User %s attempted to join the pool for class %s not in their class list" % (self.kerb, class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c in self.groups:
            app.logger.warning("User %s requested a match for class %s but is already a member of group %s in that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are currrently a member of the group %s in %s, you must leave that group before requesting a match." % (self.group_data[c]['group_name'], c))
        if self.class_data[c]['status'] == 3 or self.class_data[c]['status'] == 4:
            return "We are already working on a match for you in %s, please be patient!" % c
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 3}, resort=False)
        self._reload()
        return "We will start working on a match for you in %s, you should receive an email from us within 24 hours." % c

    def _create_group(self, class_id, public=True):
        c = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id}, projection="class_number")
        if not c:
            raise ValueError("Class not found among your classes.")
        if not c in self.classes:
            app.logger.warning("User %s attempted to join the pool for class %s not in their class list" % (self.kerb, class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c in self.groups:
            app.logger.warning("User %s tried to create a group in class %s but is already a member of group %s in that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are currrently a member of the group %s in %s, you must leave that group before creating a new group." % (self.group_data[c]['group_name'], c))
        c = self.class_data[c]
        prefs = { k: c['preferences'][k] for k in c.get('preferences',{}) if not k.endswith('affinity') }
        strengths = { k: c['strengths'][k] for k in c.get('strengths',{}) if not k.endswith('affinity') }
        maxsize = max_size_from_prefs(prefs)
        name = generate_group_name()
        g = {'class_id': class_id, 'year': current_year(), 'term': current_term(), 'class_number': c['class_number'], 'group_name': name,
             'visibility': 2 if public else 1, 'preferences': prefs, 'strengths': strengths, 'editors': [], 'max': maxsize }
        self._db.groups.insert_many([g], resort=False)
        r = {'class_id': class_id, 'group_id': g['id'], 'student_id': self.id, 'kerb': self.kerb, 'class_number': g['class_number'], 'year': g['year'], 'term': g['term'] }
        self._db.grouplist.insert_many([r], resort=False)
        self._reload()
        return "Created the group %s!" % g['group_name']

    def _class_data(self, year=current_year(), term=current_term()):
        class_data = {}
        classes = self._db.classlist.search({ 'student_id': self.id, 'year': year, 'term': term},
            projection=['class_id', 'class_number', 'properties', 'preferences', 'strengths', 'status'],
            )
        for r in classes:
            # we could also group instructor names and match_dates from classes, but not necessary right now
            r['id'] = r['class_id'] # just so we don't get confused
            r['next_match_date'] = next_match_date(r['class_id'])
            if not r['preferences']:
                r['preferences'] = self.preferences
                r['strengths'] = self.strengths
            class_data[r["class_number"]] = r
        return class_data

    def _group_data(self, year=current_year(), term=current_term()):
        group_data = {}
        groups = self._db.grouplist.search({'student_id': self.id, 'year': year, 'term': term}, projection='group_id')
        for gid in groups:
            g = self._db.groups.lucky({'id': gid},
                projection=['id', 'group_name', 'class_number', 'visibility', 'preferences', 'strengths', 'editors', 'max'])
            g['group_id'] = g['id'] # just so we don't get confused
            members = list(students_in_group(gid))
            g['count'] = len(members)
            g['members'] = sorted([[_str(s.get(k,"")) for k in ['preferred_name','preferred_pronouns','year','kerb']] for s in members])
            token = generate_timed_token({'kerb':self.kerb, 'group_id': str(g['id'])}, 'invite')
            g['invite'] = url_for(".accept_invite", token=token, _external=True, _scheme="http" if debug_mode() else "https")
            group_data[g['class_number']] = g
        return group_data

class Instructor(UserMixin):
    def __init__(self, kerb):
        if not kerb:
            raise ValueError("kerb required to create new student")
        self._db = getdb()
        self.kerb = kerb
        assert self.kerb

    @property
    def is_student(self):
        return False

    @property
    def is_instructor(self):
        return True

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
        return True if getattr(self, 'kerb', "") else False

    @property
    def is_admin(self):
        return self.kerb and is_admin(self.kerb)

    @property
    def is_anonymous(self):
        return False if getattr(self, 'kerb', "") else True

    @property
    def get_id(self):
        return lambda: getattr(self, 'kerb', None)

class AnonymousUser(AnonymousUserMixin):
    @property
    def is_student(self):
        return False

    @property
    def is_instructor(self):
        return False

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

test_timezones = ["US/Samoa", "US/Hawaii", "Pacific/Marquesas", "America/Adak", "US/Alaska", "US/Pacific", "US/Mountain",
                  "US/Central", "US/Eastern", "Brazil/East", "Canada/Newfoundland", "Brazil/DeNoronha", "Atlantic/Cape_Verde", "Iceland",
                  "Europe/London", "Europe/Paris", "Europe/Athens", "Asia/Dubai", "Asia/Baghdad", "Asia/Jerusalem", "Asia/Tehran",
                  "Asia/Karachi", "Asia/Kolkata", "Asia/Katmandu", "Asia/Dhaka", "Asia/Rangoon", "Asia/Jakarta", "Asia/Singapore", "Australia/Eucla",
                  "Asia/Seoul", "Asia/Tokyo", "Australia/Adelaide", "Australia/Sydney", "Australia/Lord_Howe",
                  "Pacific/Norfolk", "Pacific/Auckland", "Pacific/Chatham", "Pacific/Tongatapu", "Pacific/Kiritimati"]

test_departments = ['6', '8', '7', '20', '5', '9', '10', '1', '3', '2', '16',  '14', '12', '4', '11', '22', '24', '21', '17']

big_classes = [ '18.02', '18.03', '18.06', '18.404', '18.600' ]

def generate_test_population(num_students=300,max_classes=6):
    """ generates a random student population for testing (destorys existing test data) """
    from random import randint
    from . import db
    pronouns = { 'female': 'she/her', 'male': 'he/him', 'non-binary': 'they/them' }

    def rand(x):
        return x[randint(0,len(x)-1)]

    def wrand(x):
        for i in range(len(x)):
            if randint(0,i+2) == 0:
                return x[i]
        return rand(x)

    def rand_strength():
        if randint(0,2):
            return 3
        else:
            if randint(0,2):
                return randint(2,4)
            else:
                return 1 if randint(0,1) else 5

    choice = input("Are you sure? This will destroy the existing test database? [y/n] ").lower()
    if not choice or choice[0] != 'y':
        print("No changes made.")
        return
    db.test_messages.delete({}, resort=False)
    db.test_students.delete({}, resort=False)
    db.test_groups.delete({}, resort=False)
    db.test_classlist.delete({}, resort=False)
    db.test_grouplist.delete({}, resort=False)
    print("Deleted all records in test_students, test_groups, test_classlist, and test_grouplist.")
    year, term = current_year(), current_term()
    blank_student = { col: default_value(db.test_students.col_type[col]) for col in db.test_students.col_type }
    S = []
    for n in range(num_students):
        s = blank_student.copy()
        s['kerb'] = "test%03d" % n
        firstname = db.names.random()
        name = db.math_adjectives.random({'firstletter': firstname[0]}).capitalize() + " " + firstname.capitalize()
        s['preferred_name'] = s['full_name'] = name
        s['year'] = rand(year_options)[0] if randint(0,9) else None
        if ( s['year'] == 1 ):
            departments = [] if randint(0,4) else ['18']
        elif ( s['year'] == 5 ):
            departments = ['18']
        else:
            departments = ['18'] if randint(0,2) else [wrand(test_departments)]
        if len(departments) and randint(0,2) == 2:
            departments.append(wrand(test_departments))
            if randint(0,4) == 2:
                departments.append(wrand(test_departments))
        s['departments'] = list(set(departments))
        s['gender'] = db.names.lookup(firstname,projection="gender") if randint(0,1) == 0 else None
        if s['gender']:
            if randint(0,2) == 0:
                s['preferred_pronouns'] = pronouns[s['gender']]
        else:
            if randint(0,9) == 0:
                s['preferred_pronouns'] = "they/them"
        s['location'] = 'near' if randint(0,2) == 0 else rand(location_options[1:])[0]
        s['timezone'] = DEFAULT_TIMEZONE_NAME if s['location'] == 'near' else rand(test_timezones)
        hours = [False for i in range(168)]
        n = 0
        while n < 168:
            start = n + randint(0,23)
            if start >= 168:
                break
            end = randint(start+1,start+8)
            if end >= 168:
                end = 168
            for i in range(start,end):
                hours[i] = True
            n = end+1
        s['hours'] = hours
        prefs, strengths = {}, {}
        for p in student_preferences:
            if not p.endswith("_affinity"):
                if randint(0,1):
                    prefs[p] = rand(student_preferences[p]['options'])[0]
                    strengths[p] = randint(1,5)
                    if p == "forum" and p in prefs and prefs[p] == "in-person":
                        prefs[p] = "video";
            else:
                q = p.split('_')[0]
                if q in student_affinities and s[q]:
                    prefs[p] = rand(student_preferences[p]['options'])[0]
                    strengths[p] = randint(1,5)
        s['preferences'] = prefs
        s['strengths'] = strengths
        S.append(s)
    db.test_students.insert_many(S, resort=False)
    S = []
    for s in db.test_students.search(projection=3):
        student_id = s["id"]
        if s['year'] in [1,2] and randint(0,3):
            classes = [db.classes.lucky({'year': year, 'term': term, 'class_number': rand(big_classes)}, projection=['id', 'class_number'])]
        else:
            classes = [db.classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])]
            while s['year'] in [3,4,5] and classes[0]['class_number'].split('.')[1][0] == '0':
                classes = [db.classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])]
        if randint(0,2):
            classes.append(db.classes.random({'year': year, 'term': term}, projection=['id', 'class_number']))
            for m in range(2,max_classes):
                if randint(0,2*m-2):
                    break;
                classes.append(db.classes.random({'year': year, 'term': term}, projection=['id', 'class_number']))
        for i in range(len(classes)):
            prefs, strengths, props = {}, {}, {}
            for p in student_class_properties:
                if randint(0,1):
                    props[p] = rand(student_class_properties[p]['options'])[0]
                    strengths[p] = randint(1,5)
                    if randint(0,1):
                        pa = p + "_affinity"
                        prefs[pa] = rand(student_preferences[pa]['options'])[0]
                        strengths[pa] = rand_strength()
            for p in student_preferences:
                if not p.endswith("_affinity"):
                    if p in s['preferences']:
                        if randint(0,2):
                            prefs[p] = s['preferences'][p]
                            strengths[p] = s['strengths'][p]
                        else:
                            prefs[p] = rand(student_preferences[p]['options'])[0]
                            strengths[p] = rand_strength()
                    elif randint(0,2) == 0:
                        prefs[p] = rand(student_preferences[p]['options'])[0]
                        strengths[p] = rand_strength()
            for p in student_affinities:
                pa = p + "_affinity"
                if pa in s['preferences'] and randint(0,2):
                    prefs[p] = s['preferences'][pa]
                    strengths[p] = s['strengths'][pa]
                elif randint(0,2) == 0:
                    prefs[pa] = rand(student_preferences[pa]['options'])[0]
                    strengths[pa] = randint(1,5)
            c = { 'class_id': classes[i]['id'], 'student_id': student_id, 'kerb': s['kerb'], 'class_number': classes[i]['class_number'],
                  'year': year, 'term': term, 'preferences': prefs, 'strengths': strengths, 'properties': props }
            S.append(c)
    db.test_classlist.insert_many(S, resort=False)
    S = []
    for c in db.classes.search({'year': year, 'term': term}, projection=['id', 'class_number']):
        kerbs = list(db.test_classlist.search({'class_id':c['id']},projection='kerb'))
        n = len(kerbs)
        creators, names = set(), set()
        for i in range(n//10):
            name = db.plural_nouns.random()
            name = db.positive_adjectives.random({'firstletter':name[0]}).capitalize() + " " + name.capitalize()
            if name in names:
                continue
            creator = rand(kerbs)
            if creator in creators:
                continue
            s = db.test_students.lookup(creator,projection=["preferences", "strengths"])
            prefs = { k: s['preferences'][k] for k in s.get('preferences',{}) if not k.endswith('affinity') }
            strengths = { k: s['strengths'][k] for k in s.get('strengths',{}) if not k.endswith('affinity') }
            maxsize = max_size_from_prefs(prefs)
            g = {'class_id': c['id'], 'year': year, 'term': term, 'class_number': c['class_number'],
                 'group_name': name, 'visibility': 3, 'preferences': prefs, 'strengths': strengths, 'editors': [creator], 'max': maxsize }
            creators.add(creator)
            names.add(name)
            S.append(g)
    if ( S ):
        db.test_groups.insert_many(S, resort=False)
        S = []
        for g in db.test_groups.search(projection=3):
            gid, cid, cnum, eds = g['id'], g['class_id'], g['class_number'], g['editors']
            members = []
            for k in eds:
                sid = db.test_students.lookup(k,projection="id")
                S.append({'class_id': cid, 'student_id': sid, 'kerb': k, 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                members.append(student_id)
            while True:
                if g['max'] and len(members) >= g['max']:
                    break
                s = rand(list(db.test_classlist.search({'class_id': cid},projection=["student_id", "kerb"])))
                if s['student_id'] in members:
                    break
                S.append({'class_id': cid, 'student_id': s['student_id'], 'kerb': s['kerb'], 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                db.test_classlist.update({'class_id': cid, 'student_id': s['student_id']}, {'status': 1}, resort=False)
                members.append(s['student_id'])
                if randint(0,len(members)-1):
                    break
        db.test_grouplist.insert_many(S, resort=False)
