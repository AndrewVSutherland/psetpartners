
from psetpartners import db
from flask_login import UserMixin


class Student(UserMixin):
    properties = sorted(db.students.col_type) + ["id"]
    def __init__(self, identifier):
        self.identifier = identifier
        data = db.students.lookup(identifier, projection=Student.properties)
        if data is not None:
            self.__dict__.update(data)
            # For now, no password checking
            self._authenticated = True

    def save(self):
        db.students.update({"identifier": self.identifier}, {col: getattr(self, col, None) for col in db.students.search_cols})
