from psetpartners import db
from psetpartners.utils import (
    current_term,
    current_year,
    )

def class_options(year=current_year(), term=current_term()):
    return [(r["number"],r["number"] + " " + r["name"]) for r in db.classes.search({'year': year, 'term': term})]

def generate_group_name():
    while True:
        noun = db.nouns.random().capitalize()
        name = db.adjectives.random({'firstletter':noun[0]}).capitalize() + " " + noun
        if db.groups.lucky({'group_name':{'$ilike':name}}) is None:
            return name

