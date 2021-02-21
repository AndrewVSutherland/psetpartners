import datetime
from .dbwrapper import getdb, db_islive
from .utils import hours_from_default, current_year, current_term, null_logger
from collections import defaultdict
from math import sqrt, floor, ceil
from functools import lru_cache

# cols from student table relevant to matching
student_properties = ["id", "kerb", "blocked_kerbs", "gender", "hours", "year", "departments", "timezone"]

# preferences relevent to matching other than size
affinities = ["gender_affinity", "confidence_affinity", "commitment_affinity", "departments_affinity", "year_affinity"]
styles = ["forum", "start", "style"]

class MatchError(ValueError):
    pass

def initial_assign(to_match, sizes):
    # In practice, 3-4 is by far the most common requested size (and most set no preference at all)
    # We aim for a mix of 3's and 4's (3 gives room to grow, 4 reduces impact of non-responsive partners)
    # We first try to fulfill any other size requests: 9 then 5 then 2.
    # Note that this function will destroy the sizes dictionary.
    groups = {}
    def make_group(source):
        return Group([to_match[i] for i in source])
    def add(source, n=None, fill=[]):
        if n is None:
            G = make_group(source)
        else:
            G = source[:n]
            if len(G) < n:
                fill_amount = n - len(G)
                G.extend(fill[:fill_amount])
                fill[:fill_amount] = []
            G = make_group(G)
            if len(G) != n:
                print(n)
                print(len(G))
                print(G)
                raise RuntimeError
            source[:n] = []
        for S in G.students:
            groups[S.id] = G
    for m in [9,5,4,3,2]:
        while sizes[m]:
            add(sizes[m], m, sizes[0])
    remainder = sizes[3] + sizes[0]
    if len(remainder) == 5:
        # Unless there's a preference for 3 or bad time overlap, we make a group of 5
        G = make_group(remainder)
        want3 = [i for i in sizes[3] if to_match[i].preferences["size"][1] >= 1]
        if 0 < len(want3) < 3 or G.schedule_overlap() < 4:
            for i in remainder:
                if i not in want3:
                    want3.append(i)
                    if len(want3) == 3:
                        break
        if len(want3) > 3:
            want3 = want3[:3]
        if len(want3) == 3:
            add(want3)
            add([ i for i in remainder if i not in want3])
        else:
            add(remainder)
    elif len(remainder) == 4:
        G = make_group(remainder)
        if G.schedule_overlap() < 4:
            add(remainder, 2)
            add(remainder)
        else:
            add(remainder)
    elif len(remainder) == 3:
        add(remainder)
    elif len(remainder) == 2:
        add(remainder)
    elif len(remainder) == 1:
        # Have to add into one of the existing groups
        i = remainder[0]
        for m in [5, 9, 2]:
            if any(len(G) == m for G in groups.values()):
                for G in groups.values():
                    if len(G) == m:
                        G.add(to_match[i])
                        groups[i] = G
                        break
                break
    else:
        assert len(remainder) > 5
        while len(remainder):
            if len(remainder)%7 in [2,3,5,6]:
                add(remainder,3)
            if len(remainder)%7 in [1,4]:
                if len(remainder) == 4 and make_group(remainder).schedule_overlap() < 4:
                    add(remainder,2)
                    add(remainder,2)
                else:
                    add(remainder,4)
            if len(remainder)%7 == 0:
                add(remainder,4)
                add(remainder,3)
    return groups

def evaluate_swaps(groups):
    improvements = [(groups[i].evaluate_swap(i, j, groups[j]), i, j) for i in groups for j in groups if i < j]
    improvements.sort(reverse=True)
    return improvements

def run_swaps(to_match, groups, improvements):
    while improvements and improvements[0][0] > 0:
        # improvements is sorted so that the best swap is first.
        changed = []
        # execute_swap swaps the first entry of improvements, removing all affected values from improvements and inserting them into change, then returns the largest changed value.
        execute_swap(to_match, groups, improvements, changed)
        improvements.extend(changed)
        improvements.sort(reverse=True)

def execute_swap(to_match, groups, improvements, changed):
    # Execute the swap with highest value, which is the first entry in the improvements list
    value, i, j = improvements.pop(0)
    # First change the actual groups (this will update these groups indexed under other ids)
    Gj = groups[i].swap(i, to_match[j])
    Gi = groups[j].swap(j, to_match[i])
    # Now change the pointers from i and j
    groups[i] = Gi
    groups[j] = Gj
    # Now update values of every swap containing one of the members of one of these groups
    changed.append((-value, i, j))
    ctr = 0
    biggest = 0
    while ctr < len(improvements):
        old, a, b = improvements[ctr]
        if groups[a] is Gi or groups[a] is Gj or groups[b] is Gi or groups[b] is Gj:
            del improvements[ctr]
            # Swap value is symmetric
            new = groups[a].evaluate_swap(a, b, groups[b])
            if new > biggest:
                biggest = new
            changed.append((new, a, b))
        else:
            ctr += 1
    return biggest

def refine_groups(to_match, groups):
    # Check the groups to see if there are issues that can be resolved by changing group size
    G = set(groups.values())
    rerun = False
    for group in G:
        n = len(group)
        if n >= 9 and group.schedule_overlap() < 3:
            rerun = True
            # split in thirds
            L = [Group(group.students[:n//3]), Group(group.students[n//3:(2*n)//3:]), Group(group.students[(2*n)//3:])]
            for A in L:
                for S in A.students:
                    groups[S.id] = A
        elif (n in [4,5] and group.schedule_overlap() < 2 or
            n > 5 and group.schedule_overlap() < 3):
            rerun = True
            # split in half
            L = [Group(group.students[:n//2]), Group(group.students[n//2:])]
            for A in L:
                for S in A.students:
                    groups[S.id] = A
    if rerun:
        improvements = evaluate_swaps(groups)
        run_swaps(to_match, groups, improvements)
        return refine_groups(to_match, groups)
    else:
        # Now check for violated requirements
        rerun = True
        unsatisfied = []
        for group in G:
            # Failed matching based on student requirements; throw them out of the pool
            unsat = [S for S in group.students if group.contribution(S) < -162]
            if unsat:
                rerun = True
                sat = [S for S in group.students if S not in unsat]
                if len(sat) <= 1:
                    # give up on this group, we will try to match its former members after all groups have been formed
                    unsat = [S for S in group.students]
                    sat = []
                else:
                    new_group = Group(sat)
                    for S in sat:
                        groups[S.id] = new_group
                for U in unsat:
                    del groups[U.id]
                unsatisfied .extend([U.kerb for U in unsat])
        if rerun:
            improvements = evaluate_swaps(groups)
            run_swaps(to_match, groups, improvements)
        return unsatisfied

def match_all(rematch=False, forcelive=False, preview=False, vlog=null_logger()):
    """
    Returns a dictionary with three attributes: 'groups', 'unmatched_only', 'unmatched_other'
    """
    db = getdb(forcelive)
    vlog.info("matching %s database%s"%("live" if db_islive(db) else "test", " in preview mode" if preview else ""))
    year = current_year()
    term = current_term()
    query = {'active':True, 'year': year, 'term': term }
    if not rematch:
        today = datetime.datetime.now().date()
        assert datetime.datetime.now().hour >= 22
        query['match_dates'] = {'$contains': today}
    results = {}
    # TODO make classes search only return classes with students of status 2 or 5 (requires exists join, add to dbwrapper)
    for c in db.classes.search(query, ["id", "class_name", "class_number"]):
        if not preview and not rematch:
            db.classlist.update({'class_id': c['id'], 'status': 2}, {'status': 5},resort=False)
        n = len(list(db.classlist.search({'class_id': c['id'], 'status': 2 if preview else 5},projection='id')))
        if n:
            vlog.info("Matching %d students in pool for %s %s" % (n, c['class_number'], c['class_name']))
            groups, only, other = matches(c, preview, vlog)
            results[c['id']] = {'groups': groups, 'unmatched_only': only, 'unmatched_other': other}
    return results

def matches(clsrec, preview=False, vlog=null_logger()):
    """
    Creates groups for all classes in a given year and term.
    Returns three lists: a list of groups, a list of unmatched kerbs of one students in a pool,
    and a list of other unmatched students
    """
    db = getdb()
    student_data = {rec["id"]: {key: rec.get(key) for key in student_properties} for rec in db.students.search(projection=3)}
    clsid = clsrec["id"]
    to_match = {}
    # Status:
    # 0 = unchosen
    # 1 = in group
    # 2 = in pool
    # 3 = requested match
    # 4 = emailed people
    # 5 = to be matched (2 => 5 at midnight on match date, prevents students in pool from doing anything while we match)
    for rec in db.classlist.search({"class_id": clsid, "status": 2 if preview else 5}, ["student_id", "preferences", "strengths", "properties"]):
        properties = dict(rec["properties"])
        properties.update(student_data[rec["student_id"]])
        to_match[rec["student_id"]] = Student(properties, rec["preferences"], rec["strengths"])
    # We handle small cases, where the matches are determined, first
    N = len(to_match)
    # Should fix this to use existing groups
    groups = {}
    if N == 0:
        return [], [], []
    elif N == 1:
        vlog.info("%s assignments complete" % (clsrec["class_number"]))
        S = next(iter(to_match.values()))
        vlog.warning("Only student %s unmatched in %s" % (S.kerb, clsrec["class_number"]))
        return [], [S.kerb], []
    elif N in [2, 3]:
        # Only one way to group
        G = Group(list(to_match.values()))
        for S in G.students:
            groups[S.id] = G
        # Might violate a requirement
        unmatched = refine_groups(to_match, groups)
    else:
        # We first need to determine which size groups to create
        for limit in [9, 5, 4, 3, 2]:
            for threshold in range(2,6):
                sizes = defaultdict(list) # keys 2, 3, 3.5 (3 or 4), 4, 5 (5-8), 9 (9+), 0 (flexible)
                for i, student in to_match.items():
                    best, priority = student.preferences.get("size", (0, 0))
                    best = 0 if best == "3.5" else int(best)    # 3.5 = 3 or 4 is our default, so treat as flexible
                    if priority < threshold or limit == 2:
                        # If we can't succeed using groups of only 2 and 3, we make everyone flexible.
                        best = 0
                    elif best > limit:
                        best = limit
                    sizes[best].append(i)
                flex = 0
                if len(sizes[2]) % 2:
                    # odd number of people wanting pairs
                    flex += 1
                if len(sizes[3]) in [1,2,5]:
                    flex += 3 - (len(sizes[3]) % 3)
                if len(sizes[4]) in [1,2,3,7]:
                    flex += 4 - (len(sizes[4]) % 4)
                if len(sizes[5]) in [1,2,3,4,9]:
                    flex += 5 - (len(sizes[5]) % 5)
                if 0 < len(sizes[9]) < 9:
                    flex += 9 - (len(sizes[9]) % 9)
                if flex <= len(sizes[0]):
                    # Have enough flexible students
                    break
            else:
                # No arrangement will satisfy everyone's requirements
                # We prohibit groups of 9+ then 5+ since these are harder to create.
                # If that's still not enough, we make everyone flexible.
                continue
            break
        # Now there are enough students who are flexible on their group size that we can create groups.
        #print(limit, threshold, sizes, N, len(to_match))
        groups = initial_assign(to_match, sizes)
        #print(groups)
        improvements = evaluate_swaps(groups)
        run_swaps(to_match, groups, improvements)
        unmatched = refine_groups(to_match, groups)
    # Print warnings for groups with low compatibility and for non-satisfied requirements
    vlog.info("%s assignments complete" % clsrec["class_number"])
    for grp in set(groups.values()):
        grp.print_warnings(vlog)
    if unmatched:
        vlog.warning("Unmatched students %s in %s" % (unmatched, clsrec["class_number"]))
    gset = set(groups.values())
    return [[S.kerb for S in group.students] for group in gset], [], unmatched

# TODO: Our lives would be simpler if the size pref values where 2,4,8,16 rather than 2,3,5,9 (with the same meaning)
def size_pref_from_size(size):
    if size <= 2:
        return '2'
    if size <= 4:
        return '3'
    if size <= 8:
        return '5'
    return '9'

def group_member (db, class_id, kerb, g=None):
    """
    Create a student object for a student in the group g (where g is a dictionary from db.groups.search).
    The students preferences are updated to reflect the groups preferences when specified, as well as its current size
    """
    student_data = db.students.lookup(kerb, student_properties)
    rec = db.classlist.lucky({"class_id": class_id, 'kerb': kerb}, ["properties", "preferences", "strengths"])
    if not rec:
        return None
    properties = dict(rec["properties"])
    properties.update(student_data)
    if g:
        for k in styles + ['size']:
            if k in g['preferences']:
                if k not in rec['preferences']:
                    rec['strengths'][k] = 3
                elif rec['preferences'][k] != g['preferences'][k]:
                    rec['strengths'][k] = 1 # if student actually preferred something other than the group preference, make the strength weak
                rec['preferences'][k] = g['preferences'][k]
    return Student(properties, rec['preferences'], rec['strengths'])

def rank_groups (class_id, kerb):
    """
    Given a class and a student, returns a list of groups that could accomodate the student ranked by relative compatibility,
    where relative compatibility is the change in compatibility score for the group that results form adding the student.
    returns a list of triples (group_id, visibility, relative compatibility)

    Groups with visibility=0 or size=max are excluded, as are groups the student previously left, but public groups are included.
    This is only for the purpose of informing the student, students should never by put into a public group by the system.

    Because we are dealing with existing groups rather than forming new ones we override student preferences for start/style/forum/size
    with whatever the group preferences if specified, since they presumably agreed to them (but we adjust the strength based on
    the students preferences for the class).  In addition, if the group has no preferred size we will make it 1 larger than it is now
    (this is needed to make sure it conflicts with prospective students who want a different size).
    """

    db = getdb()
    res = []
    G = [g for g in db.groups.search({'class_id': class_id, 'visibility': {'$gte': 1}, 'request_id': None}, projection=['id','group_name','visibility','size','max', 'preferences']) if
         g['max'] is None or g['size'] < g['max']] # TODO write a SQL query to handle the size filter
    G = [g for g in G if not db.grouplistleft.lucky({'group_id': g['id'], 'kerb': kerb}, projection='id')]
    student = group_member(db, class_id, kerb)
    for g in G:
        if not 'size' in g['preferences']:
            g['preferences']['size'] = size_pref_from_size(g['size']+1) # default is to prefer to be 1 larger than we are
        # We expect the student is not already in a group in this class, but we may as well handle this case
        students = [group_member(db, class_id, k, g) for k in db.grouplist.search({'group_id': g['id']}, projection='kerb') if k != kerb]
        if not students:
            continue
        if len(students) == 1: # compatibility of a 1-student group is not really well-defined, treat as 0
            delta = Group(students + [student]).compatibility()
        else:
            delta = Group(students + [student]).compatibility() - Group(students).compatibility()
        res.append((g['id'], g['visibility'], delta))
    return sorted(res, key=lambda x: x[2], reverse=True)

class Student(object):
    def __init__(self, properties, preferences, strengths):
        self.id = properties["id"]
        self.kerb = properties["kerb"]
        offset = hours_from_default(properties["timezone"])
        hours = properties["hours"]
        self.hours = tuple(hours[(i-offset)%168] for i in range(168))
        self.properties = properties
        self.preferences = {}
        for k, v in preferences.items():
            self.preferences[k] = (v, strengths.get(k, 3))

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, Student) and other.id == self.id

    def __repr__(self):
        return self.kerb
        #return "%s(%s)" % (self.kerb, self.id)

    def compatibility(self, G):
        if isinstance(G, Student):
            Gplus = Group([G, self])
        else:
            Gplus = Group(G.students + [self])
        return Gplus.compatibility()

    def score(self, quality, G):
        """
        Contribution to the compatibility score from this user's preferences about ``quality``.

        INPUT:

        - ``quality`` -- one of the keys for the ``preferences`` dictionary,
            or one of a few other contributing factors: "hours", "blocked_kerbs"
        - ``G`` -- a Group, which may or may not contain this student.
        """
        if isinstance(G, Student):
            G = Group([G])
        def check(T):
            if quality in styles:
                a, s = self.preferences.get(quality, (None, 0))
                b, _ = T.preferences.get(quality, (None, 0))
            elif quality in ["blocked_kerbs"] + affinities:
                prop = quality.replace("_affinity", "")
                a = self.properties.get(prop)
                b = T.properties.get(prop)
            if quality == "blocked_kerbs":
                return not (T.properties.get("kerb") in a)
            if a is None or b is None:
                # If we don't know the relevant quantity for one of the students
                # it doesn't contribute positively but also doesn't impose a
                # penalty for mismatching
                return None
            #if quality == "hours":
            #    # Time overlap below 4 hours will start producing negative scores
            #    # One might change this measure in the following ways:
            #    # * take account the forum (video is much more synchronous than text)
            #    # * compare the times available for EVERYONE in the group
            #    overlap = sum(x and y for (x,y) in zip(a,b))
            #    if overlap < 4:
            #        return -20**(4-overlap)
            if quality in styles:
                return (a == b)
            if quality in affinities:
                pref = self.preferences.get(quality, (None, 0))[0]
                if pref == '3':
                    return (a != b)
                elif quality == "departments_affinity":
                    return bool(set(a) & set(b))
                elif pref is not None:
                    return (a == b)
            raise RuntimeError

        others = [T for T in G.students if T.id != self.id]
        if quality == "blocked_kerbs":
            if not all(check(T) for T in others):
                return -10**10
            return 0
        pref, s = self.preferences.get(quality, (None, 0))
        if pref is None:
            return 0
        if quality == "size":
            if pref == '2':
                satisfied = (len(G) == 2)
                d = 0 if satisfied else max(len(G)/2,2/len(G))
            elif pref == '3':
                satisfied = (len(G) == 3)
                d = 0 if satisfied else max(len(G)/3,3/len(G))
            elif pref == '3.5':
                satisfied = (3 <= len(G) <= 4)
                d = 0 if satisfied else max(len(G)/4,3/len(G))
            elif pref == '4':
                satisfied = (len(G) == 4)
                d = 0 if satisfied else max(len(G)/4,4/len(G))
            elif pref == '5':
                satisfied = (5 <= len(G) <= 8)
                d = 0 if satisfied else max(len(G)/8,5/len(G))
            elif pref == '9':
                satisfied = (9 <= len(G))
                d = 0 if satisfied else 9/len(G)
            else:
                assert False, "Invalid size preference %s, should be a string in ['2','3','3.5','4','5','9'] or none" % pref
            if satisfied:
                return 3**s
            elif s == 5:
                return -10**6
            else:
                return -ceil(2*d)^s
        # Affinities aren't linear
        if quality in affinities:
            if pref == '2':
                # check(T) is None is accepted as an unknown
                satisfied = all(not (check(T) is False) for T in others)
            else:
                satisfied = any(check(T) for T in others)
            if satisfied:
                # scale for appropriate comparison with other qualities
                return 3**s
            elif s == 5:
                return -10**6
            else:
                return 0
        else:
            def score_one(T):
                c = check(T)
                if c is None:
                    return 0
                elif c:
                    return 3**s
                elif s == 5:
                    return -10**6
                else:
                    return 0
            return sum(score_one(T) for T in others)


class Group(object):
    def __init__(self, students):
        """ Creates an instance of Group from a list of instances of Student (which should all be in the same class) """
        self.students = students

    def by_id(self, n):
        for S in self.students:
            if S.id == n:
                return S
        raise ValueError(n, [S.id for S in self.students])

    def add(self, student):
        self.students.append(student)

    def __len__(self):
        return len(self.students)

    def __hash__(self):
        return hash(frozenset(self.students))

    def __eq__(self, other):
        return isinstance(other, Group) and set(self.students) == set(other.students)

    def __repr__(self):
        students = ["%s%s" % (S, "(%s)" % (self.contribution(S)) if self.contribution(S) < 0 else "") for S in self.students]
        return "Group(size=%s, score=%s, overlap=%s) %s" % (len(self), self.compatibility(), self.schedule_overlap(), " ".join(students))

    def schedule_overlap(self):
        hour_data = [S.hours for S in self.students]
        return sum(all(available) for available in zip(*hour_data))

    @lru_cache(2)
    def secondary_schedule_score(self):
        n = len(self.students)
        if n < 3:
            return 0
        hour_data = [[S.hours for S in self.students[:i]+self.students[i+1:]] for i in range(n)]
        return round(sum([sum(all(available) for available in zip(*hour_data[i])) for i in range(n)]) / n)

    @lru_cache(2)
    def schedule_score(self):
        """
        Score based on how much overlap there is in the hours scheduled
        """
        overlap = self.schedule_overlap()
        if overlap < 4:
            return -20**(4-overlap)
        elif overlap < 20:
            return 5*(overlap - 4)
        else:
            return 80 + 5 * floor(sqrt(overlap - 20))

    @lru_cache(10)
    def contribution(self, student):
        return sum(student.score(q, self) for q in affinities + styles + ['size'])

    @lru_cache(2)
    def compatibility(self):
        # note that we don't want to average primary and secondary schedule scores, we want to sum them
        # averaging will potentially make a horrible primary score half as bad and we don't want to do that (especially when computing deltas)
        # this potentially favors groups of size 3 over groups of size 2 (which have no secondary score), but that's OK
        schedule_score = self.schedule_score() if len(self.students) < 3 else (self.schedule_score() + self.secondary_schedule_score())
        return sum(self.contribution(student) for student in self.students) + schedule_score

    def evaluate_swap(self, thisid, otherid, othergrp):
        if self == othergrp:
            return 0
        revised_self = Group([S for S in self.students if S.id != thisid] + [othergrp.by_id(otherid)])
        revised_other = Group([S for S in othergrp.students if S.id != otherid] + [self.by_id(thisid)])
        return (revised_self.compatibility() + revised_other.compatibility()) - (self.compatibility() + othergrp.compatibility())

    def swap(self, thisid, other):
        self.schedule_score.cache_clear()
        self.compatibility.cache_clear()
        self.contribution.cache_clear()
        self.students = [S for S in self.students if S.id != thisid] + [other]
        return self

    def print_warnings(self, vlog):
        for S in self.students:
            for quality in affinities + styles + ["blocked_kerbs"]:
                if S.score(quality, self) < 0:
                    vlog.warning("Group breaks %s's %s requirement" % (S.kerb, quality))
        overlap = self.schedule_overlap()
        if overlap < 4:
            vlog.warning("Small time overlap: %s hours" % overlap)
