import datetime
from . import app
from .app import debug_mode, livesite, send_email
from .dbwrapper import getdb, students_in_classes, students_in_class, students_groups_in_class, students_in_group, count_rows
from flask import url_for
from flask_login import UserMixin, AnonymousUserMixin
from pytz import timezone, UnknownTimeZoneError
from .utils import (
    DEFAULT_TIMEZONE_NAME,
    DEFAULT_TIMEZONE,
    current_year,
    current_term,
    hours_from_default,
    flash_announce,
    flash_notify,
    flash_error,
    validate_class_name,
    )
from .group import generate_group_name
from .token import generate_timed_token
from .match import rank_groups
from psycodict import DelayCommit

strength_options = ["no preference", "nice to have", "weakly preferred", "preferred", "strongly preferred", "required"]
default_strength = "preferred" # only relevant when preference is set to non-emtpy/non-zero value

# only student cols in this list will be visible to other group members -- note web pages depend on the order of these!
member_row_cols = [ 'preferred_name', 'preferred_pronouns', 'departments', 'year', 'kerb' ]

# only student cols in this list will be visible to instructors -- note web pages depend on the order of these!
student_row_cols = [
    'full_name',
    'preferred_name',
    'preferred_pronouns',
    'departments',
    'year',
    'kerb',
    'status',
    'group_name',
    'visibility',
    'size',
    'max',
]

student_welcome = """<b>Welcome to pset partners!</b>
To begin, enter your preferred name and any other personal details you care to share.<br>
Then select your location, timezone, the math classes you are taking this term, and hours of availability (include partial hours).<br>
You can explore your options for finding pset partners using the Preferences and Partners buttons."""

instructor_welcome = "<b>Welcome to pset partners!</b>"

permission_request = """
There is a student in {class_numbers} looking to join a pset group whose schedule and preferences appear to be a good fit for <b>{group_name}</b>.<br><br>
To you are happy to add this student to your group, please visit<br>&nbsp;&nbsp;<a href="{approve_link}">{approve_link}</a>.<br><br>
If your group is no longer accepting new members, visit<br>&nbsp;&nbsp;<a href="{deny_link}">{deny_link}</a>.
"""

signature = "<br><br>Your friends at psetpartners@mit.edu.<br>"

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
  ( '21E', 'Humanities and Engineering'),
  ( '21G', 'Global Studies and Languages'),
  ( '21H', 'History'),
  ( '21L', 'Literature'),
  ( '21M', 'Music and Theater Arts'),
  ( '21S', 'Humanities and Science'),
  ( '21W', 'Writing'),
  ( '22', 'Nuclear Science and Engineering'),
  ( '24', 'Linguistics and Philosophy'),
  ( 'CMS', 'Comparative Media Studies'),
  ( 'HST', 'Health Sciences and Technology'), 
  ( 'IDS', 'Data, Systems, and Society'),
  ( 'IMES', 'Medical Engineering and Science'),
  ( 'MAS', 'Media Arts and Sciences'),
  ( 'SCM', 'Supply Chain Management'),
  ( 'STS', 'Science, Technology, and Society'),
  ( 'WGS', "WGS Women's and Gender Studies"),
  ]
course_number_index = { departments_options[i][0]: i for i in range(len(departments_options)) }

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
    ("far", "not near MIT"),
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
    ("1", "early, soon after the problem set is posted"),
    ("2", "midway, at least 3 days before the pset is due"),
    ("3", "late, a few days before the pset is due"),
    ]

style_options = [
    ("1", "solve the problems together"),
    ("2", "discuss strategies, help each other when stuck"),
    ("3", "work independently but check answers"),
    ]

forum_options = [
    ("text", "text (e.g. Slack or Zulip)"),
    ("video", "video (e.g. Zoom)"),
    ("in-person", "in person"),
    ]

size_options = [
    ("2", "2 students"),
    ("3", "3-4 students"),
    ("5", "5-8 students"),
    ("9", "more than 8 students"),
    ]

commitment_options = [
    ("1", "I'm still shopping and/or not registered"),
    ("2", "Other courses might be a higher priority"),
    ("3", "This course is a top priority for me"),
    ]

confidence_options = [
    ("1", "This will be all new for me"),
    ("2", "I have seen some of this material before"),
    ("3", "I am quite comfortable with this material"),
    ]

departments_affinity_options = [
    ("1", "someone else in one of my departments"),
    ("2", "only students in one of my departments"),
    ("3", "students in many departments"),
    ]

year_affinity_options = [
    ("1", "someone else in my year"),
    ("2", "only students in my year"),
    ("3", "students in multiple years"),
    ]

gender_affinity_options = [
    ("1", "someone else with my gender identity"),
    ("2", "only students with my gender identity"),
    ("3", "a diversity of gender identities"),
    ]

commitment_affinity_options = [
    ("1", "someone else with my level of commitment"),
    ("2", "only students with my level of commitment"),
    ]

confidence_affinity_options = [
    ("1", "someone else at my comfort level"),
    ("2", "only students at my comfort level"),
    ("3", "a diversity of comfort levels"),
    ]

student_preferences = {
    'start': start_options,
    'style': style_options,
    'forum': forum_options,
    'size': size_options,
    'departments_affinity': departments_affinity_options,
    'year_affinity': year_affinity_options,
    'gender_affinity': gender_affinity_options,
    'commitment_affinity': commitment_affinity_options ,
    'confidence_affinity': confidence_affinity_options,
}

student_affinities = [ 'departments', 'year', 'gender' ]
student_class_affinities = [ 'commitment', 'confidence' ]

student_class_properties = {
    "commitment" : commitment_options,
    "confidence" : confidence_options,
}

countable_options = [
    'hours', 'departments', 'year', 'gender', 'location', 'timezone',
    'start', 'style', 'forum', 'size', 'commitment', 'confidence',
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

def _str(s):
    if isinstance(s,list):
        return ' '.join([str(t) for t in s])
    return str(s) if s is not None else ""

def course_number_key(s):
    return course_number_index.get(s,len(course_number_index))

def class_number_key(s):
    a = s.split('.')
    return (course_number_key(a[0]), '.'.join(a[1:]))

def current_classes(year=current_year(), term=current_term()):
    def format_class_name(r):
        if len(r['class_numbers']) == 1:
            return r['class_name']
        return '/ ' + ' / '.join([c for c in r['class_numbers'] if c != r['class_number']]) + ' ' + r['class_name']

    db = getdb()
    classes = [(r['class_number'], format_class_name(r)) for r in db.classes.search({'active': True, 'year': year, 'term': term}, projection=['class_number', 'class_numbers', 'class_name'])]
    return sorted(classes, key = lambda r: class_number_key(r[0]))

def departments():
    db = getdb()
    departments = [(r['course_number'], r['course_name']) for r  in db.departments.search({}, projection=['course_number', 'course_name'])]
    return sorted(departments, key = lambda x: course_number_key(x[0]))

def is_instructor(kerb):
    db = getdb()
    return True if db.instructors.lookup(kerb) is not None else False

def is_current_instructor(kerb):
    db = getdb()
    return True if db.classes.lucky({'year': current_year(), 'term': current_term(), 'instructor_kerbs': {'$contains':kerb}}, projection="id") is not None else False

def is_student(kerb):
    db = getdb();
    return True if (db.students.lookup(kerb) or db.whitelist.lookup(kerb)) else False

def is_admin(kerb):
    db = getdb()
    return db.admins.lucky({'kerb': kerb})

def send_message(sender, recipient, typ, content):
    db = getdb()
    now = datetime.datetime.now()
    db.messages.insert_many([{'sender_kerb': sender, 'recipient_kerb': recipient, 'type': typ, 'content': content, 'timestamp': now}], resort=False)

def log_event(kerb, event, detail={}, status=0):
    db = getdb()
    db.events.insert_many([{'kerb': kerb, 'timestamp': datetime.datetime.now(), 'status': status, 'event': event, 'detail': detail}], resort=False)

def preferred_name(s):
    if s.get('preferred_name'):
        return s['preferred_name']
    t = s['full_name'].split(',')
    if len(t) == 2:
        return t[1].strip() + ' ' + t[0]
    return s['full_name'] if s.get('full_name') else s['kerb']

def pretty_name(s):
    name = preferred_name(s)
    return "%s (%s)" % (name, s['preferred_pronouns']) if s.get('preferred_pronouns') else name

def email_address(s):
    return s['email'] if s.get('email') else s['kerb'] + '@mit.edu'

def next_match_date(class_id):
    import datetime

    if isinstance(class_id,dict):
        if 'match_dates' in class_id:
            match_dates = class_id['match_dates']
        if 'id' in class_id:
            db = getdb()
            match_dates = db.classes.lucky({'id': class_id['id']}, projection='match_dates')
        if 'class_id' in class_id:
            db = getdb()
            match_dates = db.classes.lucky({'id': class_id['class_id']}, projection='match_dates')
    else:
        db = getdb()
        match_dates = db.classes.lucky({'id': class_id}, projection='match_dates')
    if match_dates:
        today = datetime.datetime.now().date()
        match_dates = [d for d in match_dates if d >= today]
        if match_dates:
            return match_dates[0].strftime("%b %-d")
    return ""

# TODO: Our lives would be simpler if the size pref values where 2,4,8,16 rather than 2,3,5,9 (with the same meaning)
# Then this function could simply return the preferred value if it is <= 8 and None otherwise
def max_size_from_prefs(prefs):
    if not 'size' in prefs:
        return None
    bigger = [int(o[0]) for o in size_options if int(o[0]) > int(prefs['size'])]
    if not bigger:
        return None
    return bigger[0]-1

def get_pref_option(prefs, input, k):
    val = input.get(k,'').strip()
    if not val:
        return
    if not [True for v in student_preferences[k] if v[0] == val]:
        raise ValueError("Invalid option %s for %s " % (val, k))
    prefs[k] = val

def student_counts(iter, opts):
    counts = { opt: {} for opt in opts if opt in countable_options and not opt in ['hours' 'departments'] }
    count_hours = 'hours' in opts
    count_departments = 'departments' in opts
    if count_hours:
        hours = [0 for i in range(168)]
    if count_departments:
        departments = {}
    count_status = 'status' in opts
    if count_status:
        status = {}
    pref_opts = [ opt for opt in counts if opt in student_preferences ]
    prop_opts = [ opt for opt in counts if opt in student_class_properties ]
    base_opts = [ opt for opt in counts if opt not in pref_opts and opt not in prop_opts ]
    n = 0
    offs = {}
    for r in iter:
        if count_hours:
            if not r['timezone'] in offs:
                offs[r['timezone']] = hours_from_default(r['timezone'])
            off = offs[r['timezone']]
            for i in range(168):
                if r['hours'][i]:
                    hours[(i-off) % 168] += 1
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
        if count_status:
            val = r.get('status',0)
            status[val] = status[val]+1 if val in status else 1
        n += 1
    if count_hours:
        counts['hours'] = hours
    if count_departments:
        counts['departments'] = departments
    if count_status:
        counts['status'] = status
    counts["students"] = n
    return counts

def student_visibility_counts(iter):
    """
    Returns students counts within a class according to status and group visibility
    """
    vcounts = {}
    for g in iter:
        v = g['visibility']
        vcounts[v] = vcounts[v]+g['size'] if v in vcounts else g['size']
    return vcounts

def group_visibility_counts(class_number, year=current_year(), term=current_term()):
    """ 
    Returns two dictionaries of group counts for the specified class, indexed by visibility (set class_number='' for all classes.
    The first dictionary includes all groups, the second only includes groups to which members can be added (size < max)
    """
    db = getdb()
    vcounts, wcounts = {}, {}
    if class_number:
        for g in db.groups.search({'year': year, 'term': term, 'class_number': class_number}, projection=['visibility','size','max']):
            v = g['visibility']
            vcounts[v] = vcounts[v]+1 if v in vcounts else 1
            if not g.get('max') or not g.get('size') or g['size'] < g['max']:
                wcounts[v] = wcounts[v]+1 if v in wcounts else 1
    else:
        for g in db.groups.search({'year': year, 'term': term}, projection=['visibility','size','max']):
            v = g['visibility']
            vcounts[v] = vcounts[v]+1 if v in vcounts else 1
            if not g.get('max') or not g.get('size') or g['size'] < g['max']:
                wcounts[v] = wcounts[v]+1 if v in wcounts else 1
    return vcounts, wcounts

def get_counts(classes, opts, year=current_year(), term=current_term()):
    """ 
    Returns a dictionary of count dictionaries indexed by class numbers in classes ('' indicates totals across all classes).
    Each count dictionary includes keys for student preferences and properties, as well as counts of classes and groups,
    as well as students in those classes and gorups, visibility and capacity counts, and the next_match_date for each class.
    """
    db = getdb();
    counts = {}
    if '' in classes:
        counts[''] = student_counts(students_in_classes(year, term), opts)
        counts['']['classes'] = count_rows('classes', {'active':True, 'year': year, 'term': term})
        counts['']['students_classes'] = count_rows('classlist', {'year': year, 'term': term})
        counts['']['groups'] = count_rows('groups', {'year': year, 'term': term})
        counts['']['students_groups'] = count_rows('grouplist', {'year': year, 'term': term})
        counts['']['visibility'], counts['']['capacity'] = group_visibility_counts('')
        counts['']['students_visibility'] = student_visibility_counts(db.groups.search({'year': year, 'term': term}, projection=["size", "visibility"]))
    for c in classes:
        if c:
            cid = db.classes.lucky({'class_number': c, 'year': year, 'term': term}, projection="id")
            counts[c] = student_counts(students_in_class(cid), opts)
            counts[c]['groups'] = count_rows('groups',{'class_id': cid})
            counts[c]['students_groups'] = count_rows('grouplist', {'class_id': cid})
            counts[c]['next_match_date'] = next_match_date(cid)
            counts[c]['visibility'], counts[c]['capacity'] = group_visibility_counts(c, year=year, term=term)
            counts[c]['students_visibility'] = student_visibility_counts(db.groups.search({'class_id': cid}, projection=["size", "visibility"]))
            counts[c]['class_id'] = cid
    return counts

# The *_row functions determine how data is passed to the client, we avoid using dictionaries both to save space and to control
# exactly what the client can see (e.g. what students can see about group members and what instructors can see about students)
# The downside is that the javascript depends on the order of the columns.  We pass everything as strings to avoid json

def group_row(g, n):
    p = [_str(g['preferences'].get(k,"")) for k in ["start", "style", "forum"]] if g.get('preferences') else ["", "", ""]
    return [str(g['id']), g['group_name'], p[0], p[1], p[2], str(n), _str(g.get("max","")), _str(g.get("visibility",0))]

def member_row(s):
    return [_str(s.get(k,"")) for k in member_row_cols]

def student_row(s):
    return [_str(s.get(k,"")) for k in student_row_cols]

def class_groups(class_number, opts, year=current_year(), term=current_term(), visibility=None, instructor_view=False):
    db = getdb()
    G = []
    mv = 0 if instructor_view else 3
    for g in db.groups.search({'class_number': class_number, 'year': year, 'term': term, 'visibility' : {'$gte': mv} }, projection=['id']+[o for o in opts if o in db.groups.col_type]):
        members = list(students_in_group(g['id']))
        r = group_row(g, len(members))
        if 'members' in opts and (g['visibility'] >= mv):
            r.append(sorted([member_row(s) for s in members]))
        G.append(r)
    return sorted(G,key=lambda r: r[1])

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
    if data["full_name"] == "(null)":
        app.logger.warning("Ignoring displayname (null) for student %s" % kerb);
        data["full_name"] = ""
    if not data.get('timezone'):
        data['timezone'] = DEFAULT_TIMEZONE_NAME
    for pref in list(data["preferences"]):
        if not pref in student_preferences:
            app.logger.warning("Ignoring unknown preference %s for student %s"%(pref,kerb))
            data['preferences'].pop(pref)
        else:
            if not data['preferences'][pref]:
                data['preferences'].pop(pref)
            elif not data["preferences"][pref] in [k[0] for k in student_preferences[pref]]:
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
    if data['departments']:
        data['departments'] = sorted(data['departments'], key=course_number_key)

class Student(UserMixin):
    def __init__(self, kerb, full_name=''):
        if not kerb:
            raise ValueError("kerb required to create new student")
        if full_name == "(none)":
            app.log_warning("Ignoring displayname (null) for kerb %s" % kerb);
            full_name = ""
        self._db = getdb()
        data = self._db.students.lookup(kerb, projection=3)
        if data is None:
            data = { col: None for col in self._db.students.col_type }
            data['kerb'] = kerb
            data['full_name'] = full_name
            data['preferred_name'] = preferred_name(data)
            data['id'] = -1
            data['new'] = True
            now = datetime.datetime.now()
            data['last_login'] =  now
            data['last_seen'] = now
            if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
                send_message("", kerb, "welcome", student_welcome)
            log_event (kerb, 'new')
        else:
            data['new'] = False
            if not data.get('full_name'):
                data['full_name'] = full_name
            data['preferred_name'] = preferred_name(data)
        self.dual_role = is_current_instructor(kerb)
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

    @property
    def pretty_name(self):
        return pretty_name(self.__dict__)

    @property
    def email_address(self):
        return email_address(self.__dict__)

    @property
    def stale_login(self):
        if livesite():
            return False # we can use this to force new logins if needed
        elif not self.new:
            r = self._db.globals.lookup('sandbox')
            return not self.last_login or self.last_login < r['timestamp']
        else:
            return False

    def seen(self):
        now = datetime.datetime.now()
        if self.last_seen is None or self.last_seen + datetime.timedelta(hours=1) < now:
            self.last_seen = now
            self._db.students.update({'kerb': self.kerb},{'last_seen':now}, resort=False)
            log_event (self.kerb, 'seen')

    def login(self):
        self._db.students.update({'kerb': self.kerb},{'last_login':datetime.datetime.now()}, resort=False)
        log_event (self.kerb, 'login')

    def send_message(self, sender, typ, content):
        send_message(sender, self.kerb, typ, content)

    def flash_pending(self):
        for msg in self._db.messages.search({'recipient_kerb': self.kerb, 'read': None}, projection=3):
            content = ''.join(msg['content'].split('`')) # remove any backticks since we are using them as a separator
            flash_announce("%s`%s" % (msg['id'], content))

    def acknowledge(self, msgid=None):
        if msgid is None:
            self._db.messages.update({'recipient_kerb': self.kerb},{'read':True}, resort=False)
        else:
            self._db.messages.update({'recipient_kerb': self.kerb, 'id': msgid},{'read':True}, resort=False)
        log_event (self.kerb, 'ok')
        return "ok"

    def save(self):
        with DelayCommit(self):
            log_event (self.kerb, 'save', {'student_id': self.id})
            return self._save()

    def join(self, group_id):
        with DelayCommit(self):
            log_event (self.kerb, 'join', {'group_id': group_id})
            return self._join(group_id)

    def leave(self, group_id):
        with DelayCommit(self):
            log_event (self.kerb, 'leave', {'group_id': group_id})
            return self._leave(group_id)

    def poolme(self):
        if not self.class_data:
            return "You do not have any classes listed in your pset partners profile for this term"
        n = 0
        with DelayCommit(self):
            for k in self.class_data:
                c = self.class_data[k]
                if c['status'] == 0 or c['status'] == 3:
                    log_event(self.kerb, 'pool', {'class_id': c['class_id']})
                    flash_notify(self._pool(c['class_id']))
                    n += 1
        if not n:
            "You are either in a group or have already requested a match in all of your classes"
        else:
            log_event (self.kerb, 'poolme', {'count': n})

        return "Done!"

    def pool(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'pool', {'class_id': class_id})
            return self._pool(class_id)

    def unpool(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'unpool', {'class_id': class_id})
            return self._unpool(class_id)

    def matchasap(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'match', {'class_id': class_id})
            return self._matchasap(class_id)

    def matchnow(self, group_id):
        with DelayCommit(self):
            log_event (self.kerb, 'matchnow', {'group_id': group_id})
            return self._matchnow(group_id)

    def create_group(self, class_id, options, public=True):
        with DelayCommit(self):
            log_event (self.kerb, 'create', detail={'class_id': class_id, 'options': options, 'public': public})
            return self._create_group(class_id, options=options, public=public)

    def edit_group(self, group_id, options):
        with DelayCommit(self):
            log_event (self.kerb, 'edit', detail={'group_id': group_id, 'options': options})
            return self._edit_group(group_id, options)

    def accept_invite(self, invite):
        with DelayCommit(self):
            log_event (self.kerb, 'accept', detail={'group_id': invite['group_id'], 'inviter': invite['kerb']})
            return self._accept_invite(invite)

    def approve_request(self, request_id):
        with DelayCommit(self):
            log_event (self.kerb, 'approve', detail={'request_id': request_id})
            return self._approve_request(request_id)

    def deny_request(self, request_id):
        with DelayCommit(self):
            log_event (self.kerb, 'deny', detail={'request_id': request_id})
            return self._deny_request(request_id)

    def update_toggle(self, name, value):
        if not name:
            return "no"
        if self.toggles.get(name) == value:
            return "ok"
        self.toggles[name] = value;
        self._save_toggles()
        return "ok"

    def _save_toggles(self):
        self._db.students.update({'id': self.id}, {'toggles': self.toggles}, resort=False)

    def _reload(self):
        """ This function should be called after any updates to classlist or grouplist related this student """
        self.class_data = self._class_data()
        self.classes = sorted(list(self.class_data),key=class_number_key)
        self.group_data = self._group_data()
        self.groups = sorted(list(self.group_data))

    def _save(self):
        if self.departments:
            self.departments = sorted(self.departments, key=course_number_key)
        if self.new:
            assert self._db.students.lookup(self.kerb) is None
            rec = {col: getattr(self, col, None) for col in self._db.students.search_cols if col != "id"}
            self._db.students.insert_many([rec], resort=False)
            self.id = rec["id"]
        else:
            self._db.students.update({"id": self.id, "kerb": self.kerb}, {col: getattr(self, col, None) for col in self._db.students.search_cols}, resort=False)
        if len(set(self.classes)) < len(self.classes):
            raise ValueError("Duplicates in class list %s" % self.classes)
        year = current_year()
        term = current_term()
        class_ids = set()
        now = datetime.datetime.now()
        for class_number in self.classes:
            query = { 'class_number': class_number, 'year': year, 'term': term}
            class_id = self._db.classes.lucky(query, projection='id')
            if class_id is None:
                raise ValueError("Class %s is not listed in the pset partners list of classes for this term." % class_number)
            oldr = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id})
            if oldr:
                r = oldr.copy()
            else:
                r = { 'class_id': class_id, 'year': year, 'term': term, 'class_number': class_number,
                      'student_id': self.id, 'kerb': self.kerb, 'status': 0, 'status_timestamp': now }
            # if user was just added to the class (e.g. via an invitation) we may not have any class_data for it
            if class_number in self.class_data:
                r['properties'] = self.class_data[class_number].get('properties', {})
                r['preferences'] = self.class_data[class_number].get('preferences', {})
                r['strengths'] = self.class_data[class_number].get('strengths', {})
            else: 
                r['properties'], r['preferences'], r['strengths'] = {}, {}, {}
                r
            if oldr:
                if r != oldr:
                    self._db.classlist.update(oldr,r)
                    log_event (self.kerb, 'edit', detail={'class_id': class_id})
            else:
                self._db.classlist.insert_many([r])
                n = len(list(self._db.classlist.search({'class_id': class_id},projection='id')))
                self._db.classes.update({'id': class_id}, {'size': n})
                log_event (self.kerb, 'add', detail={'class_id': class_id})
            class_ids.add(class_id)
        for class_id in self._db.classlist.search ({'student_id': self.id, 'year': year, 'term': term}, projection="class_id"):
            if class_id not in class_ids:
                group_id = self._db.grouplist.lucky({'class_id': class_id, 'student_id': self.id},projection='group_id')
                if group_id is not None:
                    class_numbers = self._db.classes.lucky({'id': class_id}, projection='class_numbers')
                    group_name = self._db.groups.lucky({'id': group_id}, projection='group_name')
                    flash_error("You were not removed from the class <b>%s</b> because you are currently a member of the pset group <b>%s</b> in that class.  Please leave the group first." % (' / '.join(class_numbers), group_name))
                    log_event(self.kerb, 'drop', detail={'class_id': class_id, 'group_id': group_id}, status=-1)
                    continue
                self._db.classlist.delete({'class_id': class_id, 'student_id': self.id})
                n = len(list(self._db.classlist.search({'class_id': class_id},projection='id')))
                self._db.classes.update({'id': class_id}, {'size': n})
                log_event (self.kerb, 'drop', detail={'class_id': class_id})
        self._reload()
        return "Changes saved!"

    def _accept_invite(self, invite):
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
        gid = self._db.grouplist.lucky({'class_id': g['class_id'], 'year': g['year'], 'term': g['term'], 'student_id': self.id}, projection='group_id')
        if gid is not None:
            if gid != g['id']:
                raise ValueError("You are currently a member of a different group in <b>%s</b>\n.  To accept this invitation you need to leave your current group first." % ' / '.join(g['class_numbers']))
        if g['size'] >= g['max']:
            raise ValueError("This groups is currently full (but if the group increases its size limit you can try again).")
        if not g['class_number'] in self.classes:
            self.classes.append(g['class_number'])
            self.save()
        elif self.class_data[g['class_number']]['status'] == 5:
            raise ValueError("Unable to process invitation, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(g['class_numbers']))
        if gid == g['id']:
            self.send_message('', 'accepted', "You are already a member of the <b>%s</b> pset group <b>%s</b>.  Hello again!" % (' / '.join(g['class_numbers']), g['group_name']))
        else:
            self.join(g['id'])
            self.send_message('', 'accepted', "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (' / '.join(g['class_numbers']), g['group_name']))
        self.update_toggle('ct', g['class_number'])
        self.update_toggle('ht', 'partner-header')
        return "ok"

    def _join(self, group_id):
        g = self._db.groups.lucky({'id': group_id}, projection=3)
        if not g:
            app.logger.warning("User %s attempted to join non-existent group %s" % (self.kerb, group_id))
            raise ValueError("Group not found in database")
        c = g['class_number']
        if not c in self.classes:
            app.logger.warning("User %s attempted to join group %s in class %s not in their class list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in any of your classes for this term")
        if c in self.groups:
            app.logger.warning("User %s attempted to join group %s in class %s but is already a member of group %s" % (self.kerb, group_id, c, self.group_data[c]['id']))
            raise ValueError("You are already a member of the group %s in class %s, you must leave that group before joining a new one." % (self.group_data[c]['group_name'], c))
        if self.class_data[c]['status'] == 5:
            app.logger.warning("User %s attempted to join group %s in class %s but is currently being matched" % (self.kerb, group_id, c))
            raise ValueError("Unable to join group, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(g['class_numbers']))
        return self.__join(g)

    def _matchnow(self, group_id):
        g = self._db.groups.lucky({'id': group_id}, projection=3)
        if not g:
            app.logger.warning("User %s attempted to join non-existent group %s" % (self.kerb, group_id))
            raise ValueError("Group not found in database")
        c = g['class_number']
        if not c in self.classes:
            app.logger.warning("User %s attempted to join group %s in class %s not in their class list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in any of your classes for this term")
        if c in self.groups:
            app.logger.warning("User %s attempted to join group %s in class %s but is already a member of group %s" % (self.kerb, group_id, c, self.group_data[c]['id']))
            raise ValueError("You are already a member of the group %s in class %s, you must leave that group before joining a new one." % (self.group_data[c]['group_name'], c))
        if self.class_data[c]['status'] == 5:
            app.logger.warning("User %s attempted to join group %s in class %s but is currently being matched" % (self.kerb, group_id, c))
            raise ValueError("Unable to join group, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(g['class_numbers']))
        if g['visibility'] != 2:
            app.logger.warning("User %s attempted to join group %s in class %s but the group does not allow automatic membership" % (self.kerb, group_id, c))
            raise ValueError("Unable to join group in <b>%s</b>, this group no longer allows automatic membership. You may be able to try again with a different group." % ' / '.join(g['class_number']))
        if g['max'] and g['size'] >= g['max']:
            app.logger.warning("User %s attempted to join group %s in class %s but the group no longer has space available." % (self.kerb, group_id, c))
            raise ValueError("Unable to join group in <b>%s</b> as there is no longer a slot available.  You may be able to try again with a different group." % ' / '.join(g['class_numbers']))
        return self.__join(g)

    def _matchasap(self, group_id):
        g = self._db.groups.lucky({'id': group_id}, projection=3)
        if not g:
            app.logger.warning("User %s attempted to match non-existent group %s" % (self.kerb, group_id))
            raise ValueError("Group not found in database")
        c = g['class_number']
        if not c in self.classes:
            app.logger.warning("User %s attempted to match group %s in class %s not in their class list" % (self.kerb, group_id, c))
            raise ValueError("Group not found in any of your classes for this term")
        if c in self.groups:
            app.logger.warning("User %s attempted to match group %s in class %s but is already a member of group %s" % (self.kerb, group_id, c, self.group_data[c]['id']))
            raise ValueError("You are already a member of the group %s in class %s, you must leave that group before joining a new one." % (self.group_data[c]['group_name'], c))
        now = datetime.datetime.now()
        if self.class_data[c]['status'] == 5 or (self.class_data[c]['status'] == 3 and self.class_data[c]['status_timestamp'] + datetime.timedelta(days=1) > now):
            app.logger.warning("User %s attempted to match group %s in class %s but is currently being matched in that class" % (self.kerb, group_id, c))
            raise ValueError("Unable to request match, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(g['class_numbers']))
        if g['visibility'] != 1:
            app.logger.warning("User %s attempted to match group %s in class %s but the group does not grant membership by permission" % (self.kerb, group_id, c))
            raise ValueError("Unable to join group in <b>%s</b>, this group no longer allows membership by permission. You may be able to try again with a different group." % ' / '.join(g['class_numbers']))
        if g['request_id']:
            app.logger.warning("User %s attempted to match group %s in class %s but the group has not responded to a previous request" % (self.kerb, group_id, c))
            raise ValueError("Unable to join group in <b>%s</b>, this group does not currently allows membership by permission. You may be able to try again with a different group." % ' / '.join(g['class_numbers']))
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 3, 'status_timestamp': now}, resort=False)
        r = {'timestamp': now, 'group_id': g['id'], 'student_id': self.id, 'kerb': self.kerb}
        self._db.requests.insert_many([r])
        self._db.groups.update({'id': group_id}, {'request_id': r['id']})
        approve_link = url_for(".approve_request", request_id=r['id'], _external=True, _scheme="http" if debug_mode() else "https")
        deny_link = url_for(".deny_request", request_id=r['id'], _external=True, _scheme="http" if debug_mode() else "https")
        request_msg = permission_request .format(class_numbers=' / '.join(g['class_numbers']), group_name=g['group_name'], approve_link=approve_link, deny_link=deny_link)
        self._notify_group(g['id'], "A student in %s is looking for a pset group" % ' / '.join(g['class_numbers']), request_msg, '')
        self._reload()
        return "Sent emails requesting a match in %s.  You will be notified as soon as we receive a response (or check back in 24 hours)." % c

    def _approve_request(self, request_id):
        r = self._db.requests.lucky({'id': request_id}, projection=3)
        if not r:
            app.logger.warning("User %s attempted to approve non-existent request %s" %(self.kerb, request_id))
            raise ValueError("Request not found")
        g = self._db.groups.lucky({'id': r['group_id']}, projection=3)
        if not g:
            app.logger.warning("User %s attempted to approve request %s for non-existent group %s" %(self.kerb, r['id'], r['group_id']))
            raise ValueError("Group not found")
        if not self._db.grouplist.lucky({'group_id': g['id'], 'student_id': self.id}):
            app.logger.warning("User %s attempted to approve request %s for group %s that they no longer belong to" %(self.kerb, r['id'], r['group_id']))
            raise ValueError("You are not a member of this group")
        if g['request_id'] != r['id']:
            return "This request has already been handled by you or another group member, but thanks for responding!"
        s = self._db.classlist.lucky({'class_id': g['class_id'], 'student_id': r['student_id']})
        if not s or s['status'] not in [2,3]:
            return "It appears the student requesting permission is no longer looking for a partner, but thanks for responding!"
        s = self._db.students.lucky({'id': r['student_id']})
        assert s
        now = datetime.datetime.now()
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': r['student_id']}, {'status': 1, 'status_timestamp': now})
        self._db.grouplist.insert_many([{'class_id': g['class_id'], 'class_number': g['class_number'], 'year': g['year'], 'term': g['term'],
                                         'group_id': g['id'], 'student_id': r['student_id'], 'kerb': r['kerb']}])        
        self._db.groups.update({'id': r['group_id'], 'request_id': r['id']}, {'request_id': None})
        hello_msg1 = "%s joined your pset group <b>%s</b> in <b>%s</b>!" % (pretty_name(s), g['group_name'], ' / '.join(g['class_numbers']))
        hello_msg2 = "<br>You can contact your new partner at %s." % email_address(s)
        self._notify_group(g['id'], "Say hello to your new pset partner!", hello_msg1+hello_msg2, hello_msg1) # updates group size
        self.send_message('', 'approved', hello_msg1)
        send_message('', r['kerb'], 'approved', "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (' / '.join(g['class_numbers']), g['group_name']))
        self.update_toggle('ct', g['class_number'])
        self.update_toggle('ht', 'partner-header')
        self._reload()
        return "Thanks for responding!"

    def _deny_request(self, request_id):
        r = self._db.requests.lucky({'id': request_id}, projection=3)
        if not r:
            app.logger.warning("User %s attempted to approve non-existent request %s" %(self.kerb, request_id))
            raise ValueError("Request not found")
        g = self._db.groups.lucky({'id': r['group_id']}, projection=3)
        if not g:
            app.logger.warning("User %s attempted to deny request %s for non-existent group %s" %(self.kerb, r['id'], r['group_id']))
            raise ValueError("Group not found")
        if not self._db.grouplist.lucky({'group_id': g['id'], 'student_id': self.id}):
            app.logger.warning("User %s attempted to deny request %s for group %s that they no longer belong to" %(self.kerb, r['id'], r['group_id']))
            raise ValueError("You are not a member of this group")
        if g['request_id'] != r['id']:
            return "This request has already been handled by you or another group member, but thanks for responding!"
        now = datetime.datetime.now()
        self._db.groups.update({'id': r['group_id'], 'request_id': r['id'], 'visibility': 1}, {'request_id': None, 'visibility': 0})
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': r['student_id']}, {'status': 0, 'status_timestamp': now})
        notify_msg = "%s updated the settings for the pset group <b>%s</b> in <b>%s</b>." % (self.preferred_name, g['group_name'], ' / '.join(g['class_numbers']))
        self._notify_group(g['id'], "pset partner notification", notify_msg, notify_msg)
        notify_msg = "The group in %s we contacted on your behalf is no longer accepting new members.  Check your partner options for that class to see if other groups have open slots." % ' / '.join(g['class_numbers'])
        send_message('', r['kerb'], 'denied', notify_msg)
        send_email([email_address(r)], "pset partner notification", notify_msg + signature)
        self.update_toggle('ct', g['class_number'])
        self.update_toggle('ht', 'partner-header')
        self._reload()
        return "Thanks for responding!"

    def __join(self, g):
        now = datetime.datetime.now()
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 1, 'status_timestamp': now}, resort=False)
        r = { k: g[k] for k in  ['class_id', 'class_number', 'year', 'term']}
        r['group_id'], r['student_id'], r['kerb'] = g['id'], self.id, self.kerb
        self._db.grouplist.insert_many([r], resort=False)
        # note that size of group will be updated by _notify_group
        hello_msg1 = "%s joined your pset group <b>%s</b> in <b>%s</b>!" % (self.pretty_name, g['group_name'], ' / '.join(g['class_numbers']))
        hello_msg2 = "<br>You can contact your new partner at %s." % self.email_address
        self._notify_group(g['id'], "Say hello to your new pset partner!", hello_msg1+hello_msg2, hello_msg1) # updates group size
        self._reload()
        return "Welcome to <b>%s</b>!" % g['group_name']

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
        now = datetime.datetime.now()
        r = self._db.grouplist.lucky({'group_id': group_id, 'student_id': self.id})
        r['timestamp'] = now
        self._db.grouplistleft.insert_many([r], resort=False)
        self._db.grouplist.delete({'group_id': group_id, 'student_id': self.id}, resort=False)
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 0, 'status_timestamp': now}, resort=False)
        msg = "You have been removed from the group <b>%s</b> in <b>%s</b>." % (g['group_name'], c)
        if not self._db.grouplist.lucky({'group_id': group_id}, projection="id"):
            self._db.groups.delete({'id': group_id}, resort=False)
            msg += " You were the only member, so the group was disbanded."
        else:
            # note that size of group will be updated by _notify_group
            leave_msg = "%s (kerb=%s) left the pset group <b>%s</b> in <b>%s</b>." % (self.preferred_name, self.kerb, g['group_name'], ' / '.join(g['class_numbers']))
            self._notify_group(group_id, "pset partner notification", leave_msg, leave_msg)
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
            raise ValueError("You are currently a member of the group %s in %s, you must leave that group before joining the match pool." % (self.group_data[c]['group_name'], ' / '.join(self.class_data[c]['class_numbers'])))
        if self.class_data[c]['status'] == 5:
            app.logger.warning("User %s attempted to join the pool for class %s but is currently being matched" % (self.kerb, c))
            raise ValueError("Unable to join pool, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(self.class_data[c]['class_numbers']))
        d = next_match_date(class_id)
        msg = "You are now in the match pool for <b>%s</b> and will be matched on <b>%s</b>." %(' / '.join(self.class_data[c]['class_numbers']), d)
        now = datetime.datetime.now()
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 2, 'status_timestamp': now}, resort=False)
        self._reload()
        return msg

    def _unpool(self, class_id):
        c = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id}, "class_number")
        if not c:
            app.logger.warning("User %s attempted to leave the pool for non-existent class %s" % (self.kerb, class_id))
            raise ValueError("Class not found in database.")
        if not c in self.classes:
            app.logger.warning("User %s attempted to leave the pool for class %s not in their class list" % (self.kerb, class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c in self.groups:
            app.logger.warning("User %s attempted to leave the pool for class %s but is already a member of group %s in that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are currently a member of the group %s in %s, and not in the match pool." % (self.group_data[c]['group_name'], ' / '.join(self.class_data[c]['class_numbers'])))
        if self.class_data[c]['status'] == 5:
            app.logger.warning("User %s attempted to leave the pool for class %s but is currently being matched" % (self.kerb, c))
            raise ValueError("Unable to leave pool, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(self.class_data[c]['class_numbers']))
        if self.class_data[c]['status'] != 2:
            app.logger.warning("User %s attempted to leave the pool for class %s but is not in the match pool for that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are and not in the match pool for %s." % ' / '.join(self.class_data[c]['class_numbers']))
        d = next_match_date(class_id)
        msg = "You have been removed from the match pool for <b>%s</b> on <b>%s</b>." %(' / '.join(self.class_data[c]['class_numbers']), d)
        now = datetime.datetime.now()
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 0, 'status_timestamp': now}, resort=False)
        self._reload()
        return msg

    def _create_group(self, class_id, options=None, public=True):
        c = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id}, projection="class_number")
        if not c:
            raise ValueError("Class not found among your classes.")
        if not c in self.classes:
            app.logger.warning("User %s attempted to join the pool for class %s not in their class list" % (self.kerb, class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c in self.groups:
            app.logger.warning("User %s tried to create a group in class %s but is already a member of group %s in that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are currently a member of the group %s in %s, you must leave that group before creating a new group." % (self.group_data[c]['group_name'], ' / '.join(self.class_data[c]['class_numbers'])))
        if self.class_data[c]['status'] == 5:
            app.logger.warning("User %s attempted to create a group in the class %s but is currently being matched" % (self.kerb, ' / '.join(self.class_data[c]['class_numbers'])))
            raise ValueError("Unable to create group, you are currently in the process of being matched in <b>%s</b>." % ' / '.join(self.class_data[c]['class_numbers']))
        c = self.class_data[c]
        prefs = {}
        for k in ['start', 'style', 'forum', 'size']:
            get_pref_option(prefs, options, k)
        visibility = 3 if public else (int(options['membership'].strip()) if options.get('membership','').strip() else 0)
        editors = [self.kerb] if options.get('editors','').strip() == '1' else []
        strengths = {} # Groups don't have preference strengths right now
        limit = max_size_from_prefs(prefs)
        name = generate_group_name(class_id)
        g = {'class_id': class_id, 'year': current_year(), 'term': current_term(), 'class_number': c['class_number'], 'class_numbers': c['class_numbers'], 'group_name': name,
             'visibility': visibility, 'preferences': prefs, 'strengths': strengths, 'creator': self.kerb, 'editors': editors,
             'size': 1, 'max': limit }
        self._db.groups.insert_many([g], resort=False)
        r = {'class_id': class_id, 'group_id': g['id'], 'student_id': self.id, 'kerb': self.kerb, 'class_number': g['class_number'], 'year': g['year'], 'term': g['term'] }
        self._db.grouplist.insert_many([r], resort=False)
        now = datetime.datetime.now()
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status':1, 'status_timestamp': now})
        self._reload()
        return "Created the group <b>%s</b>!" % g['group_name']

    def _edit_group(self, group_id, options):
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
        prefs = {}
        for k in ['start', 'style', 'forum', 'size']:
            get_pref_option(prefs, options, k)
        visibility = g['visibility']
        if visibility < 3 and options.get('membership','').strip():
            visibility = int(options['membership'].strip());
        editors = g['editors']
        if len(editors) and options.get('editors','').strip() != '1':
            editors = []
        limit = max_size_from_prefs(prefs)
        if any([g['visibility'] != visibility, g['editors'] != editors, g['preferences'] != prefs]):
            self._db.groups.update({'id': group_id}, {'preferences': prefs, 'visibility': visibility, 'editors': editors, 'max': limit}, resort=False)
            notify_msg = "%s updated the settings for the pset group <b>%s</b> in <b>%s</b>." % (self.preferred_name, g['group_name'], ' / '.join(g['class_numbers']))
            self._notify_group(group_id, "pset partner notification", notify_msg, notify_msg)
            self._reload()
            return "Updated the group <b>%s</b>!" % g['group_name']
        else:
            return "No changes made to group <b>%s</b>." % g['group_name']

    def _notify_group(self, group_id, subject, email_message, announce_message):
        """ Notifies members of group and updates group size (so must be called for leave/join!) """
        S = list(students_in_group(group_id,projection=["kerb", "email"]))
        self._db.groups.update({'id': group_id}, {'size': len(S)}, resort=False)
        if not S:
            return
        if announce_message:
            # only message group memebers other than self
            messages = [{'type': 'notify', 'content': announce_message, 'recipient_kerb': s['kerb'], 'sender_kerb': self.kerb} for s in S if s['kerb'] != self.kerb ]
            if messages:
                self._db.messages.insert_many(messages, resort=False)
        if email_message:
            # email all group memebers, including self if applicable (this won't apply if self just left)
            send_email([email_address(s) for s in S], subject, email_message + signature)

    def _class_data(self, year=current_year(), term=current_term()):
        class_data = {}
        classes = self._db.classlist.search({ 'student_id': self.id, 'year': year, 'term': term})
        now = datetime.datetime.now()
        for r in classes:
            r['id'] = r['class_id'] # just so we don't get confused
            c = self._db.classes.lucky({'id': r['class_id']})
            r['class_numbers'] = c['class_numbers']
            r['next_match_date'] = next_match_date(c)
            # timeout expired request status
            if r['status'] == 3 and r['status_timestamp'] + datetime.timedelta(days=1) < now:
                r['status'] = 0
            if r['status'] in [0,2]:
                # Don't make suggestions to students who have left 2 or more groups in the class recently
                S=list(self._db.grouplistleft.search({'class_id':r['class_id'], 'student_id': self.id},projection='timestamp'))
                if len(S) < 2 or S[-2] + datetime.timedelta(hours=19) < now:
                    # Suggest matches for groups with relative compatibility > -162
                    candidates = [g for g in rank_groups(r['class_id'], self.kerb) if g[1] >= 1 and g[2] >= -162]
                    suggest = [g for g in candidates if g[1] == 1]
                    if suggest:
                        r['permission_match'] = suggest[0][0]
                        # print("permission match: %s" % r['permission_match'])
                    suggest = [g for g in candidates if g[1] == 2]
                    if suggest:
                        r['automatic_match'] = suggest[0][0]
                        # print("automatic match: %s" % r['automatic_match'])
                    suggest = [g for g in candidates if g[1] == 3]
                    if suggest:
                        r['public_match'] = suggest[0][0]
                        # print("public match: %s" % r['public_match'])
            class_data[r["class_number"]] = r
        return class_data

    def _group_data(self, year=current_year(), term=current_term()):
        group_data = {}
        groups = self._db.grouplist.search({'student_id': self.id, 'year': year, 'term': term}, projection='group_id')
        for gid in groups:
            g = self._db.groups.lucky({'id': gid},
                projection=['id', 'group_name', 'class_number', 'class_numbers', 'visibility', 'preferences', 'strengths', 'editors', 'max'])
            g['group_id'] = g['id'] # just so we don't get confused
            members = list(students_in_group(gid, member_row_cols))
            g['count'] = len(members)
            g['members'] = sorted([member_row(s) for s in members])
            g['can_edit'] = True if self.kerb in g['editors'] or g['editors'] == [] else False;
            token = generate_timed_token({'kerb':self.kerb, 'group_id': str(g['id'])}, 'invite')
            # Don't freak out on url_for failures, we want to be able to call this interactively for testing purposes
            try:
                g['invite'] = url_for(".accept_invite", token=token, _external=True, _scheme="http" if debug_mode() else "https")
            except RuntimeError:
                print("Unable to create invitation link")
            group_data[g['class_number']] = g
        return group_data

def cleanse_instructor_data(data):
    if data['toggles'] is None:
        data['toggles'] = {}

class Instructor(UserMixin):
    def __init__(self, kerb, full_name=''):
        if not kerb:
            raise ValueError("kerb required to create new instructor")
        self._db = getdb()
        data = self._db.instructors.lookup(kerb)
        if data is None:
            data = { col: None for col in self._db.instructors.col_type }
            data['kerb'] = kerb
            data['full_name'] = full_name
            data['preferred_name'] = preferred_name(data)
            data['id'] = -1
            data['new'] = True
            now = datetime.datetime.now()
            data['last_login'] =  now
            data['last_seen'] = now
            log_event (kerb, 'new', {'instructor':True})
        else:
            data['new'] = False
            if not data.get('full_name'):
                data['full_name'] = full_name
            data['preferred_name'] = preferred_name(data)
        if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
            send_message("", kerb, "welcome", instructor_welcome)
        self.dual_role = is_student(kerb)
        # copy student pofile data if relevant (they might change their name/pronouns)
        if self.dual_role:
            sdata = self._db.students.lookup(kerb)
            for col in ['full_name', 'preferred_name', 'preferred_pronouns', 'email']:
                if col in sdata:
                    data[col] = sdata[col]
        cleanse_instructor_data(data)
        self.__dict__.update(data)
        assert self.kerb
        for col, typ in self._db.instructors.col_type.items():
            if getattr(self, col, None) is None:
                setattr(self, col, default_value(typ))
        self._reload()
        assert self.kerb

    def acknowledge(self, msgid=None):
        if msgid is None:
            self._db.messages.update({'recipient_kerb': self.kerb},{'read':True}, resort=False)
        else:
            self._db.messages.update({'recipient_kerb': self.kerb, 'id': msgid},{'read':True}, resort=False)
        log_event (self.kerb, 'ok')
        return "ok"

    def activate(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'activate', {'class_id': class_id})
            return self._activate(class_id)

    def update_class(self, class_id, data):
        with DelayCommit(self):
            log_event (self.kerb, 'update', {'class_id': class_id, 'data': data})
            return self._update_class(class_id, data)

    def update_toggle(self, name, value):
        if not name:
            return "no"
        if self.toggles.get(name) == value:
            return "ok"
        self.toggles[name] = value;
        self._save_toggles()
        return "ok"

    def _save_toggles(self):
        self._db.instructors.update({'kerb': self.kerb}, {'toggles': self.toggles}, resort=False)

    def _reload(self):
        """ This function should be called after any updates to classlist or grouplist related this student """
        self.class_data = self._class_data()
        self.classes = sorted(list(self.class_data),key=class_number_key)

    def _activate(self, class_id):
        c = self._db.classes.lucky({'id': class_id})
        if c is None:
            app.logger.warning("User %s attempted to activate non-existent class %s" % (self.kerb, class_id))
            raise ValueError("Class not found in database.")
        if not c['class_number'] in self.classes:
            app.logger.warning("User %s attempted to activate a class %s (%s) not in their class list" % (self.kerb, c['class_number'], class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c['owner_kerb'] != self.kerb:
            app.logger.warning("User %s attempted to activate a class %s (%s) for which they are not the owner %s" % (self.kerb, c['class_number'], class_id, c['owner_kerb']))
            raise ValueError("Error activating class, your kerberos id does not match that of the owner of this class -- this should never happen and most likely indicates a bug, please contact psetpartners@mit.edu for assistence.")
        msg = "<b>%s</b> is now active on pset partners!" %(' / '.join(c['class_numbers']))
        self._db.classes.update({'id': class_id}, {'active': True})
        self._reload()
        return msg

    def _update_class(self, class_id, data):
        c = self._db.classes.lucky({'id': class_id})
        if c is None:
            app.logger.warning("User %s attempted to update non-existent class %s" % (self.kerb, class_id))
            raise ValueError("Class not found in database.")
        if not c['class_number'] in self.classes:
            app.logger.warning("User %s attempted to update a class %s (%s) not in their class list" % (self.kerb, c['class_number'], class_id))
            raise ValueError("Class not found in your list of classes for this term.")
        if c['owner_kerb'] != self.kerb:
            app.logger.warning("User %s attempted to update a class %s (%s) for which they are not the owner %s" % (self.kerb, c['class_number'], class_id, c['owner_kerb']))
            raise ValueError("Error updating class, your kerberos id does not match that of the owner of this class -- this is probably a bug, please contact psetpartners@mit.edu.")
        if data.get('remove_kerb'):
            kerb = data['remove_kerb']
            if kerb == self.kerb:
                app.logger.warning("User %s attempted to remove their own kerb from class %s (%s) they own" % (self.kerb, c['class_number'], class_id))
                raise ValueError("Error updating class, owner kerb cannot be removed -- this is probably a bug, please contact psetpartners@mit.edu.")
            if kerb not in c['instructor_kerbs']:
                app.logger.warning("User %s attempted to remove %s from class %s (%s) but this kerb is not present" % (self.kerb, kerb, c['class_number'], class_id))
                raise ValueError("Error removing <b>%s</b> from <b>%s</b>, instructor not found." % (kerb, ' / '.join(c['class_numbers'])))
            c['instructor_kerbs'] = [k for k in c['instructor_kerbs'] if k != kerb]
        if data.get('add_kerb') and data['add_kerb'] not in c['instructor_kerbs']:
            kerb = data['add_kerb']
            if data.get('add_name') and not self._db.instructors.lookup(kerb) and not self._db.students.lookup(kerb):
                if ',' in data['add_name']:
                    s = data['add_name'].split(',')
                    preferred_name = s[1].strip() + ' ' + s[0].strip()
                    full_name = data['add_name']
                else:
                    preferred_name = data['add_name']
                    full_name = ""
                self._db.instructors.insert_many([{'kerb':kerb, 'full_name': full_name, 'preferred_name': preferred_name}], resort=False)
            c['instructor_kerbs'].append(kerb)
        if data.get('class_name'):
            class_name = data['class_name']
            if not validate_class_name(data['class_name']):
                app.logger.warning("User %s attempted change the name of class %s (%s) to invalid name %s" % (self.kerb, c['class_number'], class_id, class_name))
                raise ValueError('The class name "%s" is invalid.' % class_name)
            c['class_name'] = class_name
        if data.get('match_delta'):
            if data['match_delta'].lower() == "none":
                if self._db.classlist.lucky({'class_id': class_id, 'status': 2}):
                    app.logger.warning("User %s attempted to set null match date for class %s (%s) with students in the pool" % (self.kerb, c['class_number'], class_id))
                    raise ValueError("Unable to clear next match date for %s, there are currently students in the pool." % ' / '.join(c['class_numbers']))
                match_dates = []
            else:
                delta = int(data['match_delta'])
                today = datetime.datetime.now().date()
                match_dates = [d for d in c['match_dates'] if d >= today]
                if match_dates == []:
                    if delta < 0:
                        app.logger.warning("User %s attempted to set match date <= today for class %s (%s) with students in the pool" % (self.kerb, c['class_number'], class_id))
                        raise ValueError("Unable to set next match date for %s, invalid date." % ' / '.join(c['class_numbers']))
                    match_dates = [today + datetime.timedelta(days=delta)]
                else:
                    match_dates[0] = match_dates[0]+datetime.timedelta(days=delta)
                    for i in range(1,len(match_dates)):
                        match_dates[i] = match_dates[i-1]+datetime.timedelta(days=7)
            c['match_dates'] = match_dates
        msg = "<b>%s</b> has been updated." % ' / '.join(c['class_numbers'])
        self._db.classes.update({'id': class_id}, c)
        self._reload()
        return msg

    def _class_data(self, year=current_year(), term=current_term()):
        class_data = {}
        classes = list(self._db.classes.search({ 'instructor_kerbs': {'$contains': self.kerb}, 'year': year, 'term': term},projection=3))
        for c in classes:
            c['students'] = sorted([student_row(s) for s in students_groups_in_class(c['id'], student_row_cols)])
            c['groups'] = count_rows('groups', {'class_id': c['id']})
            c['next_match_date'] = next_match_date(c)
            c['instructor_names'] = []
            for k in c['instructor_kerbs']:
                r = self._db.students.lookup(k)
                if not r:
                    r = self._db.instructors.lookup(k)
                c['instructor_names'].append((r['preferred_name'] if r.get('preferred_name') else r.get('full_name',"")) if r else "")
            class_data[c['class_number']] = c
        return class_data

    @property
    def is_student(self):
        return False

    @property
    def is_instructor(self):
        return True

    @property
    def col_type(self):
        return self._db.instructors.col_type

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

    @property
    def pretty_name(self):
        if not self.preferred_name:
            return self.kerb
        if not self.preferred_pronouns:
            return self.preferred_name
        return "%s (%s)" % (self.preferred_name, self.preferred_pronouns)

    @property
    def email_address(self):
        if not self.email:
            return self.kerb + "@mit.edu"
        return self.email

    @property
    def stale_login(self):
        if livesite():
            return False # we can use this to force new logins if needed
        else:
            r = self._db.globals.lookup('sandbox')
            if not self.last_login:
                return False
            return self.last_login < r['timestamp']

    def seen(self):
        now = datetime.datetime.now()
        if self.last_seen is None or self.last_seen + datetime.timedelta(hours=1) < now:
            self.last_seen = now
            self._db.instructors.update({'kerb':self.kerb},{'last_seen':now}, resort=False)
            log_event (self.kerb, 'seen', {'instructor':True})

    def login(self):
        self._db.instructors.update({'kerb':self.kerb},{'last_login':datetime.datetime.now()}, resort=False)
        log_event (self.kerb, 'login', {'instructor':True})

    def send_message(self, sender, typ, content):
        send_message(sender, self.kerb, typ, content)
        self._db.messages.insert_many([{'sender_kerb': sender, 'recipient_kerb': self.kerb, 'type': typ, 'content': content}], resort=False)

    def flash_pending(self):
        for msg in self._db.messages.search({'recipient_kerb': self.kerb, 'read': None}, projection=3):
            content = ''.join(msg['content'].split('`')) # remove any backticks since we are using them as a separator
            flash_announce("%s`%s" % (msg['id'], content))


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


