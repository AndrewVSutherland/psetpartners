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
match_dates           | date[] 	    | matching dates (only future dates are relevant)

## students
			
Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres (not MIT id)
departments           | text[]      | List of course_numbers in departments table, e.g. ["18"] or ["6","18"]
description           |	text	    | Student's public description of themself (not currently used)
email	              | text	    | smith@gmail.com (not currently used, we just email kerb@mit.edu)
gender                | text        | optional, currently female, male, or non-binary (optional)
hours                 | boolean[]   | a list of 7x24=168 booleans indicating hours available to pset (in timezone)
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
id                    |	bigint      | unique identifier automatically assigned by postgres
class_id	      | bigint	    | id in classes table
class_number	      | text        | class number (e.g. "18.701")
year                  | smallint    | year of class (e.g. 2020)
term                  | smallint    | term of class (e.g. 3 = Fall)
group_name            | text	    | custom name, editable by anyone in group
visibility            | smallint    | 0=private closed, 1=private open, 2=public group with private membership, 3=public group with public membership
preferences	      | jsonb       | optional group preferences; if unspecified, system constructs something from member preferences
hours                 | boolean[]   | hours the group is potentially available to meet (used for matching)
strengths             | jsonb       | preference strengths
creator               | text        | kerb of the student who created the group, empty string for system created groups
editors               | text[]      | list of kerbs of students authorized to modify the group (empty list means everyone)
max                   | smallint    | maximum number of students
match_run             | smallint    | only set for system created groups, incremented with each matching

## classlist

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres
class_id	      | bigint	    | id in classes table
student_id            | bigint	    | id in students table
kerb                  | text        | kerberos id of student (copied from students table for conveniencE)
class_number          | text        | class number (copied from classes table for convenience)
year		      | smallint    | year of class (copied from classes table for convenience)
term                  | smallint    | term of class (copied from classes table for convenience)
properties            | jsonb       | class-specific student properties such as commentment/confidence that may have associated affinity preferences (names should not collide with student properties such as gender or year)
preferences           |	jsonb       | replaces students preferences if not None (which is not the same as {})
strengths             | jsonb       | replaces students preferences if preferences is not None
status                | smallint    | 1 = in a group, 2 = in match pool, 3 = match requested, 4 = match in progress
			
## grouplist

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres
class_id              | bigint      | id in classes_table
group_id	      | bigint      | id in groups table
student_id            | bigint      | id in students table
kerb                  | text        | kerberos ud of student (copied from students table for convenience)
class_number          | text        | class number (copied from classes table for convenience)
year		      | smallint    | year of class (copied from classes table for convenience)
term                  | smallint    | term of class (copied for convenience)
