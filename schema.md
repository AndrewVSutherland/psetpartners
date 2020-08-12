# Schema

This file provides documentation on the underlying schema; try to keep it up to date if you make changes.

## departments

Column                | Type        |  Notes
----------------------|-------------|-------
id                    | bigint      | unique identifier automatically assigned by postgres
course_name           | text        | Course name, e.g. Mathematics
course_number         | text        | Course number, e.g. 18


## classes	

Column                | Type        |  Notes
----------------------|-------------|-------
id                    | bigint      | unique identifier automatically assigned by postgres
class_name            | text        | Course name, e.g. Algebra I
class_number          | text        | Course number, e.g. 18.701
year                  | smallint    | Calendar year
term                  | smallint    | Encoding of semester 0=IAP, 1=spring, 2=summer, 3=fall
instructor_names[]    | text[]      | list of instructor names
instructor_kerbs[]    | text[]      | list of instructor kerbs
homepage              | text        | course homepage
pset_dates            | date[] 	    | list of due dates for psets (optional, possibly only first 3 relevant)

## students
			
Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres (not MIT id)
departments           | text[]      | List of course_numbers in departments table, e.g. ["18"] or ["6","18"]
description           |	text	    | Student's public description of themself (not currently used)
email	              | text	    | smith@gmail.com (not currently used, we just email kerb@mit.edu)
gender                | text        | optional, currently female, male, or non-binary (optional)
hours                 | boolean[]   | a 7x24 array of booleans indicating hours available to pset (in timezone)
kerb                  |	text	    | kerberos id
location              | text        | currently near or far (but will eventually include dorms, ILGs, etc...
name                  |	text        | e.g. Johnathan Smith
preferred_name        | text        | e.g. John Smith
preferred_pronouns    | text	    | e.g. they/them
preferences           |	jsonb	    | dictionary of preferences (see Preferences tab)
strengths             | jsonb       | dictionary of preference strength (values are integers from 0 to 10)
timezone              |	text	    | ('MIT' means MIT's timezone, America/NewYork)
year                  | smallint    | 1=frosh, 2=soph, 3=junior, 4=senior/super-senior, 5=graduate student
blocked_student_ids   | bigint[]    | list of student ids this student will never be put in a group with
rejected_group_ids    | bigint[]    | list of group ids theis student has rejectd
			
## groups

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres (not MIT id)
class_id	      | bigint	    | id in classes table
group_name            | text	    | custom name, editable by anyone in group
visibility            | smallint    | 0=closed, 1=open, 2=public  (closed+open are system created)
preferences	      | jsonb       | optional group preferences; if unspecified, system constructs something from member preferences
strengths             | jsonb       | preference strengths

## classlist

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres (not MIT id)
class_id	      | bigint	    | id in classes table
student_id            | bigint	    | id in students table
year		      | smallint    | year of class (used to quickly get a list of current classes for a student)
term                  | smallint    | term of class (used to quickly get a list of current classes for a student)
properties            | jsonb       | class-specific student properties such as commentment/comfort lavel that may have associated affinity preferences
preferences           |	jsonb       | replaces students preferences if not None (which is not the same as {})
strengths             | jsonb       | replaces students preferences if preferences is not None
			
## grouplist

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      |	unique identifier automatically assigned by postgres (not MIT id)
class_id              | bigint      | id in classes_table
group_id	      | bigint      | id in groups table
student_id            | bigint      | id in students table
