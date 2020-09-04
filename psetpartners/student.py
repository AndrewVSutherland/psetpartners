import re, datetime
from . import app
from .app import debug_mode, livesite, send_email
from .dbwrapper import getdb, students_in_class, students_groups_in_class, students_in_group, count_rows
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
    flash_info,
    )
from .token import generate_timed_token
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
]

student_welcome = """
<b>Welcome to pset partners!</b>
To begin, enter your preferred name and any other personal details you care to share.<br>
Then select your location, timezone, the math classes you are taking this term, and hours of availability (include partial hours).<br>
You can then explore your options for finding pset partners using the Preferences and Partners buttons.
"""

old_instructor_welcome = """
<b>Welcome to pset partners!</b>
"""

new_instructor_welcome = """
<b>Welcome to pset partners!</b>
"""

signature = "<br><br>Your friends at psetparterners@mit.edu.<br>"

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

CLASS_NUMBER_RE = re.compile(r"^(\d+).(S?)(\d+)([A-Z]*)")
COURSE_NUMBER_RE = re.compile(r"^(\d*)([A-Z]*)")

def _str(s):
    if isinstance(s,list):
        return ' '.join([str(t) for t in s])
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
    return True if db.instructors.lucky({'kerb':kerb},projection="id") else False

def is_whitelisted(kerb):
    db = getdb();
    return True if (db.students.lookup(kerb) or db.whitelist.lookup(kerb)) else False

def is_admin(kerb):
    db = getdb()
    return db.admins.lucky({'kerb': kerb})

def send_message(sender, recipient, typ, content):
    db = getdb()
    db.messages.insert_many([{'sender_kerb': sender, 'recipient_kerb': recipient, 'type': typ, 'content': content}], resort=False)

def log_event(kerb, event, detail={}, status=0):
    db = getdb()
    db.events.insert_many([{'kerb': kerb, 'timestamp': datetime.datetime.now(), 'status': status, 'event': event, 'detail': detail}], resort=False)

def next_match_date(class_id):
    import datetime

    db = getdb()
    match_dates = db.classes.lucky({'id': class_id}, projection='match_dates')
    if match_dates:
        today = datetime.datetime.now().date()
        match_dates = [d for d in match_dates if d >= today]
        if match_dates:
            return match_dates[0].strftime("%b %-d")
    return ""

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

def generate_group_name(class_id, year=current_year(), term=current_term()):
    db = getdb()
    S = { g for g in db.groups.search({'class_id': class_id}, projection='group_name') }
    A = { g.split(' ')[0] for g in S }
    N = { g.split(' ')[1] for g in S }
    acount = count_rows('positive_adjectives')
    ncount = count_rows('plural_nouns')
    while True:
        a = db.positive_adjectives.random({})
        if 2*len(A) < acount and a in A:
            continue
        n = db.plural_nouns.random({'firstletter':a[0]})
        if 4*len(N) < ncount and n in N:
            continue
        name = a.capitalize() + " " + n.capitalize()
        if db.groups.lucky({'group_name': name, 'year': year, 'term': term}):
            continue
        return name

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
    mv = 0 if instructor_view else 2
    for g in db.groups.search({'class_number': class_number, 'year': year, 'term': term, 'visibility' : {'$gte': mv} }, projection=['id']+[o for o in opts if o in db.groups.col_type]):
        members = list(students_in_group(g['id']))
        r = group_row(g, len(members))
        if 'members' in opts and (g['visibility'] == 3 or instructor_view):
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
        self._db = getdb()
        data = self._db.students.lucky({"kerb":kerb}, projection=3)
        if data is None:
            data = { col: None for col in self._db.students.col_type }
            data['kerb'] = kerb
            data['full_name'] = full_name
            data['id'] = -1
            data['new'] = True
            data['last_login'] =  datetime.datetime.now()
            data['last_seen'] = data['last_login']
            if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
                send_message("", kerb, "welcome", student_welcome)
            log_event (kerb, 'new')
        else:
            data['new'] = False
            if not data.get('full_name'):
                data['full_name'] = full_name
            log_event (kerb, 'load', detail={'student_id': data['id']})
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
        elif not self.new:
            r = self._db.globals.lookup('sandbox')
            return not self.last_login or self.last_login < r['timestamp']
        else:
            return False

    def seen(self):
        self._db.students.update({'kerb': self.kerb},{'last_seen':datetime.datetime.now()}, resort=False)
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

    def acknowledge(self, msgid):
        self._db.messages.update({'id': msgid},{'read':True}, resort=False)
        log_event (self.kerb, 'ok')
        return "ok"

    def save(self):
        with DelayCommit(self):
            log_event (self.kerb, 'save', {'student_id': self.id})
            return self._save()

    def join(self, group_id):
        with DelayCommit(self):
            log_event (self.kerb, 'join''leave', {'group_id': group_id})
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
                    flash_info(self._pool(c['class_id']))
                    n += 1
        if not n:
            "You are either in a group or have already requested a match in all of your classes"
        else:
            log_event (current_user.kerb, 'poolme', {'count': n})

        return "Done!"

    def pool(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'pool', {'class_id': class_id})
            return self._pool(class_id)

    def unpool(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'unpool', {'class_id': class_id})
            return self._unpool(class_id)

    def match(self, class_id):
        with DelayCommit(self):
            log_event (self.kerb, 'match', {'class_id': class_id})
            return self._match(class_id)

    def create_group(self, group_id, options, public=True):
        with DelayCommit(self):
            log_event (self.kerb, 'create', detail={'group_id': group_id, 'options': options, 'public': public})
            return self._create_group(group_id, options=options, public=public)

    def edit_group(self, group_id, options):
        with DelayCommit(self):
            log_event (self.kerb, 'edit', detail={'group_id': group_id, 'options': options})
            return self._edit_group(group_id, options)

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
                raise ValueError("You are currently a mamber of a different group in <b>%s</b>\n.  To accept this invitation you need to leave your current group first." % g['class_number'])
        if not g['class_number'] in self.classes:
            self.classes.append(g['class_number'])
            self.save()
        if gid == g['id']:
            self.send_message('', 'accepted', "You are currently a member of the <b>%s</b> pset group <b>%s</b>.  Welcome back!" % (g['class_number'], g['group_name']))
        else:
            self.join(g['id'])
            self.send_message('', 'accepted', "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (g['class_number'], g['group_name']))
        self.update_toggle('ct', g['class_number'])
        self.update_toggle('ht', 'partner-header')
        log_event (self.kerb, 'accept', detail={'group_id':gid})

    def update_toggle(self, name, value):
        if not name:
            return "no"
        if self.toggles.get(name) == value:
            return "ok"
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
        for class_number in self.classes:
            query = { 'class_number': class_number, 'year': year, 'term': term}
            class_id = self._db.classes.lucky(query, projection='id')
            if class_id is None:
                raise ValueError("Class %s is not listed in the pset partners list of classes for this term." % class_number)
            oldr = self._db.classlist.lucky({'class_id': class_id, 'student_id': self.id})
            if oldr:
                r = oldr.copy()
                # make sure derived data is up to date (it should be but kerb was not getting set at one point)
                r['class_number'] = class_number
                r['year'] = year
                r['term'] = term
                r['kerb'] = self.kerb
            else:
                r = { 'class_id': class_id, 'student_id': self.id, 'year': year, 'term': term, 'class_number': class_number, 'kerb': self.kerb, 'status': 0 }
            # if user was just added to the class (e.g. via an invitation) we may not have any class_data for it
            if class_number in self.class_data:
                r['properties'] = self.class_data[class_number].get('properties', {})
                r['preferences'] = self.class_data[class_number].get('preferences', {})
                r['strengths'] = self.class_data[class_number].get('strengths', {})
            else: 
                r['properties'], r['preferences'], r['strengths'] = {}, {}, {}
            if oldr:
                if r != oldr:
                    self._db.classlist.update(oldr,r)
                    log_event (self.kerb, 'edit', detail={'class_id': class_id})
            else:
                self._db.classlist.insert_many([r])
                log_event (self.kerb, 'add', detail={'class_id': class_id})
            class_ids.add(class_id)

        for class_id in self._db.classlist.search ({'student_id': self.id, 'year': year, 'term': term}, projection="class_id"):
            if class_id not in class_ids:
                self._db.classlist.delete({'class_id': class_id, 'student_id': self.id})
                self._db.grouplist.delete({'class_id': class_id, 'student_id': self.id})
                log_event (self.kerb, 'drop', detail={'class_id': class_id})
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
        r = { k: g[k] for k in  ['class_id', 'class_number', 'year', 'term']}
        r['group_id'], r['student_id'], r['kerb'] = group_id, self.id, self.kerb
        self._db.grouplist.insert_many([r], resort=False)
        self._notify_group(group_id, "Say hello to your new pset partner!",
                           "%s has joined your pset group %s in %s!<br>You can contact your new partner at %s." % (self.pretty_name, g['group_name'], g['class_number'], self.email_address))
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
        self._db.grouplist.delete({'group_id': group_id, 'student_id': self.id}, resort=False)
        self._db.classlist.update({'class_id': g['class_id'], 'student_id': self.id}, {'status': 0}, resort=False)
        msg = "You have been removed from the group <b>%s</b> in <b>%s</b>." % (g['group_name'], c)
        if not self._db.grouplist.lucky({'group_id': group_id}, projection="id"):
            self._db.groups.delete({'id': group_id}, resort=False)
            msg += " You were the only member of this group, so it has been disbanded."
        else:
            self._notify_group(group_id, "pset partner notification",
                           "%s (kerb=%s) has left the pset group %s in %s." % (self.preferred_name, self.kerb, g['group_name'], g['class_number']))
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
        d = next_match_date(class_id)
        if self.class_data[c]['status'] == 4:
            msg = "We are already working on an urgent match for you in %s and have sent emails to a number of groups. If none respond we will put you in the <b>%s</b> match pool." % (c,d)
        else:
            msg = "You are now in the match pool for <b>%s</b> and will be matched on <b>%s</b>." %(c, d)
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 2}, resort=False)
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
            raise ValueError("You are currrently a member of the group %s in %s, and not in the match pool." % (self.group_data[c]['group_name'], c))
        if self.class_data[c]['status'] != 2:
            app.logger.warning("User %s attempted to leave the pool for class %s but is not in the match pool for that class" % (self.kerb, class_id, self.group_data[c]['id']))
            raise ValueError("You are and not in the match pool for %s." % c)
        d = next_match_date(class_id)
        msg = "You have been removed from the match pool for <b>%s</b> on <b>%s</b>." %(c, d)
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status': 0}, resort=False)
        self._reload()
        return msg

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
        return "We will start working on a match for you in <b>%s</b>, you should receive an email from us within 24 hours." % c

    def _create_group(self, class_id, options=None, public=True):
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
        prefs = {}
        for k in ['start', 'style', 'forum', 'size']:
            get_pref_option(prefs, options, k)
        visibility = 3 if public else (1 if options.get('open','').strip() else 0)
        editors = [self.kerb] if options.get('editors','').strip() == '1' else []
        strengths = {} # Groups don't have preference strengths right now
        maxsize = max_size_from_prefs(prefs)
        name = generate_group_name(class_id)
        g = {'class_id': class_id, 'year': current_year(), 'term': current_term(), 'class_number': c['class_number'], 'group_name': name,
             'visibility': visibility, 'preferences': prefs, 'strengths': strengths, 'editors': editors, 'max': maxsize }
        self._db.groups.insert_many([g], resort=False)
        r = {'class_id': class_id, 'group_id': g['id'], 'student_id': self.id, 'kerb': self.kerb, 'class_number': g['class_number'], 'year': g['year'], 'term': g['term'] }
        self._db.grouplist.insert_many([r], resort=False)
        self._db.classlist.update({'class_id': class_id, 'student_id': self.id}, {'status':1})
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
        if visibility < 2:
            visibility = (1 if options.get('open','').strip() else 0)
        editors = g['editors']
        if len(editors) and options.get('editors','').strip() != '1':
            editors = []
        maxsize = max_size_from_prefs(prefs)
        self._db.groups.update({'id': group_id}, {'preferences': prefs, 'visibility': visibility, 'editors': editors, 'max': maxsize}, resort=False)
        self._notify_group(group_id, "pset partner notification",
                           "%s (kerb=%s) updated the settings for the pset group %s in %s." % (self.preferred_name, self.kerb, g['group_name'], g['class_number']))
        self._reload()
        return "Updated the group <b>%s</b>!" % g['group_name']

    def _notify_group(self, group_id, subject, message):
        def email(s):
            return s['email'] if s.get('email') else s['kerb'] + '@mit.edu'

        S = [s for s in students_in_group(group_id) if s['id'] != self.id]
        if len(S) == 0:
            return

        self._db.messages.insert_many([{'type': 'notify', 'content': message, 'recipient_kerb': s['kerb'], 'sender_kerb': self.kerb} for s in S], resort=False)
        if livesite():
            send_email([email(s) for s in S], subject, message + signature)
        else: #TODO: remove this once we go live
            send_email([email(s) for s in S], subject, message + signature)

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
            members = list(students_in_group(gid, member_row_cols))
            g['count'] = len(members)
            g['members'] = sorted([member_row(s) for s in members])
            g['can_edit'] = True if self.kerb in g['editors'] or g['editors'] == [] else False;
            token = generate_timed_token({'kerb':self.kerb, 'group_id': str(g['id'])}, 'invite')
            g['invite'] = url_for(".accept_invite", token=token, _external=True, _scheme="http" if debug_mode() else "https")
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
        data = self._db.instructors.lucky({'kerb': kerb}, projection=3)
        if data is None:
            data = { col: None for col in self._db.students.col_type }
            data['kerb'] = kerb
            data['full_name'] = full_name
            data['id'] = -1
            data['new'] = True
            if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
                send_message("", kerb, "welcome", new_instructor_welcome)
            log_event (kerb, 'load', {'instructor_id': data['id']})
        else:
            data['new'] = False
            if not data.get('full_name'):
                data['full_name'] = full_name
            if not self._db.messages.lucky({'recipient_kerb': kerb, 'type': 'welcome'}):
                send_message("", kerb, "welcome", old_instructor_welcome)
            log_event (kerb, 'new', {'instructor':True})
        cleanse_instructor_data(data)
        self.__dict__.update(data)
        assert self.kerb
        for col, typ in self._db.instructors.col_type.items():
            if getattr(self, col, None) is None:
                setattr(self, col, default_value(typ))
        self.classes = self._class_data()
        assert self.kerb

    def acknowledge(self, msgid):
        self._db.messages.update({'id': msgid},{'read':True}, resort=False)
        log_event (self.kerb, 'ok')
        return "ok"

    def update_toggle(self, name, value):
        if not name:
            return "no"
        if self.toggles.get(name) == value:
            return "ok"
        self.toggles[name] = value;
        self._db.instructors.update({'id': self.id}, {'toggles': self.toggles}, resort=False)
        return "ok"

    def _class_data(self, year=current_year(), term=current_term()):
        classes = list(self._db.classes.search({ 'instructor_kerbs': {'$contains': self.kerb}, 'year': year, 'term': term},projection=3))
        for c in classes:
            c['students'] = sorted([student_row(s) for s in students_groups_in_class(c['id'], student_row_cols)])
            c['next_match_date'] = c['match_dates'][0].strftime("%b %-d")
        return sorted(classes, key = lambda x: x['class_number'])

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
        self._db.instructors.update({'kerb':self.kerb},{'last_seen':datetime.datetime.now()}, resort=False)
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

def sandbox_message():
    from . import db

    r = db.globals.lookup('sandbox')
    if not r:
        return ''
    return "The sandbox was refreshed at %s (MIT time) with a new population of %s students." % (r['timestamp'].strftime("%Y-%m-%d %H:%M:%S"), r['value'].get('students'))

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
    from . import db
    mydb = db

    with DelayCommit(mydb):
        _generate_test_population(num_students, max_classes)
        db.globals.update({'key':'sandbox'},{'timestamp': datetime.datetime.now(), 'value':{'students':num_students}}, resort=False)
    print("Done!")

def _generate_test_population(num_students=300,max_classes=6):
    from random import randint

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

    db = getdb() # we will still explicitly reference test_ tables just to be doubly sure we don't wipe out the production DB

    db.test_events.delete({}, resort=False)
    db.test_messages.delete({}, resort=False)
    db.test_students.delete({}, resort=False)
    db.test_groups.delete({}, resort=False)
    db.test_classlist.delete({}, resort=False)
    db.test_grouplist.delete({}, resort=False)
    print("Deleted all records in test_students, test_groups, test_classlist, and test_grouplist.")
    year, term = current_year(), current_term()
    blank_student = { col: default_value(db.test_students.col_type[col]) for col in db.test_students.col_type }
    S = []
    names = set()
    for n in range(num_students):
        s = blank_student.copy()
        s['kerb'] = "test%03d" % n
        while True:
            firstname = db.names.random()
            name = db.math_adjectives.random({'firstletter': firstname[0]}).capitalize() + " " + firstname.capitalize()
            if name in names:
                continue
            break
        names.add(name)
        s['preferred_name'] = s['full_name'] = name
        s['year'] = rand(year_options)[0] if randint(0,7) else None
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
        s['departments'] = sorted(list(set(departments)), key=course_number_key)
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
                if randint(0,2):
                    prefs[p] = rand(student_preferences[p])[0]
                    strengths[p] = randint(1,5)
                    if p == "forum" and p in prefs and prefs[p] == "in-person":
                        prefs[p] = "video";
            else:
                q = p.split('_')[0]
                if q in student_affinities and s[q] and randint(0,1):
                    prefs[p] = rand(student_preferences[p])[0]
                    strengths[p] = randint(1,5)
        s['preferences'] = prefs
        s['strengths'] = strengths
        S.append(s)
    db.test_students.insert_many(S, resort=False)
    S = []
    for s in db.test_students.search(projection=3):
        student_id = s["id"]
        if s['year'] in [1,2] and randint(0,3):
            classes = [db.test_classes.lucky({'year': year, 'term': term, 'class_number': rand(big_classes)}, projection=['id', 'class_number'])]
        else:
            classes = [db.test_classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])]
            while s['year'] in [3,4,5] and classes[0]['class_number'].split('.')[1][0] == '0':
                classes = [db.test_classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])]
        if randint(0,2):
            c = db.test_classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])
            if not c in classes:
                classes.append(c)
            for m in range(2,max_classes):
                if randint(0,2*m-2):
                    break;
                c = db.test_classes.random({'year': year, 'term': term}, projection=['id', 'class_number'])
                if not c in classes:
                    classes.append(c)
        for i in range(len(classes)):
            prefs, strengths, props = {}, {}, {}
            for p in student_class_properties:
                if randint(0,1):
                    props[p] = rand(student_class_properties[p])[0]
                    strengths[p] = randint(1,5)
                    if randint(0,1):
                        pa = p + "_affinity"
                        prefs[pa] = rand(student_preferences[pa])[0]
                        strengths[pa] = rand_strength()
            for p in student_preferences:
                if not p.endswith("_affinity"):
                    if p in s['preferences']:
                        if randint(0,2):
                            prefs[p] = s['preferences'][p]
                            strengths[p] = s['strengths'][p]
                        else:
                            prefs[p] = rand(student_preferences[p])[0]
                            strengths[p] = rand_strength()
                    elif randint(0,2) == 0:
                        prefs[p] = rand(student_preferences[p])[0]
                        strengths[p] = rand_strength()
            for p in student_affinities:
                pa = p + "_affinity"
                if pa in s['preferences'] and randint(0,2):
                    prefs[pa] = s['preferences'][pa]
                    strengths[pa] = s['strengths'][pa]
                elif randint(0,2) == 0:
                    prefs[pa] = rand(student_preferences[pa])[0]
                    strengths[pa] = randint(1,5)
            c = { 'class_id': classes[i]['id'], 'student_id': student_id, 'kerb': s['kerb'], 'class_number': classes[i]['class_number'],
                  'year': year, 'term': term, 'preferences': prefs, 'strengths': strengths, 'properties': props, 'status': 0 }
            S.append(c)
    db.test_classlist.insert_many(S, resort=False)
    S = []
    names = set({})
    for c in db.test_classes.search({'year': year, 'term': term}, projection=['id', 'class_number']):
        kerbs = list(db.test_classlist.search({'class_id':c['id']},projection='kerb'))
        n = len(kerbs)
        creators = set()
        for i in range(n//10):
            while True:
                name = generate_group_name(c['id'])
                if name in names:
                    continue
                break
            names.add(name)            
            creator = rand(kerbs)
            if creator in creators:
                continue
            s = db.test_students.lookup(creator, projection=['id','preferences', 'strengths'])
            prefs = { p: s['preferences'][p] for p in s.get('preferences',{}) if not p.endswith('affinity') }
            strengths = { p: s['strengths'][p] for p in s.get('strengths',{}) if not p.endswith('affinity') }
            for p in ["start", "style", "forum", "size"]:
                if not p in prefs and randint(0,1):
                    prefs[p] = rand(student_preferences[p])[0]
                    strengths[p] = rand_strength()
            maxsize = max_size_from_prefs(prefs)
            eds = [creator] if randint(0,1) else []
            g = {'class_id': c['id'], 'year': year, 'term': term, 'class_number': c['class_number'],
                 'group_name': name, 'visibility': 3, 'preferences': prefs, 'strengths': strengths, 'creator': creator, 'editors': eds, 'max': maxsize }
            creators.add(creator)
            S.append(g)
    if ( S ):
        db.test_groups.insert_many(S, resort=False)
        S = []
        for g in db.test_groups.search(projection=3):
            gid, cid, cnum, eds = g['id'], g['class_id'], g['class_number'], g['editors']
            n = 0
            for k in eds:
                sid = db.test_students.lookup(k,projection="id")
                # make creator didn't leave to join another group
                if db.test_classlist.lucky({'class_id': cid, 'student_id': sid},projection='status'):
                    db.test_groups.update({'id':gid},{'editors':[]})
                    continue
                S.append({'class_id': cid, 'student_id': sid, 'kerb': k, 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                n += 1
                db.test_classlist.update({'class_id': cid, 'student_id': sid}, {'status': 1}, resort=False)
            while True:
                if g['max'] and n >= g['max']:
                    break
                s = rand(list(db.test_classlist.search({'class_id': cid, 'status': 0},projection=["student_id", "kerb"])))
                S.append({'class_id': cid, 'student_id': s['student_id'], 'kerb': s['kerb'], 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                n += 1
                db.test_classlist.update({'class_id': cid, 'student_id': s['student_id']}, {'status': 1}, resort=False)
                if randint(0,n-1):
                    break
        db.test_grouplist.insert_many(S, resort=False)
    # put most of the students not already in a group into the pool
    for s in db.test_classlist.search(projection=["id","status"]):
        if s['status'] == 0 and randint(0,9):
            db.test_classlist.update({'id':s['id']},{'status':2}, resort=False)

    # take instructors from classes table for current term
    S = []
    for r in db.test_classes.search({'year': current_year(), 'term': current_term()},projection=['class_number', 'instructor_kerbs','instructor_names']):
        if r['instructor_kerbs']:
            for i in range(len(r['instructor_kerbs'])):
                kerb, name = r['instructor_kerbs'][i], r['instructor_names'][i]
                S.append({'kerb':kerb,'preferred_name':name,'full_name':name,'departments':['18'],'toggles':{}})
    db.test_instructors.insert_many(S, resort=False)             
