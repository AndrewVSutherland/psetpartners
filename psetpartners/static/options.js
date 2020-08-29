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
  { label: '21E/21S Humanities + Eng./Science', value: '21E/21S', },
  { label: '21G Global Studies and Languages', value: '21G', },
  { label: '21H History', value: '21H', },
  { label: '21L Literature', value: '21L', },
  { label: '21M Music and Theater Arts', value: '21M', },
  { label: '22 Nuclear Science and Engineering', value: '22', },
  { label: '24 Linguistics and Philosophy', value: '24', },
  { label: 'CMS/21W Comp. Media Studies/Writing', value: 'CMS/21W', },
  { label: 'IDS Data, Systems, and Society', value: 'IDS', },
  { label: 'IMES Medical Engineering and Science', value: 'IMES', },
  { label: 'MAS Media Arts and Sciences', value: 'MAS', },
  { label: 'STS Science, Technology, and Society', value: 'STS', },
  ];

const yearOptions = [
  { label: '', value: '' },
  { label: 'first year', value: '1', },
  { label: 'sophomore', value: '2', },
  { label: 'junior', value: '3', },
  { label: 'senior or super senior', value: '4', },
  { label: 'graduate student', value: '5', },
];

const yearShort = ["", "first year", "sophomore", "junior", "senior", "graduate"]

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
  { label: 'shortly after the problem set is posted', value: '6', },
  { label: '3-4 days before the pset is due', value: '4', },
  { label: '1-2 days before the pset is due', value: '2', },
];
const startShort = ["", "early", "midway", "late"];

const togetherOptions = [
  { label: '', value: '' },
  { label: 'solve the problems together', value: '1', },
  { label: 'discuss strategies, work together if stuck', value: '2', },
  { label: 'work independently but check answers', value: '3', },
];
const togetherShort = ["", "unified", "collegial", "independent"];

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
  { label: 'more than 8 students', value: '8', },
];
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
  { label: 'other courses might be a higher priority', value: '2' },
  { label: 'This course is a top priority', value: '3' },
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

const studentPreferences = [ "start", "together", "forum", "size", "departments_affinity", "year_affinity", "gender_affinity" ];
const studentAffinities = [ 'departments', 'year', 'gender' ];
const studentClassPreferences = ["commitment_affinity", "confidence_affinity" ];
const studentClassAffinities = ['commitment', 'confidence' ];

const studentOptions = {
  departments: departmentsOptions,
  year: yearOptions,
  gender: genderOptions,
  location: locationOptions,
  start: startOptions,
  together: togetherOptions,
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

const studentPlaceholders = {
  departments: 'select up to three departments (optional)',
  year: 'select year (optional)',
  gender: 'select gender (optional)',
  classes: 'select your classes',
  start: 'how long before the due date',
  together: 'collaboration style',
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

const profileOptions = [ "expand", "contract" ]
