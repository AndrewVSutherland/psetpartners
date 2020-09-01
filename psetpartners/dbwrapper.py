from psycopg2.sql import SQL
from psycodict.utils import IdentifierWrapper
from . import db
from .app import livesite

# TODO: get rid of this once the .count method in psycodict is fixed!
def count_rows(table, query, forcelive=False):
    _db = getdb() if not forcelive else db
    return sum(1 for _ in _db[table].search(query, projection="id"))

_db = None

def getdb():
    global _db

    if livesite():
        return db
    if _db is None:
        _db = PsetPartnersTestDB(db)
    return _db

# list of tablenames X we want to redirect to test_X
test_redirects = ['instructors', 'students', 'groups', 'classlist', 'grouplist', 'messages', 'events', 'classes']

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


#TODO: add query and projection args to these functions

def students_in_class(class_id):
    s, c = ("students", "classlist") if livesite() else ("test_students", "test_classlist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['id', 'kerb', 'preferred_name', 'preferred_pronouns', 'full_name', 'email', 'departments', 'year', 'gender', 'location', 'timezone', 'hours', 'properties', 'preferences', 'strengths']
    cmd = SQLWrapper(
        """
SELECT {s}.{id}, {s}.{kerb}, {s}.{preferred_name}, {s}.{preferred_pronouns}, {s}.{full_name}, {s}.{email}, {s}.{departments}, {s}.{year}, {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}, {c}.{properties}, {c}.{preferences}, {c}.{strengths}
FROM {c} INNER JOIN {s} ON {s}.{id} = {c}.{student_id}
WHERE {c}.{class_id} = %s
        """,
        {'s':s, 'c':c}
    )
    return DBIterator(db._execute(cmd, [class_id]), cols)

def students_in_group(group_id):
    s, g = ("students", "grouplist") if livesite() else ("test_students", "test_grouplist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['id', 'kerb', 'preferred_name', 'preferred_pronouns', 'full_name', 'email', 'departments', 'year', 'gender', 'location', 'timezone', 'hours']
    cmd = SQLWrapper(
        """
SELECT {s}.{id}, {s}.{kerb}, {s}.{preferred_name}, {s}.{preferred_pronouns}, {s}.{full_name}, {s}.{email}, {s}.{departments}, {s}.{year}, {s}.{gender}, {s}.{location}, {s}.{timezone}, {s}.{hours}
FROM {g} INNER JOIN {s} ON {s}.{id} = {g}.{student_id}
WHERE {g}.{group_id} = %s
        """,
        {'s':s, 'g':g}
    )
    return DBIterator(db._execute(cmd, [group_id]), cols)

def groups_in_class(class_id):
    g, c = ("groups", "grouplist") if livesite() else ("test_groups", "test_grouplist")
    # note that the order of cols must match the order they appear in the SELECT below
    cols = ['group_name', 'visibility', 'preferences', 'strengths']
    cmd = SQLWrapper(
        """
SELECT {g}.{group_name}, {g}.{visibility}, {g}.{preferences}, {g}.{strengths}
FROM {c} INNER JOIN {s} ON {g}.{id} = {c}.{group_id}
WHERE {c}.{class_id} = %s
        """,
        {'g':g, 'c':c}
    )
    return DBIterator(db._execute(cmd, [class_id]), cols)
