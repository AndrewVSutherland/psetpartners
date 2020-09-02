from psetpartners import db
from collections import defaultdict
from math import sqrt, floor

def compatible_sizes(G, S, size_lookup):
    size = size_lookup[S.id]
    if size == 2:
        return isinstance(G, Student) and size_lookup[G.id] in [0, 2]
    elif size == 3:
        return (isinstance(G, Student) and size_lookup[G.id] in [0, 3] or
                isinstance(G, Group) and len(G) < 4 and all(size_lookup[T.id] in [0, 3] for T in G.students))
    elif size == 5:
        return (isinstance(G, Student) and size_lookup[G.id] in [0, 5] or
                isinstance(G, Group) and len(G) < 8 and all(size_lookup[T.id] in [0, 5] for T in G.students))
    elif size == 9:
        return (isinstance(G, Student) and size_lookup[G.id] in [0, 9] or
                isinstance(G, Group) and all(size_lookup[T.id] in [0, 9] for T in G.students))
    else: # size == 0
        if isinstance(G, Student):
            return True
        cursize = max(size_lookup[T.id] for T in G.students)
        return (cursize in [0, 9] or
                cursize == 3 and len(G) < 4 or
                cursize == 5 and len(G) < 8)

def assign_one(to_match, groups, compatibilities, size_lookup):
    """
    Picks a student from the ``to_match`` dictionary and assigns them to a group

    INPUT:

    - ``to_match`` -- a dictionary with keys student system ids and values the corresponding student object
    - ``groups`` -- a dictionary with keys the negation of group ids and values the corresponding Group object
    - ``compatibilities`` -- a dictionary with keys student system ids, and values a dictionary giving the compatibility scores with other students and groups (ie, the keys are student and negated group ids, values are scores)
    - ``size_lookup`` -- a dictionary with keys student ids and values the size of group to assign them (2, 3, 5, 9, or 0)

    OUTPUT:

    None, but updates to_match (popping the student who was assigned), groups (adding the student to the relevant group) and compatibilities (updating to account for the changed group and assigned student).

    For simplicity, we don't backtrack, but instead heuristically choose an order to assign students to groups.
    """
    positive_count = {i : len([j for j, score in compatibilities[i].items() if score > 0]) for i in to_match}
    min_count = min(positive_count.values())
    poss = {i : S for (i, S) in to_match.items() if positive_count[i] == min_count}
    # After trying to avoid making people unhappy by violating their requirements, we aim to make people happy by choosing pairings with maximal scores
    besti = None
    bestj = None
    bestscore = -10**12
    for i, S in poss.items():
        for j, score in compatibilities[i].items():
            if score > bestscore:
                # Figure out if the size preferences are compatible
                if j < 0: # existing group
                    G = groups[j]
                else:
                    G = to_match[j]
                if compatible_sizes(G, S, size_lookup):
                    besti = i
                    bestj = j
                    bestscore = score
    # TODO: this loop might not find any places to add S
    # or might end up with groups that need to be combined with each other
    if besti is None: raise RuntimeError

    def pop_student(i):
        student = to_match.pop(i)
        del compatibilities[i]
        for D in compatibilities.values():
            del D[i]
        return student

    student = pop_student(besti)
    # Delete compatibility scores for besti
    if bestj < 0:
        # add to existing group
        gid = bestj
        G = groups[gid]
        G.add(student)
    else:
        other = pop_student(bestj)
        gid = -1 - len(groups)
        G = Group([student, other])
        groups[gid] = G
    for i, S in to_match.items():
        compatibilities[i][gid] = S.compatibility(G)

def matches(year=2020, term=3):
    """
    Creates groups for all classes in a given year and term.
    """
    student_data = {rec["id"]: {key: rec.get(key) for key in ["id", "kerb", "blocked_student_ids", "gender", "hours", "year", "departments"]} for rec in db.test_students.search(projection=3)}
    by_class = {}
    for clsrec in db.classes.search({"year": year, "term": term}, ["id", "class_name"]):
        clsid = clsrec["id"]
        to_match = {}
        # Might also need to search on status for unmatched students?
        for rec in db.test_classlist.search({"class_id": clsid}, ["student_id", "preferences", "strengths", "properties"]):
            properties = dict(rec["properties"])
            properties.update(student_data[rec["student_id"]])
            to_match[rec["student_id"]] = Student(properties, rec["preferences"], rec["strengths"])
        # We handle small cases, where the matches are determined, first
        N = len(to_match)
        # Should fix this to use existing groups
        groups = {}
        if N in [1, 2, 3]:
            # Only one way to group
            groups[-1] = Group(list(to_match.values()))
        elif N >= 4:
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
                # Now there are enough students who are flexible on their group size that we can create groups.
                # We start creating groups based on which students are hardest to satisfy
                compatibilities = defaultdict(dict)
                # We use student ids as keys for students, and create negative ids for groups
                for i, A in to_match.items():
                    for j, B in to_match.items():
                        if j <= i: continue
                        compatibilities[i][j] = compatibilities[j][i] = A.compatibility(B)
                while to_match:
                    assign_one(to_match, groups, compatibilities, size_lookup)
                # We succeeded, so we break out of the limit loop
                break
        # Print warnings for groups with low compatibility and for non-satisfied requirements
        print("%s assignments complete" % clsrec["class_name"])
        for grp in groups.values():
            grp.print_warnings()
        by_class[clsrec["class_name"]] = list(groups.values())
    return by_class


affinities = ["gender", "confidence_affinity", "commitment_affinity", "departments_affinity", "year_affinity"]
styles = ["forum", "start", "style"]


class Student(object):
    def __init__(self, properties, preferences, strengths):
        self.id = properties["id"]
        self.kerb = properties["kerb"]
        self.properties = properties
        self.preferences = {}
        for k, v in preferences.items():
            self.preferences[k] = (v, strengths.get(k, 3))

    def compatibility(self, G):
        if isinstance(G, Student):
            Gplus = Group([G, self])
        else:
            Gplus = Group(G.students + [self])
        return sum(T.score(q, Gplus) for q in affinities + styles for T in Gplus.students) + Gplus.schedule_score()

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
                if check(T):
                    return 3**s
                elif s == 5:
                    return -10**6
                else:
                    return 0
            return sum(score_one(T) for T in others)


class Group(object):
    def __init__(self, students):
        self.students = students

    def add(self, student):
        self.students.append(student)

    def __len__(self):
        return len(self.students)

    def schedule_overlap(self):
        hour_data = [S.properties["hours"] for S in self.students]
        return sum(all(available) for available in zip(hour_data))

    def schedule_score(self):
        """
        Score based on how much overlap there is in the hours scheduled
        """
        overlap = self.schedule_overlap()
        if overlap < 4:
            return -20**(4-overlap)
        else:
            return 20 * floor(sqrt(overlap - 4))

    def print_warnings(self):
        for S in self.students:
            for quality in affinities + styles + ["blocked_student_ids"]:
                if S.score(quality, self) < 0:
                    print("Group breaks %s's %s requirement" % (S.kerb, quality))
        overlap = self.schedule_overlap()
        if overlap < 4:
            print("Small time overlap: %s hours" % overlap)
