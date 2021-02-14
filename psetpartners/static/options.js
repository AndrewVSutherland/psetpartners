// This replicates data defined in the database and/or python source code, you need to update both

const departmentsOptions = [
  { label: '1 Civil and Environmental Engineering', value: '1', },
  { label: '2 Mechanical Engineering', value: '2', },
  { label: '3 Materials Science and Engineering', value: '3', },
  { label: '4 Architecture', value: '4', },
  { label: '5 Chemistry', value: '5', },
  { label: '6 EECS', value: '6', },
  { label: '7 Biology', value: '7', },
  { label: '8 Physics', value: '8', },
  { label: '9 Brain and Cognitive Sciences', value: '9', },
  { label: '10 Chemical Engineering', value: '10', },
  { label: '11 Urban Studies and Planning', value: '11', },
  { label: '12 EAPS', value: '12', },
  { label: '14 Economics', value: '14', },
  { label: '15 Management', value: '15', },
  { label: '16 Aeronautics and Astronautics', value: '16', },
  { label: '17 Political Science', value: '17', },
  { label: '18 Mathematics', value: '18', },
  { label: '20 Biological Engineering', value: '20', },
  { label: '21 Humanities', value: '21', },
  { label: '21A Anthropology', value: '21A', },
  { label: '21E Humanities and Engineering', value: '21E', },
  { label: '21G Global Studies and Languages', value: '21G', },
  { label: '21H History', value: '21H', },
  { label: '21L Literature', value: '21L', },
  { label: '21M Music and Theater Arts', value: '21M', },
  { label: '21S Humanities and Science', value: '21S', },
  { label: '21W Writing', value: '21W', },
  { label: '22 Nuclear Science and Engineering', value: '22', },
  { label: '24 Linguistics and Philosophy', value: '24', },
  { label: 'CMS Comparative Media Studies', value: 'CMS', },
  { label: 'HST Health Sciences and Technology', value: 'HST', },
  { label: 'IDS Data, Systems, and Society', value: 'IDS', },
  { label: 'IMES Medical Engineering and Science', value: 'IMES', },
  { label: 'MAS Media Arts and Sciences', value: 'MAS', },
  { label: 'SCM Supply Chain Management', value: 'SCM', },
  { label: 'STS Science, Technology, and Society', value: 'STS', },
  { label: "WGS Women's and Gender Studies", value: 'WGS', },
  ];

const yearOptions = [
  { label: '', value: '' },
  { label: 'first year', value: '1', },
  { label: 'sophomore', value: '2', },
  { label: 'junior', value: '3', },
  { label: 'senior or super senior', value: '4', },
  { label: 'graduate student', value: '5', },
];

const yearShort = ["", "first year", "sophomore", "junior", "senior", "graduate"];

const genderOptions = [
  { label: '', value: '' },
  { label: 'female', value: 'female', },
  { label: 'male', value: 'male', },
  { label: 'non-binary', value: 'non-binary', },
];

const locationOptions = [
  { label: 'on campus or near MIT', value: 'near', },
  { label: 'not near MIT', value: 'far', },
  { value: "baker", label: "Baker House", disabled: true },
  { value: "buron-conner",  label: "Burton Conner House", disabled: true },
  { value: "east",  label: "East Campus", disabled: true },
  { value: "macgregor",  label: "MacGregor House", disabled: true },
  { value: "maseeh",  label: "Maseeh Hall", disabled: true },
  { value: "mccormick",  label: "McCormick Hall", disabled: true },
  { value: "new",  label: "New House", disabled: true },
  { value: "next",  label: "Next House", disabled: true },
  { value: "random",  label: "Random Hall", disabled: true },
  { value: "simmons",  label: "Simmons Hall", disabled: true },
  { value: "epsilontheta",  label: "Epsilon Theta", disabled: true },
  { value: "fenway",  label: "Fenway House", disabled: true },
  { value: "pika",  label: "pika", disabled: true },
  { value: "student",  label: "Student House", disabled: true },
  { value: "wilg",  label: "WILG", disabled: true },
  { value: "amherst", label: "70 Amherst Street", disabled: true },
  { value: "ashdown", label: "Ashdown House", disabled: true },
  { value: "edgerton", label: "Edgerton House", disabled: true },
  { value: "tower4", label: "Graduate Tower at Site 4", disabled: true },
  { value: "sidneypacific", label: "Sidney-Pacific", disabled: true },
  { value: "tang", label: "Tang Hall", disabled: true },
  { value: "warehouse", label: "The Warehous", disabled: true },
  { value: "westgate", label: "Westgate", disabled: true },
];

const startOptions = [
  { label: '', value: '' },
  { label: 'early, shortly after the problem set is posted', value: '1', },
  { label: 'middle, at least 3 days before the pset is due', value: '2', },
  { label: 'late, a few days before the pset is due', value: '3', },
];
const startShort = ["", "early", "middle", "late"];

const styleOptions = [
  { label: '', value: '' },
  { label: 'solve the problems together', value: '1', },
  { label: 'discuss strategies, help each other when stuck', value: '2', },
  { label: 'work independently but check answers', value: '3', },
];
const styleShort = ["", "together", "collegial", "soloists"];

const forumOptions = [
  { label: '', value: '' },
  { label: 'text (e.g. Slack or Zulip)', value: 'text', },
  { label: 'video (e.g. Zoom)', value: 'video', },
  { label: 'in person', value: 'in-person', disabled: true },
];
const forumShort = ["", "text", "video", "in-person"];

const sizeOptions = [
  { label: '', value: '' },
  { label: '2 students', value: '2', },
  { label: '3-4 students', value: '3', },
  { label: '5-8 students', value: '5', },
  { label: 'more than 8 students', value: '9', },
];
const sizeShort = ["", "2", "3-4", "5-8", "9+"];

const department_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else in my department', value: '1', },
  { label: 'only students in my department', value: '2', },
  { label: 'students in many departments', value: '3', },
];
const departments_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else in one of my departments', value: '1', },
  { label: 'only students in one of my departments', value: '2', },
  { label: 'students in many departments', value: '3', },
];
const year_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else in my year', value: '1', },
  { label: 'only students in my year', value: '2', },
  { label: 'students in multiple years', value: '3', },
];
const gender_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else with my gender identity', value: '1', },
  { label: 'only students with my gender identity', value: '2', },
  { label: 'a diversity of gender identities', value: '3', },
];

const commitmentOptions = [
  { label: '', value: '' },
  { label: 'still shopping and/or not taking for credit', value: '1' },
  { label: 'other courses might be higher priority', value: '2' },
  { label: 'This course is a top priority for me', value: '3' },
];
const confidenceOptions = [
  { label: '', value: '' },
  { label: 'This will be all new for me', value: '1' },
  { label: 'I have seen some of the material before', value: '2' },
  { label: 'I am generally familiar with most of it', value: '3' },
];
const commitment_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else with my level of commitment', value: '1', },
  { label: 'only students with my level of commitment', value: '2', },
];
const confidence_affinityOptions = [
  { label: '', value: '' },
  { label: 'someone else at my comfort level', value: '1', },
  { label: 'only students at my comfort level', value: '2', },
  { label: 'a diversity of comfort levels', value: '3', },
];

const editorOptions = [
  { label: 'everyone', value: '0' },
  { label: 'just me', value: '1' },
];
const groupMembershipOptions = [
  { label: 'invitation', value: '0' },
  { label: 'permission', value: '1' },
  { label: 'automatic', value: '2' },
];

const studentPreferences = [ "start", "style", "forum", "size", "departments_affinity", "year_affinity", "gender_affinity" ];
const studentAffinities = [ 'departments', 'year', 'gender' ];
const studentClassPreferences = ["commitment_affinity", "confidence_affinity" ];
const studentClassAffinities = ['commitment', 'confidence' ];

const studentOptions = {
  departments: departmentsOptions,
  year: yearOptions,
  gender: genderOptions,
  location: locationOptions,
  start: startOptions,
  style: styleOptions,
  forum: forumOptions,
  size: sizeOptions,
  commitment: commitmentOptions,
  confidence: confidenceOptions,
  departments_affinity: departments_affinityOptions,
  year_affinity: year_affinityOptions,
  gender_affinity: gender_affinityOptions,
  commitment_affinity: commitment_affinityOptions,
  confidence_affinity: confidence_affinityOptions,
};

// jshint ignore:start
const startShortOptions = [...startOptions];
for ( let i = 0 ; i < startOptions.length ; i++ ) { startShortOptions[i] = {...startOptions[i]}; startShortOptions[i].label = startShort[i]; }
const styleShortOptions = [...styleOptions];
for ( let i = 0 ; i < styleOptions.length ; i++ ) { styleShortOptions[i] = {...styleOptions[i]}; styleShortOptions[i].label = styleShort[i]; }
const forumShortOptions = [...forumOptions];
for ( let i = 0 ; i < forumOptions.length ; i++ ) { forumShortOptions[i] = {...forumOptions[i]}; forumShortOptions[i].label = forumShort[i]; }
const sizeShortOptions = [...sizeOptions];
for ( let i = 0 ; i < sizeOptions.length ; i++ ) { sizeShortOptions[i] = {...sizeOptions[i]}; sizeShortOptions[i].label = sizeShort[i]; }
// jshint ignore:end
/* global startShortOptions, styleShortOptions, forumShortOptions, sizeShortOptions */

const shortOptions = { start: startShortOptions, style: styleShortOptions, forum: forumShortOptions, size: sizeShortOptions, };

const studentPlaceholders = {
  departments: 'select up to three departments (optional)',
  year: 'select year (optional)',
  gender: 'select gender (optional)',
  classes: 'select your classes',
  start: 'how long before the due date',
  style: 'collaboration style',
  forum: 'communication medium',
  size: 'size range',
  commitment: 'commitment level',
  confidence: 'comfort level',
  departments_affinity: 'department affinity',
  year_affinity: 'year affinity',
  gender_affinity: 'gender affinity',
  commitment_affinity: 'commitment affinity',
  confidence_affinity: 'knowledge affinity',
};

const profileOptions = [ 'expand', 'collapse' ];

const kerbMinLength = 2 // New kerbs have length at least 3 but a few length 2 kerbs are still active
const kerbRE = new RegExp('^[a-z][a-z0-9_]+$');
const classnameRE = new RegExp("^[a-zA-Z0-9 ,.;:&?!/@#'()\-]+$");

