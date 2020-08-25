from psycopg2.sql import SQL
from psycodict.utils import IdentifierWrapper
from psetpartners import db
from psetpartners.app import is_livesite
from psetpartners.utils import current_year, current_term

# TODO: get rid of this once the .count method in psycodict is fixed!
def count_rows(table, query):
    _db = getdb()
    return sum(1 for _ in _db[table].search(query, projection="id"))

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

    def __getitem__(self,key):
        if key in ['students', 'groups', 'classlist', 'grouplist']:
            return self._db['test_'+key]
        else:
            return self._db[key]

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
    def grouplist(self):
        return self._db.test_grouplist

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

def students_in_class(class_number, year=current_year(), term=current_term()):
    s, c = ("students", "classlist") if is_livesite() else ("test_students", "test_classlist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['kerb', 'preferred_name', 'departments', 'year', 'gender', 'location', 'timezone', 'hours', 'properties', 'preferences', 'strengths']
    if not class_number:
        cols.remove('properties')
        return db[s].search({},projection=cols)
    cmd = SQLWrapper(
        """
SELECT {s}.{kerb}, {s}.{preferred_name}, {s}.{departments}, {s}.{year}, {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}, {c}.{properties}, {c}.{preferences}, {c}.{strengths}
FROM {c} INNER JOIN {s} ON {s}.{id} = {c}.{student_id}
WHERE {c}.{class_number} = %s and {c}.{year} = %s and {c}.{term} = %s
        """,
        {'s':s, 'c':c}
    )
    return DBIterator(db._execute(cmd, [class_number, year, term]), cols)

def students_in_group(group_id):
    s, g = ("students", "grouplist") if is_livesite() else ("test_students", "test_grouplist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['kerb', 'preferred_name', 'departments', 'year', 'gender', 'location', 'timezone', 'hours']
    cmd = SQLWrapper(
        """
SELECT {s}.{kerb}, {s}.{preferred_name}, {s}.{departments}, {s}.{year}, {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}
FROM {g} INNER JOIN {s} ON {s}.{id} = {g}.{student_id}
WHERE {g}.{group_id} = %s
        """,
        {'s':s, 'g':g}
    )
    return DBIterator(db._execute(cmd, [group_id]), cols)

def groups_in_class(class_number, year=current_year(), term=current_term()):
    g, c = ("groups", "grouplist") if is_livesite() else ("test_groups", "test_grouplist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['group_name', 'visibility', 'preferences', 'strengths']
    if not class_number:
        return db[g].search({},projection=cols)
    cmd = SQLWrapper(
        """
SELECT {g}.{group_name}, {g}.{visibility}, {g}.{preferences}, {g}.{strengths}
FROM {c} INNER JOIN {s} ON {g}.{id} = {c}.{group_id}
WHERE {c}.{class_number} = %s and {c}.{year} = %s and {c}.{term} = %s
        """,
        {'g':g, 'c':c}
    )
    return DBIterator(db._execute(cmd, [class_number, year, term]), cols)
