import datetime
from psycodict import DelayCommit
from .utils import current_term, current_year, DEFAULT_TIMEZONE_NAME
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

def sandbox_data():
    from . import db

    r = db.globals.lookup('sandbox')
    if not r:
        return None
    return {
        'students': r['value'].get('students',"?"),
        'instructors': r['value'].get('instructors',"?"),
        'date': r['timestamp'].strftime("%Y-%m-%d"),
        'time': r['timestamp'].strftime("%H:%M"),
        }

test_timezones = ["US/Samoa", "US/Hawaii", "Pacific/Marquesas", "America/Adak", "US/Alaska", "US/Pacific", "US/Mountain",
                  "US/Central", "US/Eastern", "Brazil/East", "Canada/Newfoundland", "Brazil/DeNoronha", "Atlantic/Cape_Verde", "Iceland",
                  "Europe/London", "Europe/Paris", "Europe/Athens", "Asia/Dubai", "Asia/Baghdad", "Asia/Jerusalem", "Asia/Tehran",
                  "Asia/Karachi", "Asia/Kolkata", "Asia/Katmandu", "Asia/Dhaka", "Asia/Rangoon", "Asia/Jakarta", "Asia/Singapore", "Australia/Eucla",
                  "Asia/Seoul", "Asia/Tokyo", "Australia/Adelaide", "Australia/Sydney", "Australia/Lord_Howe",
                  "Pacific/Norfolk", "Pacific/Auckland", "Pacific/Chatham", "Pacific/Tongatapu", "Pacific/Kiritimati"]

test_departments = ['6', '8', '7', '20', '5', '9', '10', '1', '3', '2', '16',  '14', '12', '4', '11', '22', '24', '21', '17']

big_classes = [ '1.00', '2.001', '3.091', '4.021', '5.111', '5.112', '6.0001', '6.002', '6.004', '6.033', '6.034',
    '7.012', '7.013', '7.014', '7.015', '7.016', '7.26', '8.01', '8.02', '8.033', '9.13', '9.40', '9.85', '10.00', '10.01',
    '12.400', '14.01', '14.02', '15.025', '15.034', '16.001',     '16.002', '16.003', '16.004',
    '18.01', '18.02', '18.03', '18.06', '18.404', '18.600', '22.00', '22.01', '24.09' ]

def populate_sandbox(num_students=5000, num_instructors=0, active_classes=500, max_classes_per_student=8, prefprob=3, groupsize=4):
    """ generates a random student population for testing (destorys existing test data) """
    from . import db
    mydb = db

    choice = input("Are you sure? This will destroy the existing test database? [y/n] ").lower()
    if not choice or choice[0] != 'y':
        print("No changes made.")
        return

    with DelayCommit(mydb):
        # copy classes from live database for current term
        mydb.test_classes.delete({}, resort=False)
        mydb.test_classes.insert_many(list(mydb.classes.search({'year': current_year(), 'term': current_term()}, projection=3)), resort=False)
        n = len(list(mydb.test_classes.search({})))
        if n == 0:
            print("Unable to populate sandbox, there are no classes defined for the current term")
            return
        print ("Copied %d records from classes to test_classes"%n)
        mydb.test_classes.update({},{'active':False,'owner_kerb':'','instructor_kerbs':[]},resort=False)
        mydb.test_classes.update({},{'size':0},resort=False)
        if n < active_classes:
            print ("Only %d classes available, using all of them."%n)
            active_classes = m = n
            mydb.test_classes.update({},{'active':True},resort=False)
        else:
            n = active_classes
            m = len(list(mydb.test_classes.search({'active':True})))
            while m != n:
                class_id = mydb.test_classes.random({'active': m > n},projection="id")
                mydb.test_classes.update({'id':class_id}, {'active': m < n},resort=False)
                m += 1 if m < n else -1
        print ("Made %d classes active" % active_classes)
        if num_instructors == 0:
            num_instructors = 2*n // 3
        _populate_sandbox(num_students, num_instructors, max_classes_per_student, prefprob)
        mydb.globals.update({'key':'sandbox'},{'timestamp': datetime.datetime.now(), 'value':{'students': "%04d" % num_students, 'instructors': "%03d" % num_instructors}}, resort=False)
        print("Committing changes...")
    print("Done!")

def _populate_sandbox(num_students=5000, num_instructors=500, max_classes_per_student=8, prefprob=3, groupsize=4):
    from random import randint
    from .dbwrapper import getdb

    pronouns = { 'female': 'she/her', 'male': 'he/him', 'non-binary': 'they/them' }

    assert num_students < 10000

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

    npref = prefprob-1 if prefprob > 1 else 1
    db = getdb()
    db.test_events.delete({}, resort=False)
    db.test_messages.delete({}, resort=False)
    db.test_requests.delete({}, resort=False)
    db.test_students.delete({}, resort=False)
    db.test_instructors.delete({}, resort=False)
    db.test_groups.delete({}, resort=False)
    db.test_classlist.delete({}, resort=False)
    db.test_grouplist.delete({}, resort=False)
    db.test_survey_responses.delete({}, resort=False)
    print("Deleted all records in test database.")

    active_classes = len(list(db.test_classes.search({'active':True})))
    
    if num_students < 5*active_classes:
        active_classes = num_students // 5
        print ("Reduced active classes to %d to ensure an average of at least 5 students per class" % active_classes)

    if num_students > 100*active_classes:
        num_students = 100*active_classes
        print("Reduced number of_students to %d to ensure an average of no more than 100 students per class" % num_students)

    year, term = current_year(), current_term()

    S = [{ 'kerb' : "p%03d" % n, 'full_name': 'Professor ' + db.profnames.random() } for n in range(1,num_instructors+1)]
    for r in S:
        r['preferred_name'] = r['full_name']
    db.test_instructors.insert_many(S, resort=False)
    n = 0
    for class_id in db.test_classes.search(projection="id"):
        p=rand(S)
        db.test_classes.update({'id': class_id}, {'owner_kerb': p['kerb'], 'owner_name': p['preferred_name'], 'instructor_kerbs': [p['kerb']]},resort=False)
        n += 1
    print ("Created %d instructors and randomly assigned them to %d classes, now generating students..." % (num_instructors, n))

    # make sure first few professors have at least one active class
    for n in range(1,8):
        if not db.test_classes.lucky({'active':True, 'owner_kerb': "p%03d" % n}):
            p = S[n]
            c = db.test_classes.random({'active':True}, projection=3)
            kerbs = c['instructor_kerbs']
            if not p['kerb'] in kerbs:
                kerbs = [p['kerb']] + kerbs
            db.test_classes.update({'id': c['id']}, {'owner_kerb': p['kerb'], 'owner_name': p['preferred_name'], 'instructor_kerbs': kerbs}, resort=False)

    blank_student = { col: default_value(db.test_students.col_type[col]) for col in db.test_students.col_type }
    now = datetime.datetime.now()
    S = []
    names = set()
    for num in range(1,num_students+1):
        s = blank_student.copy()
        s['kerb'] = "s%04d" % num
        while True:
            firstname = db.names.random()
            name = db.student_adjectives.random({'firstletter': firstname[0]}).capitalize() + " " + firstname.capitalize()
            if name in names:
                continue
            break
        names.add(name)
        if len(names)%100 == 0:
            print(len(names))
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
                if randint(0,npref) == 0:
                    prefs[p] = rand(student_preferences[p])[0]
                    strengths[p] = randint(1,5)
                    if p == "forum" and p in prefs and prefs[p] == "in-person":
                        prefs[p] = "video";
            else:
                q = p.split('_')[0]
                if q in student_affinities and s[q] and randint(0,npref) == 0:
                    prefs[p] = rand(student_preferences[p])[0]
                    strengths[p] = randint(1,5)
        s['preferences'] = prefs
        s['strengths'] = strengths
        s['conduct'] = True
        S.append(s)
    db.test_students.insert_many(S, resort=False)
    big = {x for x in big_classes if db.test_classes.lucky({'class_number':x, 'active':True},projection="id")}
    aclasses = list(db.test_classes.search({'year': year, 'term': term, 'active': True}, projection=['id', 'class_number']))
    bclasses = [r for r in aclasses if r['class_number'] in big]
    S = []
    for s in db.test_students.search(projection=3):
        student_id = s["id"]
        classes = [rand(bclasses)] if bclasses and s['year'] in [1,2] and randint(0,2) else [rand(aclasses)]
        while s['year'] in [3,4,5] and classes[0]['class_number'].split('.')[1][0] == '0':
            classes = [rand(aclasses)]
        while True:
            c = rand(aclasses)
            if not c in classes:  # sometimes random returns None!
                classes.append(c)
                break
        for m in range(2,max_classes_per_student):
            if m > 3 and randint(0,m-3):
                break
            while True:
                c = rand(aclasses)
                if not c in classes:
                    classes.append(c)
                    break
        for i in range(len(classes)):
            prefs, strengths, props = {}, {}, {}
            for p in student_class_properties:
                if randint(0,1):
                    props[p] = rand(student_class_properties[p])[0]
                    if randint(0,npref) == 0:
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
                    elif randint(0,npref) == 0:
                        prefs[p] = rand(student_preferences[p])[0]
                        strengths[p] = rand_strength()
            for p in student_affinities:
                pa = p + "_affinity"
                if pa in s['preferences'] and randint(0,2):
                    prefs[pa] = s['preferences'][pa]
                    strengths[pa] = s['strengths'][pa]
                elif randint(0,npref) == 0:
                    prefs[pa] = rand(student_preferences[pa])[0]
                    strengths[pa] = randint(1,5)
            c = { 'class_id': classes[i]['id'], 'student_id': student_id, 'kerb': s['kerb'], 'class_number': classes[i]['class_number'],
                  'year': year, 'term': term, 'preferences': prefs, 'strengths': strengths, 'properties': props, 'status': 0, 'status_timestamp': now }
            S.append(c)
    db.test_classlist.insert_many(S, resort=False)
    for class_id in db.test_classes.search({'active':True}, projection='id'):
        n = len(list(db.test_classlist.search({'class_id': class_id},projection='id')))
        db.test_classes.update({'id': class_id}, {'size': n}, resort=False)
    S = []
    names = set()
    for c in db.test_classes.search({'active': True, 'year': year, 'term': term}, projection=['id', 'class_number', 'class_numbers']):
        kerbs = list(db.test_classlist.search({'class_id':c['id']},projection='kerb'))
        n = len(kerbs)
        creators = set()
        class_names = set()
        for i in range(n//(groupsize+1)):
            name = generate_group_name(class_names=class_names,avoid_names=names,year=year,term=term)
            names.add(name)
            class_names.add(name)            
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
            eds = [creator] if randint(0,2)==0 else []
            if randint(0,2):
                creator = ''
            visibility = randint(0,3)
            g = {'class_id': c['id'], 'year': year, 'term': term, 'class_number': c['class_number'], 'class_numbers': c['class_numbers'],
                 'group_name': name, 'visibility': visibility, 'preferences': prefs, 'strengths': strengths, 'created': now, 'creator': creator, 'editors': eds, 'max': maxsize }
            creators.add(creator)
            S.append(g)
        print("Created %s groups in %s, total names used = %s" % (n//(groupsize+1),c['class_number'], len(names)))
    if ( S ):
        db.test_groups.insert_many(S, resort=False)
        S = []
        for g in db.test_groups.search(projection=3):
            gid, cid, cnum, eds = g['id'], g['class_id'], g['class_number'], g['editors']
            n = 0
            for k in eds:
                sid = db.test_students.lookup(k,projection="id")
                # make sure creator didn't leave to join another group
                if db.test_classlist.lucky({'class_id': cid, 'student_id': sid},projection='status'):
                    db.test_groups.update({'id':gid},{'editors':[]}, resort=False)
                    continue
                S.append({'class_id': cid, 'student_id': sid, 'kerb': k, 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                n += 1
                db.test_classlist.update({'class_id': cid, 'student_id': sid}, {'status': 1, 'status_timestamp': now}, resort=False)
            while True:
                if g['max'] and n >= g['max']:
                    break
                L = list(db.test_classlist.search({'class_id': cid, 'status': 0},projection=["student_id", "kerb"]))
                if not L:
                    break
                s = rand(L)
                S.append({'class_id': cid, 'student_id': s['student_id'], 'kerb': s['kerb'], 'group_id': gid, 'year': year, 'term': term, 'class_number': cnum})
                n += 1
                db.test_classlist.update({'class_id': cid, 'student_id': s['student_id']}, {'status': 1, 'status_timestamp': now}, resort=False)
                if randint(0,groupsize-1)==0:
                    break
            db.test_groups.update({'id': g['id']}, {'size': n}, resort=False)
        db.test_grouplist.insert_many(S, resort=False)
    # put most of the students not already in a group into the pool
    for s in db.test_classlist.search(projection=["id","status"]):
        if s['status'] == 0 and randint(0,9):
            db.test_classlist.update({'id':s['id']},{'status':2, 'status_timestamp': now}, resort=False)
