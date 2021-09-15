import logging, datetime
from psycodict import DelayCommit
from .app import send_email, livesite
from .config import Configuration
from .dbwrapper import getdb, db_islive
from .people import get_kerb_data
from .utils import current_term, current_year
from .match import match_all
from .group import process_matches, disband_group

poolme_subject = "[Action Required] pset partner matching {matchdate} for {cs}"

poolme_body = """
You are receiving this message because you added the class<br><br>

&nbsp;&nbsp;<b>{cstr}</b><br><br>

on pset partners but you are not currently a member of a group or
in the match pool for this class.  If you would like to be included
in the pool of students to be matched {matchdate} at 10pm, click
the link below:<br><br>

&nbsp;&nbsp;<a href="{poolmeurl}">{poolmeurl}</a><br><br>

If you are no longer looking for a pset partner in this class you
can click the link below to remove it from your profile and prevent
messages like this in the future:<br><br>

&nbsp;&nbsp;<a href="{removemeurl}">{removemeurl}</a>
"""

checkin_subject = "pset partner check-in for {cs}"

checkin_body = """
We're checking in to see how things are going with your pset group in:<br><br>

&nbsp;&nbsp;<b>{cstr}</b><br><br>

If your group is working well, great!  You can let us know (or not) at:<br><br>

&nbsp;&nbsp;<a href="{imgoodurl}">{imgoodurl}</a><br><br>

If your group is not working so well, or if you simply had trouble connecting,<br>
we'd be happy to help you find a new group.  Click<br><br>

&nbsp;&nbsp;<a href="{regroupmeurl}">{regroupmeurl}</a><br><br>

to leave your current group and see your options for joining a new one.<br>
You will be asked for confirmation before any action is taken.
"""

uncap_subject = "A student in {cs} is looking for a pset group"

uncap_body = """
We were unable to match a student in <b>{cs}</b> with a pset group because every compatible group is full.<br><br>

When the group <b>{gname}</b> was created it was capped at 4 students by default.
Removing this cap would potentially allow this unmatched student to join your group.
To approve this action, visit the following link:<br><br>

&nbsp;&nbsp;<a href="{uncapurl}">{uncapurl}</a><br><br>

Removing this cap does not necessarily mean a student will be added to your group, it simply makes it possible.
You can restore this cap at any time by editing the size preference for your group.
"""


def are_we_live(forcelive):
    return forcelive or livesite()

def send_poolme_links(forcelive=False, preview=True, class_number="", nonempty_pool_only=True, days_ahead=1):
    from . import app
    from .student import email_address, signature, log_event

    logger = create_admin_logger('poolme', forcelive=forcelive, preview=preview)
    now = datetime.datetime.now()
    db = getdb(forcelive)
    root = "https://psetpartners.mit.edu/" if db_islive(db) else "https://psetpartners-test.mit.edu/"
    with app.app_context():
        query = {'active':True, 'year': current_year(), 'term': current_term(), 'size': {'$gt':1}}
        if class_number:
            query['class_number']=class_number
        today = now.date()
        tomorrow = today + datetime.timedelta(days=1)
        mindate = today if now.hour < 22 else tomorrow
        maxdate = now.date() + datetime.timedelta(days=days_ahead)
        for c in db.classes.search(query, projection=3):
            match_dates = [d for d in c['match_dates'] if d >= mindate and d <= maxdate]
            if len(match_dates) == 0:
                continue
            if nonempty_pool_only and len(list(db.classlist.search({'class_id': c['id'], 'status': 2}, projection='id'))) == 0:
                continue
            match_date = match_dates[0]
            matchdate = "tonight" if match_date == today else ("tomorrow night" if match_date == tomorrow else match_date.strftime("%b %-d"))
            cs = ' / '.join(c['class_numbers'])
            cstr = cs + " " + c['class_name']
            poolmeurl = root + "poolme/%s" % c['class_number']
            removemeurl = root + "removeme/%s" % c['class_number']
            subject = poolme_subject.format(matchdate=matchdate,cs=cs)
            body = poolme_body.format(cstr=cstr, poolmeurl=poolmeurl, removemeurl=removemeurl, matchdate=matchdate)
            for kerb in db.classlist.search({'class_id': c['id'], 'status':0 }, projection="kerb"):
                if db.events.lucky({'kerb':kerb,'event':'poolnag','detail':{'class_id':c['id'],'match_date': match_date}}):
                    logger.info('Not sending already sent email "%s" to %s' % (subject, kerb))
                    continue
                if preview:
                    logger.info('Not sending poolme email "%s" to %s' % (subject, kerb))
                else:
                    logger.info('Sending poolme email "%s" to %s' % (subject, kerb))
                    send_email(email_address(kerb), subject, body+signature)
                    log_event(kerb, 'poolnag', {'class_id': c['id'], 'match_date': match_date})
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return logfile

def send_checkins(forcelive=False, preview=True):
    from . import app
    from .student import email_address, signature, log_event

    logger = create_admin_logger('checkin', forcelive=forcelive, preview=preview)
    db = getdb(forcelive)
    latest = datetime.datetime.now() - datetime.timedelta(days=4)
    root = "https://psetpartners.mit.edu/" if db_islive(db) else "https://psetpartners-test.mit.edu/"
    with app.app_context():
        for c in db.classes.search({'active':True, 'year': current_year(), 'term': current_term()}, projection=3):
            cs = ' / '.join(c['class_numbers'])
            cstr = cs + " " + c['class_name']
            imgoodurl = root + "imgood/%s" % c['class_number']
            regroupmeurl = root + "regroupme/%s" % c['class_number']
            for kerb in db.classlist.search({'class_id': c['id'], 'status':1, 'status_timestamp': {'$lt': latest}, 'checkin_pending': True }, projection="kerb"):
                subject = checkin_subject.format(cs=cs)
                body = checkin_body.format(cstr=cstr, imgoodurl=imgoodurl, regroupmeurl=regroupmeurl)
                if preview:
                    logger.info("Not sending checkin email: %s to %s" % (subject, kerb))
                else:
                    logger.info("Sending checkin email: %s to %s" % (subject, kerb))
                    send_email(email_address(kerb), subject, body+signature)
                    db.classlist.update({'class_id': c['id'], 'kerb': kerb}, {'checkin_pending': False}, resort=False)
                    log_event(kerb, 'checkin', {'class_id': c['id']})
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return logfile

def send_uncap_requests(forcelive=False, preview=True):
    from . import app
    from .student import email_address, signature, log_event

    logger = create_admin_logger('uncap', forcelive=forcelive, preview=preview)
    db = getdb(forcelive)
    root = "https://psetpartners.mit.edu/" if db_islive(db) else "https://psetpartners-test.mit.edu/"
    with app.app_context():
        for c in db.classes.search({'active':True, 'year': current_year(), 'term': current_term()}, projection=['id','class_numbers']):
            n = db.groups.count({'class_id': c['id']})
            if n == 0 or not db.events.lucky({'event':'unmatched','detail.class_id':c['id']}):
                continue
            full = [r for r in db.groups.search({'class_id':c['id'],'visibility':2,'preferences.size':'3.5','creator':''}, projection=3) if r['size'] == r['max']]
            if len(full) > 0 and len(full) == n:
                cs = ' / '.join(c['class_numbers'])
                for g in full:
                    kerbs = list(db.grouplist.search({'group_id': g['id']}, projection="kerb"))
                    prefs = [db.students.lookup(kerb,projection='preferences') for kerb in kerbs]
                    prefs = [p for p in prefs if 'size' in p]
                    if len([p for p in prefs if p['size'] <= '4']) == 0 or len([p for p in prefs if p['size'] <= '4']) < len([p for p in prefs if p['size'] > '4']):
                        uncapurl = root + "uncap/%s" % g['id']
                        for kerb in kerbs:
                            subject = uncap_subject.format(cs=cs)
                            body = uncap_body.format(cs=cs, gname=g['group_name'], uncapurl=uncapurl)
                            if preview:
                                logger.info("Not sending uncap email: %s to %s" % (subject, kerb))
                            else:
                                logger.info("Sending uncap email: %s to %s" % (subject, kerb))
                                send_email(email_address(kerb), subject, body+signature)
                                log_event(kerb, 'uncaprequest', {'group_id': g['id']})
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return logfile

def create_admin_logger(name, forcelive=False, preview=True):
    logger = logging.getLogger(name)
    if logger.handlers:
        logger.handlers.clear()
    today = datetime.datetime.now()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
    filename = '%s-%s-%s-%s.log' % ("live" if are_we_live(forcelive) else "test", name, "preview" if preview else "execute", today.strftime("%Y:%m:%d:%H:%M:%S"))
    fh = logging.FileHandler(filename, mode='w')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    logger.propagate = False
    logger.info("Beginning %s log" % name)
    return logger

def admin_logger_filename(logger):
    return logger.handlers[0].baseFilename

def clear_admin_logger(logger):
    logger.info("Ending %s log" % logger.name)
    logger.handlers.clear()

def preview_matches(forcelive=False):
    logger = create_admin_logger('match', forcelive=forcelive, preview=True)
    results = match_all(forcelive=forcelive, preview=True, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return results, logfile

def compute_matches(forcelive=False):
    logger = create_admin_logger('cmatch', forcelive=forcelive, preview=False)
    results = match_all(forcelive=forcelive, preview=False, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return results, logfile

def apply_matches(results, forcelive=False, email_test=False):
    from . import app

    db = getdb(forcelive)
    r = db.globals.lookup('match_run')
    match_run = r['value']+1 if r else 0
    db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)
    logger = create_admin_logger('pmatch', forcelive=forcelive, preview=False)
    with app.app_context():
        process_matches (results, match_run=match_run, forcelive=forcelive, email_test=email_test, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return logfile

# compute_matches + apply_matches
def make_matches(forcelive=False, email_test=False):
    from . import app

    db = getdb(forcelive)
    with DelayCommit(db):
        r = db.globals.lookup('match_run')
        match_run = r['value']+1 if r else 0
        db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)
        logger = create_admin_logger('match', forcelive=forcelive, preview=False)
        results = match_all(forcelive=forcelive, vlog=logger)
        if results:
            with app.app_context():
                process_matches (results, match_run=match_run, forcelive=forcelive, email_test=email_test, vlog=logger)
        logfile = admin_logger_filename(logger)
        clear_admin_logger(logger)
        return logfile
    return None

def rematch_groups(group_ids, forcelive=False, email_test=False):
    from . import app

    db = getdb(forcelive)
    r = db.globals.lookup('match_run')
    match_run = r['value']+1 if r else 0
    db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)
    logger = create_admin_logger('pmatch', forcelive=forcelive, preview=False)
    with app.app_context():
        for gid in group_ids:
            disband_group (gid, rematch=True, forcelive=forcelive, email_test=email_test, vlog=logger)
        results = match_all(rematch=True, forcelive=forcelive, vlog=logger)
        process_matches (results, match_run=match_run, forcelive=forcelive, email_test=email_test, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return logfile

def fill_from_people():
    db = getdb(True)

    db.students.update({'full_name': '(null)'}, {'full_name': ''},restort=False)
    for kerb in db.students.search({'full_name': ''}, projection='kerb'):
        c = Configuration().options['people']
        data = get_kerb_data(kerb, c['id'], c['secret'])
        if not data:
            print("No data available for kerb %s" % kerb)
            continue
        if not data.get('full_name'):
            print("No displayName data available for kerb %s" % kerb)
            continue
        db.students.update({'kerb': kerb}, {'full_name': data['full_name']},resort=False)
        print("Full name %s for %s" % (data['full_name'], kerb))

    for kerb in db.students.search({'year': None}, projection='kerb'):
        c = Configuration().options['people']
        data = get_kerb_data(kerb, c['id'], c['secret'])
        if not data:
            print("No data available for kerb %s" % kerb)
            continue
        if not data.get('year'):
            print("No year available for kerb %s" % kerb)
            continue
        db.students.update({'kerb': kerb, 'year': None}, {'year': data['year']})
        print("Year %d for kerb %s" % (data['year'], kerb))

    for kerb in db.students.search({'departments': []}, projection='kerb'):
        c = Configuration().options['people']
        data = get_kerb_data(kerb, c['id'], c['secret'])
        if not data:
            print("No data available for kerb %s" % kerb)
            continue
        if not data.get('departments'):
            print("No departments data available for kerb %s" % kerb)
            continue
        db.students.update({'kerb': kerb, 'departments': []}, {'departments': data['departments']},resort=False)
        print("Departments %s for kerb %s" % (data['departments'], kerb))
