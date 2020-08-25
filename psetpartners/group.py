from . import db

def generate_group_name():
    while True:
        noun = db.nouns.random()
        name = db.adjectives.random({'firstletter':noun[0]}).capitalize() + " " + noun.capitalize()
        if db.groups.lucky({'group_name':{'$ilike':name}}) is None:
            return name
