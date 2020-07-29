from psetpartners import db

def generate_group_name():
    while True:
        noun = db.nouns.random().capitalize()
        name = db.adjectives.random({'firstletter':noun[0]}).capitalize() + " " + noun
        if db.groups.lucky({'group_name':{'$ilike':name}}) is None:
            return name

