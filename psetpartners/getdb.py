from psetpartners import db
from psetpartners.utils import domain

_db = None

def getdb():
    global _db

    if domain() == "psetpartners.mit.edu":
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
    def nouns(self):
        return self._db.nouns

    @property
    def adjectives(self):
        return self._db.adjectives

