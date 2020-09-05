from psetpartners import db
from psetpartners.utils import hours_from_default, current_year, current_term
from collections import defaultdict
from math import sqrt, floor
import heapq
from functools import lru_cache

class MatchError(ValueError):
    pass

def initial_assign(to_match, sizes):
    # In practice, 3-4 is by far the most common requested size.  In order to have room for expansion, we aim for 3.
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
                raise RuntimeError
            source[:n] = []
        for S in G.students:
            groups[S.id] = G
    for m in [9,5,2]:
        # 9-5-2 is one of my favorite card games.  See https://debitcardcasino.ca/games/2018/04/19/9-5-2-rules-canada/ for a version of the rules.
        while sizes[m]:
            add(sizes[m], m, sizes[0])
    remainder = sizes[3] + sizes[0]
    if len(remainder) == 5:
        # Unless there's a strong preference for 3 or bad time overlap, we keep this case in a group of 5.
        G = make_group(remainder)
        strong = [i for i in sizes[3] if to_match[i].preferences["size"][1] > 3]
        if 0 < len(strong) <= 3 or G.schedule_overlap() < 4:
            for i in remainder:
                if i not in strong:
                    strong.append(i)
                    if len(strong) == 3:
                        break
            other = [i for i in remainder if i not in strong]
            add(strong)
            add(other)
        else:
            add(remainder)
    elif len(remainder) == 4:
        G = make_group(remainder)
        if G.schedule_overlap() < 4:
            add(remainder, 2)
            add(remainder, 2)
        else:
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
        while len(remainder) % 3:
            add(remainder, 4)
        while remainder:
            add(remainder, 3)
    return groups

def evaluate_swaps(groups):
    improvements = [(groups[i].evaluate_swap(i, j, groups[j]), i, j) for i in groups for j in groups if i < j]
    improvements.sort(reverse=True)
    return improvements

def run_swaps(to_match, groups, improvements):
    while improvements[0][0] > 0:
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
            unsat = [S for S in group.students if group.contribution(S) < 0]
            if unsat:
                rerun = True
                unsatisfied.extend([(U.kerb, "requirement") for U in unsat])
                sat = [S for S in group.students if S not in unsat]
                new_group = Group(sat)
                if len(new_group) == 1:
                    raise NotImplementedError
                for U in unsat:
                    del group[U.id]
                for S in sat:
                    groups[S.id] = new_group
        if rerun:
            improvements = evaluate_swaps(groups)
            run_swaps(to_match, groups, improvements)
        return unsatisfied

def match_all(dryrun=True):
    year = current_year()
    term = current_term()
    for clsrec in db.classes.search({"year": year, "term": term}, ["id", "class_name", "class_number"]):
        matches(clsrec, dryrun)

def matches(clsrec, dryrun=True):
    """
    Creates groups for all classes in a given year and term.
    """
    student_data = {rec["id"]: {key: rec.get(key) for key in ["id", "kerb", "blocked_student_ids", "gender", "hours", "year", "departments", "timezone"]} for rec in db.students.search(projection=3)}
    clsid = clsrec["id"]
    to_match = {}
    # Status:
    # 0 = unchosen
    # 1 = in group
    # 2 = in pool
    # 3 = requested match
    # 4 = emailed people
    for rec in db.classlist.search({"class_id": clsid, "status": 2}, ["student_id", "preferences", "strengths", "properties"]):
        properties = dict(rec["properties"])
        properties.update(student_data[rec["student_id"]])
        to_match[rec["student_id"]] = Student(properties, rec["preferences"], rec["strengths"])
    # We handle small cases, where the matches are determined, first
    N = len(to_match)
    # Should fix this to use existing groups
    groups = {}
    if N == 0:
        return [], []
    elif N == 1:
        S = next(iter(to_match.values()))
        if dryrun:
            print("%s %s assignments complete" % (clsrec["class_number"], clsrec["class_name"]))
            print("Only student %s unmatched" % S.kerb)
        else:
            return [], [(S.kerb, "only")]
    elif N in [2, 3]:
        # Only one way to group
        G = Group(list(to_match.values()))
        for S in G.students:
            groups[S.id] = G
        # Might violate a requirement
        unmatched = refine_groups(to_match, groups)
        G = next(iter(groups.values()))
        if dryrun:
            print("%s %s assignments complete" % (clsrec["class_number"], clsrec["class_name"]))
            print(G)
        else:
            return [[S.kerb for S in G.students], unmatched]
    else:
        # We first need to determine which size groups to create
        for limit in [9, 5, 3, 2]:
            for threshold in range(2,6):
                sizes = defaultdict(list) # keys 2, 3 (3 or 4), 5 (5-8), 9 (9+), 0 (flexible)
                size_lookup = {}
                for i, student in to_match.items():
                    best, priority = student.preferences.get("size", (0, 0))
                    best = int(best)
                    if priority < threshold or limit == 2:
                        # If we can't succeed using groups of only 2 and 3, we make everyone flexible.
                        best = 0
                    elif best > limit:
                        best = limit
                    sizes[best].append(i)
                    size_lookup[i] = best
                flex = 0
                if len(sizes[2]) % 2:
                    # odd number of people wanting pairs
                    flex += 1
                if len(sizes[3]) in [1,2,5]:
                    flex += 3 - (len(sizes[3]) % 3)
                if len(sizes[5]) in [1,2,3,4,9]:
                    flex += 5 - (len(sizes[5]) % 5)
                if 0 < len(sizes[9]) < 9:
                    flex += 9 - (len(sizes[9]) % 5)
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
        removed = refine_groups(to_match, groups)
        # Print warnings for groups with low compatibility and for non-satisfied requirements
        if dryrun:
            print("%s %s assignments complete" % (clsrec["class_number"], clsrec["class_name"]))
            for grp in set(groups.values()):
                print(grp)
        else:
            gset = set(groups.values())
            return [[S.kerb for S in group] for group in gset], removed

affinities = ["gender", "confidence_affinity", "commitment_affinity", "departments_affinity", "year_affinity"]
styles = ["forum", "start", "style"]


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
            or one of a few other contributing factors: "hours", "blocked_student_ids"
        - ``G`` -- a Group, which may or may not contain this student.
        """
        if isinstance(G, Student):
            G = Group([G])
        def check(T):
            if quality in styles:
                a, s = self.preferences.get(quality, (None, 0))
                b, _ = T.preferences.get(quality, (None, 0))
            elif quality in ["blocked_student_ids"] + affinities:
                prop = quality.replace("_affinity", "")
                a = self.properties.get(prop)
                b = T.properties.get(prop)
                s = self.preferences.get(quality, (None, 0))[1]
                t = T.preferences.get(quality, (None, 0))[1]
            if quality == "blocked_student_ids":
                return not (T.properties.get("id") in a)
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
        if quality == "blocked_student_ids":
            if not all(check(T) for T in others):
                return -10**10
            return 0
        pref, s = self.preferences.get(quality, (None, 0))
        if pref is None:
            return 0
        if quality == "size":
            if pref == '2':
                satisfied = (len(G) == 2)
            elif pref == '3':
                satisfied = (3 <= len(G) <= 4)
            elif pref == '5':
                satisfied = (5 <= len(G) <= 8)
            elif pref == '9':
                satisfied = (9 <= len(G))
            if satisfied:
                return (len(G) - 1) * 3**s
            elif s == 5:
                return -10**6
            else:
                return 0
        # Affinities aren't linear
        if quality in affinities:
            if pref == '2':
                # check(T) is None is accepted as an unknown
                satisfied = all(not (check(T) is False) for T in others)
            else:
                satisfied = any(check(T) for T in others)
            if satisfied:
                # scale for appropriate comparison with other qualities
                return (len(G) - 1) * 3**s
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
        return sum(student.score(q, self) for q in affinities + styles)

    @lru_cache(2)
    def compatibility(self):
        return sum(self.contribution(student) for student in self.students) + self.schedule_score()

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

    def print_warnings(self):
        for S in self.students:
            for quality in affinities + styles + ["blocked_student_ids"]:
                if S.score(quality, self) < 0:
                    print("Group breaks %s's %s requirement" % (S.kerb, quality))
        overlap = self.schedule_overlap()
        if overlap < 4:
            print("Small time overlap: %s hours" % overlap)
