def get_kerb_data (kerb, client_id, client_secret, raw=False):
    import requests
    from psetpartners import db
    from psetpartners.student import course_number_key

    assert kerb
    headers = {'Accept': 'application/json', 'client_id': client_id, 'client_secret': client_secret}
    endpoint = 'https://mit-people-v3.cloudhub.io/people/v3/people/' + kerb
    resp = requests.get(endpoint, headers=headers).json()
    data = resp.get('item',{})
    if not data or data.get('kerberosId','') != kerb:
        return {}
    if raw:
        return data
    res = { 'kerb': kerb }
    full_name = data.get('displayName','').strip()
    if full_name:
        res['full_name'] = full_name
    homepage = data.get('website','')
    if homepage:
        res['homoepage'] = homepage
    affiliations = data.get('affiliations',[])
    for a in affiliations:
        if a.get('type','') == 'student':
            year = a.get('classYear',None)
            year = 5 if year == 'G' else ( int(year) if year in ['1','2','3','4'] else None )
            if year:
                res['year'] = year
            if a.get('departments',{}):
                depts = [r['code'].strip() for r in a['departments'] if r.get('code')]
                depts = [c for c in depts if c and db.departments.lookup(c)]
                res['departments'] = sorted(depts, key=course_number_key)
            email = a.get('email','').strip()
            if email and not email.endswith('@mit.edu'):
                res['email'] = email
    return res
