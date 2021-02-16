from psycopg2.sql import SQL
from psycodict.utils import IdentifierWrapper
from . import db
from .app import livesite
from .utils import current_year, current_term

# TODO: get rid of this once the .count method in psycodict is fixed!
def count_rows(table, query={}):
    _db = getdb()
    return sum(1 for _ in _db[table].search(query, projection="id"))

_db = None
_forcelive = False
_warn_forcelive = False

def set_forcelive(forcelive):
    global _db, _forcelive
    _forcelive = forcelive
    _db = None
    _db = getdb()

def get_forcelive():
    global _forcelive
    return _forcelive

def getdb(forcelive=False):
    global _db, _forcelive, _warn_forcelive

    if forcelive:
        set_forcelive(forcelive)
    if _db is None:
        if livesite():
            _db = db
        elif _forcelive:
            if not _warn_forcelive:
                _warn_forcelive=True
                print("_forclive=True!")
            _db = db
        else:
            _db = PsetPartnersTestDB(db)
    return _db

# list of tablenames X we want to redirect to test_X
test_redirects = [
    'instructors',
    'students',
    'groups',
    'classlist',
    'grouplist',
    'grouplistleft',
    'messages',
    'events',
    'classes',
    'requests',
    'surveys',
    'survey_responses'
]

def test_redirect(str):
    return 'test_'+str if str in test_redirects else str

class PsetPartnersTestDB():
    def __init__(self, db):
        self._db = db

    def __getitem__(self, key):
        return self._db[test_redirect(key)]

    def __getattr__(self, item):
        if item == "_db":
            return self.__dict__["_db"]
        return getattr(self._db, test_redirect(item))

    def __setattr__(self, item, value):
        if item == "_db":
            self.__dict__["_db"] = value
        else:
            setattr(self._db, test_redirect(item), value)

    def __delattr__(self, item):
        if item == "_db":
            self.__dict__.pop("_db")
        else:
            delattr(self._db, test_redirect(item))

class DBIterator:
    def __init__(self, SQL_iterator, cols, projection=[]):
        self._iter, self._cols = SQL_iterator, cols
        if projection:
            if isinstance(projection,str):
                self.indexes = [cols.index(projection)]
            else:
                self.indexes = [i for i in range(len(cols)) if cols[i] in projection]    
        else:
            self.indexes = [i for i in range(len(cols))]

    def __iter__(self):
        return self

    def __next__(self):
        vals = self._iter.__next__()
        return { self._cols[i]: vals[i] for i in self.indexes }

def SQLWrapper(str,map={}):
    from string import Formatter
    keys = [t[1] for t in Formatter().parse(str) if t[1] is not None]
    return (SQL(str).format(**{key:IdentifierWrapper(map[key] if key in map else key) for key in keys}))


#TODO: handle query and projection args to these functions (we fake projection at the moment)

# returns data for students in classes for specified year and term (this is only used for computing counts, we don't need personal info)
def students_in_classes(year=current_year(), term=current_term(), projection=[]):
    s, cs = ("students", "classlist") if livesite() or get_forcelive() else ("test_students", "test_classlist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['departments', 'year', 'gender', 'location', 'timezone', 'hours', 'preferences', 'strengths']
    cmd = SQLWrapper(
        """
SELECT {s}.{departments}, {s}.{year}, {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}, {s}.{preferences}, {s}.{strengths}
FROM {s}
WHERE EXISTS (SELECT FROM {cs} WHERE {cs}.{year} = %s AND {cs}.{term} = %s and {cs}.{student_id} = {s}.{id})
        """,
        {'s':s, 'cs':cs}
    )
    return DBIterator(db._execute(cmd, [year, term]), cols, projection)


# returns data for students in classes for specified year and term (this is only used for computing counts, we don't need personal info)
def count_students_in_classes(department='', year=current_year(), term=current_term(), projection=[]):
    cs = "classlist" if livesite() or get_forcelive() else "test_classlist"
    department += '.%' if department else '%'
    cmd = SQLWrapper(
        """
SELECT COUNT ( DISTINCT {cs}.{student_id} ) AS "count"
FROM {cs}
WHERE {cs}.{year} = %s AND {cs}.{term} = %s AND {cs}.{class_number} LIKE %s
        """,
        {'cs':cs}
    )
    return list(DBIterator(db._execute(cmd, [year, term, department]), ["count"]))[0]['count']

def count_students_in_class(class_number, year=current_year(), term=current_term(), projection=[]):
    cs = "classlist" if livesite() or get_forcelive() else "test_classlist"
    cmd = SQLWrapper(
        """
SELECT COUNT (*) AS "count"
FROM {cs}
WHERE {cs}.{year} = %s AND {cs}.{term} = %s AND {cs}.{class_number} = %s
        """,
        {'cs':cs}
    )
    return list(DBIterator(db._execute(cmd, [year, term, class_number]), ["count"]))[0]['count']

# returns data for students in a particular class
def students_in_class(class_id, projection=[]):
    s, cs = ("students", "classlist") if livesite() or get_forcelive() else ("test_students", "test_classlist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['id', 'kerb', 'preferred_name', 'preferred_pronouns', 'full_name', 'email', 'departments', 'year', 'gender',
            'location', 'timezone', 'hours', 'properties', 'preferences', 'strengths', 'status']
    cmd = SQLWrapper(
        """
SELECT {s}.{id}, {s}.{kerb}, {s}.{preferred_name}, {s}.{preferred_pronouns}, {s}.{full_name}, {s}.{email}, {s}.{departments}, {s}.{year},
       {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}, {cs}.{properties}, {cs}.{preferences}, {cs}.{strengths}, {cs}.{status}
FROM {cs} JOIN {s} ON {s}.{id} = {cs}.{student_id}
WHERE {cs}.{class_id} = %s
        """,
        {'s':s, 'cs':cs}
    )
    return DBIterator(db._execute(cmd, [class_id]), cols, projection)

# this will return multiple rows for students in more than one group (which should not happen), empty groups will not be returned
def students_groups_in_class(class_id, projection=[]):
    s, cs, cgs, g = ("students", "classlist", "grouplist", "groups") if livesite() or get_forcelive() else ("test_students", "test_classlist", "test_grouplist", "test_groups")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['student_id', 'kerb', 'preferred_name', 'preferred_pronouns', 'full_name', 'email', 'departments', 'year', 'gender',
            'location', 'timezone', 'hours', 'properties', 'preferences', 'strengths', 'status', 'group_id', 'group_name', 'visibility', 'size', 'max']
    cmd = SQLWrapper(
        """
SELECT {s}.{id}, {s}.{kerb}, {s}.{preferred_name}, {s}.{preferred_pronouns}, {s}.{full_name}, {s}.{email}, {s}.{departments}, {s}.{year},
       {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}, {cs}.{properties}, {cs}.{preferences}, {cs}.{strengths}, {cs}.{status},
       {g}.{id}, {g}.{group_name}, {g}.{visibility}, {g}.{size}, {g}.{max}
FROM {cs} JOIN {s} ON {s}.{id} = {cs}.{student_id}
         LEFT JOIN {cgs} on {cgs}.{student_id} = {s}.{id} AND {cgs}.{class_id} = {cs}.{class_id}
         LEFT JOIN {g} on {g}.{id} = {cgs}.{group_id}
WHERE {cs}.{class_id} = %s
        """,
        {'s':s, 'cs':cs, 'cgs':cgs, 'g':g}
    )
    return DBIterator(db._execute(cmd, [class_id]), cols, projection)

# returns data for students in a particular group
def students_in_group(group_id, projection=[]):
    s, g = ("students", "grouplist") if livesite() or get_forcelive() else ("test_students", "test_grouplist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['id', 'kerb', 'preferred_name', 'preferred_pronouns', 'full_name', 'email', 'departments', 'year', 'gender',
            'location', 'timezone', 'hours']
    cmd = SQLWrapper(
        """
SELECT {s}.{id}, {s}.{kerb}, {s}.{preferred_name}, {s}.{preferred_pronouns}, {s}.{full_name}, {s}.{email}, {s}.{departments}, {s}.{year},
       {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}
FROM {g} INNER JOIN {s} ON {s}.{id} = {g}.{student_id}
WHERE {g}.{group_id} = %s
        """,
        {'s':s, 'g':g}
    )
    return DBIterator(db._execute(cmd, [group_id]), cols, projection)

# this will return multiple rows for students in more than one group (which should not happen), empty groups will not be returned
def class_counts(department='', year=current_year(), term=current_term()):
    from .utils import MAX_STATUS

    cs, g = ("classlist", "group") if livesite() or get_forcelive() else ("test_classlist", "test_groups")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['class_number', 'status', 'count', 'year', 'term']
    department += '.%' if department else '%'
    cmd = SQLWrapper(
        """
SELECT {cs}.{class_number}, {cs}.{status}, COUNT({cs}.{status}) AS {count}
FROM {cs}
WHERE {cs}.{year} = %s AND {cs}.{term} = %s AND {cs}.{class_number} LIKE %s
GROUP BY {cs}.{class_number}, {cs}.{status}
        """,
        {'cs':cs}
    )
    S = DBIterator(db._execute(cmd, [year, term, department]), cols, projection=['class_number','status','count'])
    res = {}
    for r in S:
        if r['class_number'] not in res:
            res[r['class_number']] = {'status':[0 for i in range(MAX_STATUS+1)]}
        res[r['class_number']]['status'][r['status']] = r['count']
        res[r['class_number']]['groups'] = 0
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['class_number', 'count', 'year', 'term']
    cmd = SQLWrapper(
        """
SELECT {g}.{class_number}, COUNT({g}.{id}) AS {count}
FROM {g}
WHERE {g}.{year} = %s AND {g}.{term} = %s AND {g}.{class_number} LIKE %s
GROUP BY {g}.{class_number}
        """,
        {'g':g}
    )
    S = DBIterator(db._execute(cmd, [year, term, department]), cols, projection=['class_number','count'])
    for r in S:
        res[r['class_number']]['groups'] = r['count']
    return res
