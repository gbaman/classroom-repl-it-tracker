import concurrent.futures
import traceback
from typing import List

import requests
from flask import request, g

#from config import classroom_ids, master_classroom
import config

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
            return "✅", "Complete"
        elif self.submission_status == "submitted":
            return "🔶", "Need help - Manual task"
        elif self.submission_status == "submitted_incomplete":
            return "🔴", "Need help - Automarked task"
        elif self.submission_status == "sent_back":
            return "⬅", "Task returned - Awaiting resubmission"
        elif self.important:
            return "❌", "Requirement missing"
        elif self.submission_status == None:
            return "✖️", "Missing"
        else:
            return "⁉️", f"Unknown status... - {self.submission_status}"

    @property
    def completed(self):
        if self.submission_status == "complete":
            return True
        else:
            return False


class Assignment():

    def __init__(self, assignment_id, assignment_name, classroom, time_published, time_due):
        self.assignment_id = assignment_id
        self.assignment_name = assignment_name
        self.classroom: Classroom = classroom
        if time_published:
            self.draft = False
        else:
            self.draft = True
        self.time_due = time_due
        self.submissions = []

    @property
    def exercise_code(self):
        return self.assignment_name.split(" - ")[0]

    def _clone(self, new_classroom_id):
        data = requests.post(url=f"https://repl.it/data/assignments/{self.assignment_id}/clone", headers=headers, data={"classroomId":new_classroom_id})
        print(f"Assignment {self.assignment_name} copied to {new_classroom_id}")

    def safe_clone(self, classroom):
        for assignment in classroom.assignments:
            if assignment.assignment_name == self.assignment_name:
                print(f"Failed to copy assignment {assignment.assignment_name} to {classroom.classroom_name} as it already exists there!")
                break
        else:
            self._clone(classroom.classroom_id)

    def publish(self):
        if self.draft:
            data = requests.post(url=f"https://repl.it/data/teacher/assignments/{self.assignment_id}/publish", headers=headers)
            print(f"Published {self.assignment_name} to {self.classroom.classroom_name}.")
        else:
            print(f"Failed to publish {self.assignment_name} to {self.classroom.classroom_name} because it is already published!")

    def set_due_date(self, due_date):
        if due_date != self.time_due:
            str_date_time = due_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            data = requests.post(url=f"https://repl.it/data/teacher/assignments/{int(self.assignment_id)}]/update", headers=headers, data={"time_due": str_date_time})
            print(data)

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
        self.assignments: List[Assignment] = []
        self.students: List[Student] = []
        self.filtered_students: List[Student] = []
        self.submissions: List[Submission] = []
        self.error = False
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                jobs = []
                jobs.append(executor.submit(self._get_details()))
                jobs.append(executor.submit(self._get_assignments))
                jobs.append(executor.submit(self._get_students))
                jobs.append(executor.submit(self._get_submissions_raw_data()))

        #self._get_assignments()
        #self._get_students()
            self._get_submissions()
        except Exception as e:
            traceback.print_exc()
            print(f"An error has occurred when trying to pull data for classroom {self.classroom_id}!")
            self.error = True

    def _get_details(self):
        data = requests.get(f"https://repl.it/data/classrooms/{self.classroom_id}", headers=headers)
        if not data.ok:
            raise Exception("Request failed for classroom details")
        self.classroom_name = data.json()["name"]

    def _get_assignments(self):
        data = requests.get(f"https://repl.it/data/classrooms/{self.classroom_id}/assignments", headers=headers)
        if not data.ok:
            raise Exception("Request failed for assignments")
        for assignment in data.json():
            self.assignments.append(Assignment(assignment["id"], assignment["name"], self, assignment["time_published"], assignment["time_due"]))

    def _setup_for_student_submissions(self):
        for student in self.students:
            for assignment in self.assignments:
                submission = Submission(student_id=student.student_id, assignment_id=assignment.assignment_id)
                submission.assignment = assignment
                student.submissions.append(submission)

    def _get_students(self):
        data = requests.get(f"https://repl.it/data/teacher/classrooms/{self.classroom_id}/students", headers=headers)
        if not data.ok:
            raise Exception("Request failed for students")
        for student in data.json():
            self.students.append(Student(student["id"], student["first_name"], student["last_name"], student["email"]))

    def _get_submissions_raw_data(self):
        data = requests.get(f"https://repl.it/data/teacher/classrooms/{self.classroom_id}/submissions",headers=headers)
        if not data.ok:
            raise Exception("Request failed for submissions")
        self.submissions_raw_data = data.json()

    def _get_submissions(self):
        data = self.submissions_raw_data
        self._setup_for_student_submissions()
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

    @property
    def selected_students_sorted_surname(self) -> List[Student]:
        return sorted(self.selected_students, key=lambda student: student.student_surname.lower(), reverse=False)

    def add_co_teacher(self, email):
        data = requests.post(url=f"https://repl.it/data/teacher/classrooms/{self.classroom_id}/teaching_assistant_invites/create", headers=headers, data={"emails[]": email})
        return data


def check_cookie():
    if "ajs_user_id" in request.cookies:
        cookie_to_return = ""
        for cookie in request.cookies.items():
            cookie_to_return = f"{cookie_to_return}{cookie[0]}={cookie[1]};"
        return cookie_to_return
    else:
        return False


def build_classroom(classroom_id):
    print(f"Fetching data for {classroom_id}!")
    return Classroom(classroom_id)


def setup_classrooms(browser_cookie) -> List[Classroom]:
    g.years = config.years
    year_id = request.cookies.get('year_id')
    if not year_id:
        year_id = 0
    g.year = config.years[int(year_id)]
    print("Getting classroom data")
    global headers
    headers = {"cookie": browser_cookie, "x-requested-with": "XMLHttpRequest", "Referer": "https://repl.it/login"}
    cookie = browser_cookie
    classrooms = []
    year: config.YearGroup = g.year
    with concurrent.futures.ThreadPoolExecutor() as executor:
        jobs = []
        for classroom_id in year.classroom_ids + [year.master_classroom_id]:
            jobs.append(executor.submit(build_classroom, classroom_id))
        for job in jobs:
            if job.result().classroom_id in [year.master_classroom_id]:
                g.master_classroom = job.result()
            else:
                classrooms.append(job.result())
        g.classrooms = classrooms

        # Create dict version of classrooms to store in g
        g.classrooms_dict = {}
        for classroom in classrooms:
            g.classrooms_dict[classroom.classroom_id] = classroom

        return classrooms


def get_login_cookie(username, password):
    response = requests.post(url="https://repl.it/login", headers={"x-requested-with":"XMLHttpRequest", "Referer":"https://repl.it/login"}, data={"username":username, "password":password, "teacher":False})
    if response.ok:
        cookies = {"__cfduid":response.cookies.get("__cfduid"), "ajs_user_id":response.json()["id"], "connect.sid":response.cookies.get("connect.sid")}
        return cookies
    else:
        return response.ok


def create_classroom(name, language="python3", description="", is_public=False):
    data = requests.post(url="https://repl.it/data/classrooms/create", headers=headers, data={"name":name, "language_key":language, "description":description, "isPublic":is_public, "image":""})
    print(f"Classroom created with the following ID - {data.json()['id']}")