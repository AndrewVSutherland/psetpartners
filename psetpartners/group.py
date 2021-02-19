import datetime
from psycodict import DelayCommit
from .app import send_email, livesite
from .utils import current_term, current_year, hours_from_default
from .dbwrapper import getdb, get_forcelive

FIRST_MEETING_OFFSET = 36 # first meeting is at least this many hours after the email is sent

group_preferences = [ 'start', 'style', 'forum', 'size' ]

new_group_subject = "Say hello to your pset partners in {class_numbers}!"

new_group_email = """
Greetings!  You have been matched with a pset group in <b>{class_numbers}</b>.<br>
To learn more about your group and its members please visit<br><br>

&nbsp;&nbsp;{url}<br><br>

We encourage you to reach out to your new group today.<br>
You can use the "email group" button on pset partners to do this.<br><br>

It looks like there are {hours} each week when your schedules overlap.  We suggest a brief initial meeting at<br><br>

&nbsp;&nbsp;{meet_time} (MIT Time)<br><br>

to introduce yourselves to each other and discuss how you want to work together.
"""

new_group_short_email = """
Greetings!  You have been matched with a pset group in <b>{class_numbers}</b>.<br>
To learn more about your group and its members please visit<br><br>

&nbsp;&nbsp;{url}<br><br>

We encourage you to reach out to your new group today.<br>
You can use the "email group" button on pset partners to do this.<br><br>
"""

unmatched_subject = "Notification from pset partners regarding {class_numbers}"

unmatched_email = """
We were unable to place you in a pset group in <b>{class_numbers}</b>.

We are very sorry this happened!  It most likely occured because there were no students in the match pool whose schedule overlapped with yours, or possibly you had a required preference that could not be met.

We encourage you to visit<br><br>

&nbsp;&nbsp;{url}<br><br>

and either join a public group, or click the "match me asap" button if available and we will try to put you into an existing group.
"""

def normalized_hours(s):
    offset = hours_from_default(s["timezone"])
    hours = s["hours"]
    return tuple(hours[(i-offset)%168] for i in range(168))

def available_hours(S):
    x = list(zip(*[normalized_hours(s) for s in S]))
    return [i for i in range(168) if all(x[i])]

def student_url(class_number):
    url = "https://psetpartners.mit.edu/student" if (livesite() or get_forcelive()) else "https://psetpartners-test.mit.edu/student"
    return url if not class_number else url + "/" + class_number

def generate_group_name(class_id=None, year=current_year(), term=current_term(), class_names=set(), avoid_names=set()):
    from random import randint
    def rand(x):
        return x[randint(0,len(x)-1)]

    db = getdb()
    S = set(class_names)
    if class_id is not None:
        S.update({ g for g in db.groups.search({'class_id': class_id}, projection='group_name') })
    Sa = { g.split(' ')[0].lower() for g in S }
    Sn = { g.split(' ')[1].lower() for g in S }
    N = list(db.plural_nouns.search({},projection="word"))
    L = { w[0] for w in Sn }
    if len(L) <= 20: # don't force 26 letters
        N = [ n for n in N if not n[0] in L ]
    for i in range(100):
        n = rand(N)
        if n in Sn:
            continue
        a = db.positive_adjectives.random({'firstletter':n[0]},projection="word")
        if not a:
            continue
        if a in Sa:
            continue
        name = a.capitalize() + " " + n.capitalize()
        if i < 50 and name in avoid_names:
            continue
        if i < 50 and db.groups.lucky({'group_name': name, 'year': year, 'term': term}):
            continue
        return name
    print("error in generate_group_name, L=%s, N=%s, class_names=%s, len(avoid_names)=%s:" % (L,N,class_names,len(avoid_names)))
    raise NotImplementedError("Unable to generate group name!")

def create_group (class_id, kerbs, match_run=0, group_name=''):
    from .student import max_size_from_prefs, email_address, signature, log_event

    db = getdb()
    c = db.classes.lucky({'id': class_id})
    assert c, "Class id %s not found" % class_id

    now = datetime.datetime.now()

    g = { 'class_id': class_id, 'year': c['year'], 'term': c['term'], 'class_number': c['class_number'], 'class_numbers': c['class_numbers'] }
    g['visibility'] = 2  # automatic by default
    g['creator'] = ''    # system created
    g['created'] = now   # created now
    g['editors'] = []    # everyone can edit

    students = [db.students.lookup(kerb, projection=['kerb', 'email', 'timezone', 'hours', 'preferences', 'id']) for kerb in kerbs]
    assert all(students), "Student in %s not found" % kerbs
    available = available_hours(students)
    hours = len(available)
    if hours:
        now = datetime.datetime.now()
        current_hour = 24*now.weekday() + now.hour()
        next_hour = (current_hour + FIRST_MEETING_OFFSET) % 168
        meet_hour = min([i for i in available if i >= next_hour]) if available[-1] > next_hour else available[0]
        meet_time = now + datetime.timedelta(hours=(meet_hour-current_hour)%168)

    g['preferences'] = {}
    for p in group_preferences:
        v = { s['preferences'][p] for s in students if p in s['preferences'] }
        if len(v) == 1:
            g['preferences'][p] = list(v)[0]
    g['size'] = len(kerbs)
    g['max'] = max_size_from_prefs(g['preferences'])
    g['match_run'] = match_run

    with DelayCommit(db):
        g['group_name'] = group_name if group_name else generate_group_name(class_id, c['year'], c['term'])
        print("creating group %s with members %s" % (g['group_name'], kerbs))
        # sanity check
        assert all([db.classlist.lucky({'class_id': class_id, 'student_id': s['id']},projection='status')==5 for s in students])
        db.groups.insert_many([g], resort=False)
        gs = [{'class_id': class_id, 'group_id': g['id'], 'student_id': s['id'], 'kerb': s['kerb'],
               'class_number': c['class_number'], 'year': c['year'], 'term': c['term']} for s in students]
        db.grouplist.insert_many(gs, resort=False)
        now = datetime.datetime.now()
        for s in students:
            db.classlist.update({'class_id': class_id, 'student_id': s['id']}, {'status':1, 'status_timestamp': now}, resort=False)
        log_event ('', 'create', detail={'group_id': g['id'], 'group_name': g['group_name'], 'members': kerbs})
        print("created group %s with members %s" % (g['group_name'], kerbs))

    cs = ' / '.join(g['class_numbers'])
    message = "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (cs, g['group_name'])
    db.messages.insert_many([{'type': 'newgroup', 'content': message, 'recipient_kerb': s['kerb'], 'sender_kerb':''} for s in students], resort=False)
    subject = new_group_subject.format(class_numbers=cs)
    url = student_url(g['class_number'])
    if hours:
        body = new_group_email.format(class_numbers=cs,url=url,hours=hours,meet_time=meet_time.strftime("%-I%p on %b %-d"))
    else:
        body = new_group_short_email.format(class_numbers=cs,url=url)
    send_email([email_address(s) for s in students], subject, body + signature)
    return g
 
def process_matches (matches, match_run=-1):
    """
    Takes a dictionary returned by all_matches, keys are class_id's, values are objects with attributes
    groups = list of lists of kerbs, unmatched = list of tuples (kerb, reason) where reason is 'only' or 'requirement'
    only means there was only one member of the pool, requirement means a required preference could not be satisifed
    """
    from .student import Student, email_address, signature
    from .match import rank_groups

    db = getdb()
    if match_run < 0:
        r = db.globals.lookup('match_run')
        match_run = r['value']+1 if r else 0
    db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)

    m = n = o = 0
    for class_id in matches:
        class_number = db.classes.lucky({'id': class_id}, projection="class_number")
        assert class_number
        print("Processing results for %s (%d)" % (class_number, class_id))
        for kerbs in matches[class_id]['groups']:
            g = create_group(class_id, kerbs, match_run=match_run)
            print("Created group %s (%d) in %s (%d) with %s members: %s" % (g['group_name'], g['id'], g['class_number'], g['class_id'], len(kerbs), kerbs))
            m += 1
        for kerb in matches[class_id]['unmatched']:
            c = db.classes.lucky({'id': class_id})
            assert c, "Class id %s not found" % class_id
            assert db.students.lookup(kerb), "Student %s not found" % kerb
            S = [t for t in rank_groups(class_id, kerb) if t[1] == 2]
            db.classlist.update({'class_id': class_id, 'kerb': kerb}, {'status': 0}, resort=False)
            if S and S[0][2] > -1000:
                group_id = S[0][0]
                group_name = db.groups.lucky({'id': group_id}, projection="group_name")
                s = Student(kerb)
                assert not s.new
                s.join(group_id)
                print("Added %s to the group %s (%d) in %s (%d)" % (kerb, group_name, group_id, c['class_number'], class_id))
                n += 1
            else:
                print("Unable to match %s in %s (id=%d)" % (kerb, class_number, class_id))
                cs = ' / '.join(c['class_numbers'])
                subject = unmatched_subject.format(class_numbers=cs)
                body = unmatched_email.format(class_numbers=cs, url=student_url(c['class_number']))
                send_email(email_address(kerb), subject, body + signature)
                o += 1
    print("Created %d new groups and added %d new members in match_run %d with %d unmatched" % (m, n, match_run, o))
