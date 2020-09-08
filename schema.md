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
size                  | smallint    | number of rows in classlist with class_id = id (read/write ratio is high, so worth maintaining)

## students
			
Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres (not MIT id)
departments           | text[]      | List of course_numbers in departments table, e.g. ["18"] or ["6","18"]
description           |	text	    | Student's public description of themself (not currently used)
email	              | text	    | smith@gmail.com (not currently used, we just email kerb@mit.edu)
gender                | text        | optional, currently female, male, or non-binary (optional)
hours                 | boolean[]   | a list of 7x24=168 booleans indicating hours available to pset (in timezone)
kerb                  |	text	    | kerberos id (lookup column for this table)
location              | text        | currently near or far (but will eventually include dorms, ILGs, etc...
name                  |	text        | e.g. Johnathan Smith
preferred_name        | text        | e.g. John Smith
preferred_pronouns    | text	    | e.g. they/them
preferences           |	jsonb	    | dictionary of preferences (see Preferences tab)
strengths             | jsonb       | dictionary of preference strength (values are integers from 0 to 10)
timezone              |	text	    | ('MIT' means MIT's timezone, America/NewYork)
year                  | smallint    | 1=frosh, 2=soph, 3=junior, 4=senior/super-senior, 5=graduate student
blocked_student_ids   | bigint[]    | list of student ids this student will never be put in a group with
			
## groups

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres
class_id	      | bigint	    | id in classes table
class_number	      | text        | class number (e.g. "18.701")
year                  | smallint    | year of class (e.g. 2020)
term                  | smallint    | term of class (e.g. 3 = Fall)
group_name            | text	    | custom name, editable by anyone in group
visibility            | smallint    | 0=invitation, 1=permission, 2=automatic, 3=public
preferences	      | jsonb       | optional group preferences; if unspecified, system constructs something from member preferences
strengths             | jsonb       | preference strengths
creator               | text        | kerb of the student who created the group, empty string for system created groups
editors               | text[]      | list of kerbs of students authorized to modify the group (empty list means everyone)
size                  | smallint    | number of rows in grouplist with group_id=id (read/write ratio is high, so worth maintaining)
max                   | smallint    | maximum number of students (None if no limit, may be less than size due to edits)
match_run             | smallint    | only set for system created groups, incremented with each matching
permission_requested  | timestamp   | set when permission has been requested, set to none if/when granted (only relevant if visibility=1)

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
properties            | jsonb       | class-specific student properties such as commentment/confidence that may have associated affinity preferences (names should not collide with student properties)
preferences           |	jsonb       | copied from student preferences initially but may be modified
strengths             | jsonb       | copied from studnet strengths initially but may then be modified
status                | smallint    | 1 = in a group, 2 = in match pool, 3 = match requested, 4 = match permissions sought, 5 = pool match in progress
permission_requested  | timestamp   | set when permission requested (match_me_asap), expires after 24 hours
		
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

## grouplistleft
(rows are moved here from grouplist whenver a student leaves a group)

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

## events

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres
kerb                  | text        | kerberos ud of user (student or instructor)
event                 | text        | type of event (e.g. login, join, leave, pool, match, ...)
detail                | jsonb       | details associated to the even (e.g. group id or class id)
timestamp             | timestamp   | time of event (always in MIT time, no timezone)
status                | smallint    | status code -- 0 means informational, nonzero is some sort of error

## messages

Column                | Type        |  Notes
----------------------|-------------|-------
id                    |	bigint      | unique identifier automatically assigned by postgres
sender_kerb           | text        | kerberos of of sender (empty string for system messages)
recipient_kerb        | text        | kerberos of of recipient (who will see the message on their home page)
type                  | text        | type of message (e.g. welcome, notify, accepted, newgroup, ...)
content               | text        | the HTML content of the message (will appear inside a `p` element)
read                  | boolean     | set when user acknowledges messages by clicking ok

