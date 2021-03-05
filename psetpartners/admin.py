import logging, datetime
from psycodict import DelayCommit
from .app import send_email, livesite
from .config import Configuration
from .dbwrapper import getdb, db_islive
from .people import get_kerb_data
from .utils import current_term, current_year
from .match import match_all
from .group import process_matches, disband_group

poolme_subject = "[Action Required] pset partner matching tonight for {cs}"

poolme_body = """
You are receiving this message because you added the class<br><br>

&nbsp;&nbsp;<b>{cstr}</b><br><br>

on pset partners but you are not currently a member of a group or
in the match pool for this class, which is forming new pset groups
tonight.  If you want to be included, click the link below:<br><br>

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

def are_we_live(forcelive):
    return forcelive or livesite()

def send_poolme_links(forcelive=False, preview=True):
    from . import app
    from .student import email_address, signature, log_event

    db = getdb(forcelive)
    today = datetime.datetime.now().date()
    root = "https://psetpartners.mit.edu/" if db_islive(db) else "https://psetpartners-test.mit.edu/"
    with app.app_context():
        for c in db.classes.search({'active':True, 'year': current_year(), 'term': current_term(), 'match_dates': {'$contains': today}}, projection=3):
            cs = ' / '.join(c['class_numbers'])
            cstr = cs + " " + c['class_name']
            poolmeurl = root + "poolme/%s" % c['class_number']
            removemeurl = root + "removeme/%s" % c['class_number']
            for kerb in db.classlist.search({'class_id': c['id'], 'status':0 }, projection="kerb"):
                subject = poolme_subject.format(cs=cs)
                body = poolme_body.format(cstr=cstr, poolmeurl=poolmeurl, removemeurl=removemeurl)
                if preview:
                    print("Not sending email: %s to %s" % (subject, kerb))
                else:
                    send_email(email_address(kerb), subject, body+signature)
                    log_event(kerb, 'poolnag', {'class_id': c['id'], 'match_date': today})

def send_checkins(forcelive=False, preview=True):
    from . import app
    from .student import email_address, signature, log_event

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
                    print("Not sending email: %s to %s" % (subject, kerb))
                else:
                    send_email(email_address(kerb), subject, body+signature)
                    db.classlist.update({'class_id': c['id'], 'kerb': kerb}, {'checkin_pending': False}, resort=False)
                    log_event(kerb, 'checkin', {'class_id': c['id']})

def create_admin_logger(name, forcelive=False):
    logger = logging.getLogger(name)
    if logger.handlers:
        logger.handlers.clear()
    today = datetime.datetime.now().date()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', "%Y-%m-%d %H:%M:%S")
    filename = '%s%s-%s.log' % ("" if are_we_live(forcelive) else "test-", name, today.strftime("%Y-%m-%d"))
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
    logger = create_admin_logger('preview', forcelive=forcelive)
    results = match_all(forcelive=forcelive, preview=True, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return results, logfile

def compute_matches(forcelive=False):
    logger = create_admin_logger('cmatch', forcelive=forcelive)
    results = match_all(forcelive=forcelive, vlog=logger)
    logfile = admin_logger_filename(logger)
    clear_admin_logger(logger)
    return results, logfile

def apply_matches(results, forcelive=False, email_test=False):
    from . import app

    db = getdb(forcelive)
    r = db.globals.lookup('match_run')
    match_run = r['value']+1 if r else 0
    db.globals.update({'key':'match_run'},{'timestamp': datetime.datetime.now(), 'value': match_run}, resort=False)
    logger = create_admin_logger('pmatch-'+str(match_run), forcelive=forcelive)
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
        logger = create_admin_logger('match-'+str(match_run), forcelive=forcelive)
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
    logger = create_admin_logger('pmatch-'+str(match_run), forcelive=forcelive)
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
