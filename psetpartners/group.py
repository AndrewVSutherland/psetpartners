import re
from psetpartners import db
from psetpartners.utils import (
    current_term,
    current_year,
    )

CLASS_NUMBER_RE = re.compile(r"^(\d+).(\d+)([A-Z]*)")

def class_number_key(s):
    r = CLASS_NUMBER_RE.match(s)
    return 260000*int(r.group(1)) + 26*int(r.group(2)) + (ord(r.group(3)[0]) if r.group(3) != '' else 0)

def current_classes(year=current_year(), term=current_term()):
    print ((year,term))
    classes = list(db.classes.search({"year": year, "term": term}, projection=["class_number","class_name"]))
    numbers = sorted([r["class_number"] for r in classes], key=class_number_key)
    names = { r["class_number"]: r["class_name"] for r in classes }
    return numbers, names
    

def generate_group_name():
    while True:
        noun = db.nouns.random()
        name = db.adjectives.random({'firstletter':noun[0]}).capitalize() + " " + noun.capitalize()
        if db.groups.lucky({'group_name':{'$ilike':name}}) is None:
            return name
