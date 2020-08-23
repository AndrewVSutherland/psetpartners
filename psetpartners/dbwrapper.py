from psycopg2.sql import SQL
from psycodict.utils import IdentifierWrapper
from psetpartners import db
from psetpartners.app import is_livesite
from psetpartners.utils import current_year, current_term, hours_from_default

_db = None

def getdb():
    global _db

    if is_livesite():
        return db
    if _db is None:
        _db = PsetPartnersTestDB(db)
    return _db

class PsetPartnersTestDB:
    def __init__(self, db):
        self._db = db

    @property
    def students(self):
        return self._db.test_students

    @property
    def groups(self):
        return self._db.test_groups

    @property
    def classlist(self):
        return self._db.test_classlist

    @property
    def departments(self):
        return self._db.departments

    @property
    def classes(self):
        return self._db.classes

    @property
    def admins(self):
        return self._db.admins

    @property
    def names(self):
        return self._db.names

    @property
    def plural_nouns(self):
        return self._db.plural_nouns

    @property
    def math_adjectives(self):
        return self._db.positive_adjectives

    @property
    def positive_adjectives(self):
        return self._db.positive_adjectives

class DBIterator:
    def __init__(self, SQL_iterator, cols):
        self._iter, self._cols = SQL_iterator, cols
        self._n = len(self._cols)

    def __iter__(self):
        return self

    def __next__(self):
        vals = self._iter.__next__()
        return { self._cols[i]: vals[i] for i in range(self._n) }

def SQLWrapper(str,map={}):
    from string import Formatter
    keys = [t[1] for t in Formatter().parse(str) if t[1] is not None]
    return (SQL(str).format(**{key:IdentifierWrapper(map[key] if key in map else key) for key in keys}))

def students_in_class(class_number):
    s, c = ("students", "classlist") if is_livesite() else ("test_students", "test_classlist")
    if not class_number:
        return db[s].search({},projection=['timezone', 'hours', 'departments', 'year', 'gender','preferences', 'strengths'])
    cmd = SQLWrapper(
        """
SELECT {s}.{timezone}, {s}.{hours}, {s}.{departments}, {s}.{year}, {s}.{gender}, {c}.{properties}, {c}.{preferences}, {s}.{strengths}
FROM {c} INNER JOIN {s} ON {s}.{id} = {c}.{student_id}
WHERE {c}.{class_number} = %s and {c}.{year} = %s and {c}.{term} = %s
        """,
        {'s':s, 'c':c}
    )
    cols = ['timezone', 'hours', 'departments', 'year', 'gender', 'properties', 'preferences', 'strengths']
    return DBIterator(db._execute(cmd, [class_number, current_year(), current_term()]), cols)

def count_hours(iter):
    hours = [0 for i in range(168)]
    for r in iter:
        off = hours_from_default(r["timezone"]) if r["timezone"] else 0
        for i in range(168):
            hours[(i-off) % 168] += 1 if r['hours'][i] else 0
    return hours

def get_counts(classes):
    db = getdb();
    counts = {}
    c = {}
    c['students'] = len(list(db.students.search({},projection='id')))
    c['groups'] = len(list(db.groups.search({'year': current_year(), 'term': current_term()},projection='id')))
    c['hours'] = count_hours(students_in_class(''))
    counts['General'] = c
    for class_number in classes:
        c = {}
        class_id = db.classes.lucky({'year': current_year(), 'term': current_term(), 'class_number': class_number},projection="id")
        if class_id is not None:
            c['students'] = len(list(db.classlist.search({'class_id':class_id},projection='id')))
            c['groups'] = len(list(db.groups.search({'year': current_year(), 'term': current_term(), 'class_number': class_number},projection='id')))
            c['hours'] = count_hours(students_in_class(class_number))
            counts[class_number] = c
    return counts