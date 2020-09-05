import datetime
from psycodict import DelayCommit
from .utils import current_term, current_year, DEFAULT_TIMEZONE_NAME
from .dbwrapper import getdb
from .student import (
    student_preferences,
    student_affinities,
    student_class_properties,
    course_number_key,
    year_options,
    location_options,
    max_size_from_prefs,
    default_value,
    generate_group_name,
)

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
