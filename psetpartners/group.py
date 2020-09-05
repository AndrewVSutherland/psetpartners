from psycodict import DelayCommit
from .app import send_email
from .utils import current_term, current_year
from .dbwrapper import getdb, count_rows

group_preferences = [ 'start', 'style', 'forum', 'size' ]

new_group_subject = "Say hellp to your new pset partners in %s!"

new_group_email = """
Greetings!  Pset partners has placed you in a pset group in <b>%s</b>.
To learn more about your group and its memebers please visit<br><br>

&nbsp;&nbsp;https://psetpartners.mit.edu/student/%s<br><br>

We encourage you to reach out to your new group today.  You can
use the "email the group" button on pset partners to do this.
"""

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

def create_group (class_id, student_ids, match_run=0, group_name=''):
    from .student import max_size_from_prefs, email_address, signature

    db = getdb()
    c = db.classes.lucky({'id': class_id})

    g = { 'class_id': class_id, 'year': c['year'], 'term': c['term'], 'class_number': c['class_number'] }
    g['visibility'] = 1  # open by default
    g['creator'] = ''    # system created
    g['editors'] = []    # everyone can edit

    students = [db.students.lucky({'id': id}, projection=['kerb','email','preferences', 'id']) for id in student_ids]
    g['preferences'] = {}
    for p in group_preferences:
        v = { s['preferences'][p] for s in students if p in s['preferences'] }
        if len(v) == 1:
            g['preferences'][p] = list(v)[0]
    print(g)
    g['max'] = max_size_from_prefs(g['preferences'])
    g['match_run'] = match_run

    with DelayCommit(db):
        g['group_name'] = group_name if group_name else generate_group_name(class_id, c['year'], c['term'])
        db.groups.insert_many([g])
        gs = [{'class_id': class_id, 'group_id': g['id'], 'student_id': s['id'], 'kerb': s['kerb'],
               'class_number': c['class_number'], 'year': c['year'], 'term': c['term']} for s in students]
        db.grouplist.insert_many(gs)
        for id in student_ids:
            db.classlist.update({'class_id': class_id, 'id': id}, {'status':1})

    cnum = g['class_number']
    message = "Welcome to the <b>%s</b> pset group <b>%s</b>!" % (cnum, g['group_name'])
    db.messages.insert_many([{'type': 'newgroup', 'content': message, 'recipient_kerb': s['kerb'], 'sender_kerb':''} for s in students], resort=False)
    send_email([email_address(s) for s in students], new_group_subject % cnum, new_group_email % (cnum, cnum) + signature)
 