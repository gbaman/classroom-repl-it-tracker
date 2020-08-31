import concurrent.futures
from typing import List

import requests

from config import classroom_ids

headers = {}


class Submission():

    def __init__(self, submission_id=None, student_id=None, assignment_id=None, submission_text=None, submission_submitted_time=None, submission_status=None):
        self.submission_id = submission_id
        self.student_id = student_id
        self.assignment_id = assignment_id
        self.submission_text = submission_text
        self.submission_submitted_time = submission_submitted_time
        self.submission_status = submission_status
        self.student = None
        self.assignment = None
        self.important = False

    @property
    def completed_symbol(self):
        if self.submission_status == "complete":
            return "✅"
        elif self.submission_status == "submitted":
            return "🟡"
        elif self.important:
            return "❌"
        else:
            return "✖️"

    @property
    def completed(self):
        if self.submission_status == "complete":
            return True
        else:
            return False


class Assignment():

    def __init__(self, assignment_id, assignment_name, classroom):
        self.assignment_id = assignment_id
        self.assignment_name = assignment_name
        self.classroom: Classroom = classroom
        self.submissions = []

    @property
    def exercise_code(self):
        return self.assignment_name.split(" - ")[0]


class Student():

    def __init__(self, student_id, student_first_name, student_surname, student_email):
        self.student_id = student_id
        self.student_first_name = student_first_name
        self.student_surname = student_surname
        self.student_email = student_email
        self.submissions: List[Submission] = []

    @property
    def submissions_sorted(self):
        return sorted(self.submissions, key=lambda s: s.assignment.exercise_code, reverse=False)

    @property
    def submissions_dict_by_assignment_id(self):
        submission_dict = {}
        for submission in self.submissions:
            submission_dict[submission.assignment_id] = submission
        return submission_dict

    # @property
    # def assignment_exercise_ids(self):
    #    assignment_exercise_ids = []
    #    for assignment in self.ass
    #    return 


class Classroom():
    classroom_id = None
    classroom_name = None

    def __init__(self, classroom_id):
        self.classroom_id = classroom_id
        self._get_details()
        self.assignments: List[Assignment] = []
        self.students: List[Student] = []
        self.filtered_students: List[Student] = []
        self.submissions: List[Submission] = []
        self._get_assignments()
        self._get_students()
        self._get_submissions()

    def _get_details(self):
        data = requests.get(f"https://repl.it/data/classrooms/{self.classroom_id}", headers=headers).json()
        self.classroom_name = data["name"]

    def _get_assignments(self):
        data = requests.get(f"https://repl.it/data/classrooms/{self.classroom_id}/assignments", headers=headers).json()
        for assignment in data:
            self.assignments.append(Assignment(assignment["id"], assignment["name"], self))

    def _setup_for_student_submissions(self):
        for student in self.students:
            for assignment in self.assignments:
                submission = Submission(student_id=student.student_id, assignment_id=assignment.assignment_id)
                submission.assignment = assignment
                student.submissions.append(submission)

    def _get_students(self):
        data = requests.get(f"https://repl.it/data/teacher/classrooms/{self.classroom_id}/students", headers=headers).json()
        for student in data:
            self.students.append(Student(student["id"], student["first_name"], student["last_name"], student["email"]))

    def _get_submissions(self):
        self._setup_for_student_submissions()
        data = requests.get(f"https://repl.it/data/teacher/classrooms/{self.classroom_id}/submissions", headers=headers).json()
        for assignment_id in data:
            assignment = self.assignments_dict[int(assignment_id)]
            for raw_submission in data[assignment_id]:
                student = self.students_dict[int(raw_submission["student_id"])]
                submission = student.submissions_dict_by_assignment_id[int(assignment.assignment_id)]
                submission.submission_id = raw_submission["id"]
                submission.submission_text = raw_submission["editor_text"]
                submission.submission_submitted_time = raw_submission["time_submitted"]
                submission.submission_status = raw_submission["status"]
                # student.submissions.append(submission)
                submission.assignment = assignment
                submission.student = student

    @property
    def assignments_dict(self):
        assignment_dict = {}
        for assignment in self.assignments:
            assignment_dict[assignment.assignment_id] = assignment
        return assignment_dict

    @property
    def assignments_sorted(self):
        return sorted(self.assignments, key=lambda a: a.exercise_code, reverse=False)

    @property
    def students_dict(self):
        student_dict = {}
        for student in self.students:
            student_dict[student.student_id] = student
        return student_dict

    @property
    def selected_students(self) -> List[Student]:
        if self.filtered_students:
            return self.filtered_students
        return self.students


def build_classroom(classroom_id):
    print(f"Fetching data for {classroom_id}!")
    return Classroom(classroom_id)


def setup_classrooms(browser_cookie) -> List[Classroom]:
    global headers
    headers = {"cookie": browser_cookie}
    cookie = browser_cookie
    classrooms = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        jobs = []
        for classroom_id in classroom_ids:
            jobs.append(executor.submit(build_classroom, classroom_id))
        for job in jobs:
            classrooms.append(job.result())
        return classrooms


def get_login_cookie(username, password):
    response = requests.post(url="https://repl.it/login", headers={"x-requested-with":"XMLHttpRequest", "Referer":"https://repl.it/login"}, data={"username":username, "password":password, "teacher":False})
    if response.ok:
        cookies = {"__cfduid":response.cookies.get("__cfduid"), "ajs_user_id":response.json()["id"], "connect.sid":response.cookies.get("connect.sid")}
        return cookies
    else:
        return response.ok