import datetime
from psycodict import DelayCommit
from .app import send_email, livesite
from .utils import current_term, current_year, hours_from_default, null_logger
from .dbwrapper import getdb, get_forcelive, db_islive

FIRST_MEETING_OFFSET = 36 # first meeting is at least this many hours after the email is sent

group_preferences = [ 'start', 'style', 'forum', 'size' ]

new_group_subject = "Say hello to your pset partners in {class_numbers}!"

new_group_email = """
Greetings!  You have been matched with a pset group in <b>{class_numbers}</b>.<br>
To learn more about your group and its members please visit<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

We encourage you to reach out to your new partners today to discuss how/where/when you would like to collaborate.
You can use the "email group" button on pset partners to do this.<br><br>

It looks like there are {hours} hours each week when your schedules overlap.<br>
Based on your schedules, one possible time for a first meeting is<br><br>

&nbsp;&nbsp;{meet_time} (MIT Time)<br><br>

but of course you can choose any time that is mutually agreeable, and you may want to meet earlier if your next pset is due soon.
"""

new_group_problem_email = """
Greetings!  You have been matched with a pset group in <b>{class_numbers}</b>.<br>
To learn more about your group and its members please visit<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

We encourage you to reach out to your new partners today.<br>
You can use the "email group" button on pset partners to do this.<br><br>

There appears to be a scheduling conflict with your group that we were unable to avoid.  We suggest discussing this issue to see if you can still find a time that works for everyone (or perhaps agree to work asynchronously). 
if that isn't possible one or more of you may want to leave this group and try entering the match pool again next week.
"""

disbanded_group_subject = "Important pset partner notification for {class_numbers}"

disbanded_group_email = """
We are writing to let you know that the group <b>{group_name}</b> in <b>{class_numbers}</b> has been disbanded.<br><br>

If you were placed in this group in a recent matching this means you are being reassigned to a new group and should receive a separate email about your new group soon.<br><br>

As always, you can view your current status and pset partner options for this class at<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

Please feel free to contact us if you have any questions or concerns.
"""

unmatched_subject = "pset partner match notification for {class_numbers}"

unmatched_only_email = """
We were unable to place you in a pset group in <b>{class_numbers}</b>.

We are very sorry this happened!  It most likely occured because there were no students in the match pool whose schedule overlapped yours.

We encourage you to visit<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

and either join a public group if one is available, or join the match pool for next week.
"""

unmatched_other_email = """
We were unable to place you in a pset group in <b>{class_numbers}</b>.

We are very sorry this happened!  It most likely occured because there were no students in the match pool whose schedule overlapped yours or you had a requirement that could not be satisifed.

We encourage you to visit<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

and either join a public group if one is available, or join the match pool for next week.
"""

only_subject = """Pset partners failed to match any students in {class_numbers}"""

only_email = """
You are receiving this email because pset partners failed to match any students in the class {class_numbers} for which you are an instructor.  This occurred because there was only one student in the match pool.<br><br>

We suggest advertizing pset partners to your class and actively encouraging students to place themselves in the match pool in the coming week.<br><br>

Unmatched students must explicitly request a match by placing themselves in the pool for the next match date in order to be eligible for a match, it is not enough to simply have the class listed in their pset partners profile (unmatched students are emailed reminders but do not always respond to them).<br><br>

The next match date for {class_numbers} is {next_match_date}.  You can change this date by clicking the "edit" link next to your class on<br><br>

&nbsp;&nbsp;<a href="{url}">{url}</a><br><br>

Please contact us if you have any questions or concerns.
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

def generate_group_name(class_id=None, year=current_year(), term=current_term(), class_names=set(), avoid_names=set(), forcelive=False):
    from random import randint
    def rand(x):
        return x[randint(0,len(x)-1)]

    db = getdb(forcelive)
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

def disband_group (group_id, rematch=False, forcelive=False, email_test=False, vlog=null_logger()):
    from .student import email_address, signature, log_event

    db = getdb(forcelive)
    now = datetime.datetime.now()
    with DelayCommit(db):
        g = db.groups.lucky({'id': group_id}, projection=3)
        if not g:
            raise ValueError("Group %s not found" % group_id)
        members = list(db.grouplist.search({'group_id':group_id}))
        for r in members:
            db.classlist.update({'class_id': r['class_id'], 'student_id': r['student_id']}, {'status': 5 if rematch else 0, 'status_timestamp': now}, resort=False)
        kerbs = [r['kerb'] for r in members]
        db.groups.delete({'id': group_id}, resort=False)
        db.grouplist.delete({'group_id': group_id}, resort=False)
        log_event ('admin', 'disband', detail={'group_id': g['id'], 'group_name': g['group_name'], 'members': kerbs})
        vlog.info("Disbanded group %s (%d) in %s (%d) with %d members %s" % (g['group_name'], g['id'], g['class_number'], g['class_id'], len(kerbs), kerbs))

    cs = ' / '.join(g['class_numbers'])
    url = student_url(g['class_number'])
    message = "The <b>%s</b> pset group <b>%s</b> has been disbanded." % (cs, g['group_name'])
    db.messages.insert_many([{'sender_kerb':'', 'recipient_kerb': k, 'type': 'disband', 'content': message, 'timestamp': now} for k in kerbs], resort=False)
    subject = disbanded_group_subject.format(class_numbers=cs, group_name=g['group_name'])
    body = disbanded_group_email.format(class_numbers=cs, group_name=g['group_name'], url=url)
    if db_islive(db) or email_test:
        vlog.info("emailing [%s] to %s" % (subject, [email_address(k) for k in kerbs]))
        send_email([email_address(k) for k in kerbs], subject, body + signature)
    else:    
        vlog.info("not emailing [%s] to %s" % (subject, [email_address(k) for k in kerbs]))
    return g


def create_group (class_id, kerbs, match_run=0, group_name='', forcelive=False, email_test=False, vlog=null_logger()):
    from .student import max_size_from_prefs, email_address, signature, log_event

    db = getdb(forcelive)
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
        current_hour = 24*now.weekday() + now.hour
        next_hour = (current_hour + FIRST_MEETING_OFFSET) % 168
        meet_hour = min([i for i in available if i >= next_hour]) if available[-1] > next_hour else available[0]
        meet_time = now + datetime.timedelta(hours=(meet_hour-current_hour)%168)

    g['preferences'] = {}
    for p in group_preferences:
        v = { s['preferences'][p] for s in students if p in s['preferences'] }
        if len(v) == 1:
            g['preferences'][p] = list(v)[0]
    g['size'] = len(kerbs)
    # for automatic groups with no size preference, set a size preference based on the current size
    # this is important to prevent highly compatible groups from excessive growth via "match me now"
    if not 'size' in g['preferences'] and g['visibility'] == 2 and match_run:
        if g['size'] <= 4:
            g['preferences']['size'] = "3.5"
        elif g['size'] <= 8:
            g['preferences']['size'] = "5"
    g['max'] = max_size_from_prefs(g['preferences'])
    g['match_run'] = match_run

    with DelayCommit(db):
        g['group_name'] = group_name if group_name else generate_group_name(class_id, c['year'], c['term'], forcelive=forcelive)
        # sanity check
        assert all([db.classlist.lucky({'class_id': class_id, 'student_id': s['id']},projection='status')==5 for s in students])
        db.groups.insert_many([g], resort=False)
        gs = [{'class_id': class_id, 'group_id': g['id'], 'student_id': s['id'], 'kerb': s['kerb'],
               'class_number': c['class_number'], 'year': c['year'], 'term': c['term']} for s in students]
        db.grouplist.insert_many(gs, resort=False)
        now = datetime.datetime.now()
        for s in students:
            db.classlist.update({'class_id': class_id, 'student_id': s['id']}, {'status':1, 'status_timestamp': now, 'checkin_pending': True}, resort=False)
        log_event ('', 'create', detail={'group_id': g['id'], 'group_name': g['group_name'], 'members': kerbs})
        vlog.info("Created group %s (%d) in %s (%d) with %d members %s" % (g['group_name'], g['id'], g['class_number'], g['class_id'], len(kerbs), kerbs))

    cs = ' / '.join(g['class_numbers'])
    message = "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (cs, g['group_name'])
    db.messages.insert_many([{'sender_kerb':'', 'recipient_kerb': s['kerb'], 'type': 'newgroup', 'content': message, 'timestamp': now} for s in students], resort=False)
    subject = new_group_subject.format(class_numbers=cs)
    url = student_url(g['class_number'])
    if hours:
        body = new_group_email.format(class_numbers=cs,url=url,hours=hours,meet_time=meet_time.strftime("%-I%p on %b %-d"))
    else:
        body = new_group_problem_email.format(class_numbers=cs,url=url)
    if db_islive(db) or email_test:
        vlog.info("emailing [%s] to %s" % (subject, [email_address(s) for s in students]))
        send_email([email_address(s) for s in students], subject, body + signature)
    else:    
        vlog.info("not emailing [%s] to %s" % (subject, [email_address(s) for s in students]))
    return g

def notify_instructors (class_id, forcelive=False, email_test=False, vlog=null_logger()):
    from .student import email_address, signature

    db = getdb(forcelive)
    if db.grouplist.count({'class_id':class_id}) > 1:
        return False
    c = db.classes.lucky({'id': class_id}, projection=["class_numbers", "instructor_kerbs", "match_dates"])
    root = "https://psetpartners.mit.edu/" if db_islive(db) else "https://psetpartners-test.mit.edu/"
    now = datetime.datetime.now()
    today = now.date()
    match_dates = [d for d in c["match_dates"] if d > today]
    if not match_dates:
        return False
    nd = match_dates[0].strftime("%b %-d")
    cs = ' / '.join(c['class_numbers'])
    subject = only_subject.format(class_numbers=cs)
    body = only_email.format(class_numbers=cs, next_match_date=nd, url=root)
    kerbs = c["instructor_kerbs"]
    if db_islive(db) or email_test:
        vlog.info("emailing [%s] to %s" %(subject, kerbs))
        send_email([email_address(k) for k in kerbs], subject, body + signature)
        return True
    else:
        vlog.info("not emailing [%s] to %s" % (subject, kerbs))
    return False
 
def process_matches (matches, match_run=-1, forcelive=False, email_test=False, vlog=null_logger()):
    """
    Takes a dictionary returned by all_matches, keys are class_id's, values are objects with attributes
    groups = list of lists of kerbs, unmatched = list of tuples (kerb, reason) where reason is 'only' or 'requirement'
    only means there was only one member of the pool, requirement means a required preference could not be satisifed
    """
    from .student import Student, email_address, signature, log_event
    from .match import rank_groups

    db = getdb(forcelive)
    vlog.info("processing matches for %s database"%("live" if db_islive(db) else "test"))
    if match_run < 0:
        r = db.globals.lookup('match_run')
        match_run = r['value']+1 if r else 1
    db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)
    vlog.info("match_run = %o", match_run)

    now = datetime.datetime.now()
    m = n = o = 0
    for class_id in matches:
        class_number = db.classes.lucky({'id': class_id}, projection="class_number")
        assert class_number
        vlog.info("Processing results for %s (%d)" % (class_number, class_id))
        for kerbs in matches[class_id]['groups']:
            create_group(class_id, kerbs, match_run=match_run, forcelive=forcelive, email_test=email_test, vlog=vlog)
            m += 1
        onlykerbs = { kerb for kerb in matches[class_id]['unmatched_only'] }
        unmatched = matches[class_id]['unmatched_only'] + matches[class_id]['unmatched_other']
        for kerb in unmatched:
            c = db.classes.lucky({'id': class_id})
            assert c, "Class id %s not found" % class_id
            assert db.students.lookup(kerb), "Student %s not found" % kerb
            S = [t for t in rank_groups(class_id, kerb) if t[1] == 2]
            db.classlist.update({'class_id': class_id, 'kerb': kerb}, {'status': 0, 'status_timestamp': now}, resort=False)
            if S and S[0][2] > -1000:
                group_id = S[0][0]
                group_name = db.groups.lucky({'id': group_id}, projection="group_name")
                s = Student(kerb)
                assert not s.new
                s.join(group_id)
                vlog.info("Added %s to the group %s (%d) in %s (%d)" % (kerb, group_name, group_id, c['class_number'], class_id))
                n += 1
            else:
                cs = ' / '.join(c['class_numbers'])
                subject = unmatched_subject.format(class_numbers=cs)
                if kerb in onlykerbs:
                    body = unmatched_only_email.format(class_numbers=cs, url=student_url(c['class_number']))
                else:
                    body = unmatched_other_email.format(class_numbers=cs, url=student_url(c['class_number']))
                if db_islive(db) or email_test:
                    vlog.info("emailing [%s] to %s" %(subject, kerb))
                    send_email(email_address(kerb), subject, body + signature)
                else:
                    vlog.info("not emailing [%s] to %s" %(subject, kerb))
                log_event(kerb, 'unmatched', detail={'class_id': class_id, 'class_number': c['class_number']})
                o += 1
        if onlykerbs:
            notify_instructors(class_id, forcelive=forcelive, email_test=email_test, vlog=vlog)
    vlog.info("Created %d new groups and added %d new members in match_run %d with %d unmatched" % (m, n, match_run, o))
