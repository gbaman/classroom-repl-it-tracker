from __future__ import annotations
import concurrent.futures
from typing import List
import requests
from flask import request, g
import config


headers = {}

class TestResult():
    def __init__(self, test_id, test_status):
        self.test_id = test_id
        self.test_status = test_status

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
        self.test_results: List[TestResult] = []
        self.last_reviewed = None
        self.url = ""

    @property
    def all_tests_passed(self):
        tests_passed = 0
        if self.test_results:
            for test in self.test_results:
                if test.test_status == "passed":
                    tests_passed = tests_passed + 1
            if tests_passed == len(self.test_results):
                return True
        else:
            return False

    @property
    def completed_symbol(self):
        if self.all_tests_passed or self.last_reviewed:
            return "✅", "Complete"
        elif self.test_results:
            return "🔶", "Need help - Manual task (but submitted)"
        elif self.submission_status == "submitted_incomplete":
            return "🔴", "Need help - Automarked task"
        elif self.submission_status == "sent_back":
            return "⬅", "Task returned - Awaiting resubmission"
        elif self.important:
            return "❌", "Requirement missing"
        elif self.submission_id and self.submission_submitted_time:
            return "🔜", "Legacy - Before testing (or never run the tests, but submitted anyway)"
        elif self.submission_id and not self.submission_submitted_time:
            return "🟨", "Working on currently (not submitted)"
        elif self.submission_status == None and self.submission_id == None:
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

    def __init__(self, assignment_id, assignment_name, team, time_published, time_due):
        self.assignment_id = assignment_id
        self.assignment_name = assignment_name
        self.team: Team = team
        if time_published:
            self.draft = False
        else:
            self.draft = True
        self.time_due = time_due
        self.submissions: List[Submission] = []

    @property
    def exercise_code(self):
        return self.assignment_name.split(" - ")[0]

    def get_student_submission(self, student:Student):
        for submission in self.submissions:
            if submission.student == student:
                return submission
        return Submission(None, None, None, None, None, None)


class Student():
    def __init__(self, student_id, student_first_name, student_surname, student_username, student_email):
        self.student_id = student_id
        self.student_first_name = student_first_name
        self.student_surname = student_surname
        self.student_email = student_email
        self.submissions: List[Submission] = []
        self.student_username = student_username
        if not student_surname:
                if student_email.endswith("westminster.org.uk"):
                    self.student_first_name, self.student_surname = student_email.split("@")[0].split(".")
                else:
                    self.student_surname = self.student_username
        self.to_ignore = False

    @property
    def submissions_sorted(self):
        return sorted(self.submissions, key=lambda s: s.assignment.exercise_code, reverse=False)

    @property
    def submissions_dict_by_assignment_id(self):
        submission_dict = {}
        for submission in self.submissions:
            submission_dict[submission.assignment_id] = submission
        return submission_dict


class Team():
    team_name = None

    def __init__(self, team_name):
        self.team_name = team_name
        self.team_full_name = ""
        self.assignments: List[Assignment] = []
        self.students: List[Student] = []
        self.filtered_students: List[Student] = []
        self.submissions: List[Submission] = []
        self.error = False

    def update_team_data(self):
        team_data = run_graphql_query(main_query.replace("{", "<").replace("}", ">").replace("[", "{").replace("]", "}").format(name=self.team_name).replace("<", "{").replace(">", "}"))["data"]["team"]
        self.team_full_name = team_data["displayName"]

        for student in team_data["members"]:
            new_student = Student(student["user"]["id"], student["user"]["firstName"], student["user"]["lastName"], student["user"]["username"], student["email"])
            if student["user"]["username"] in config.ignored_usernames:
                new_student.to_ignore = True

            self.students.append(new_student)

        for template in team_data["templates"]:
            new_assignment = Assignment(template["id"], template["repl"]["title"], self, True, None)
            for submission in template["submissions"]:
                new_submission = Submission(submission["id"], submission["author"]["id"], new_assignment.assignment_id, None, submission["timeSubmitted"])
                new_submission.assignment = new_assignment
                new_submission.last_reviewed = submission["timeLastReviewed"]
                new_submission.student = self.students_dict[new_submission.student_id]
                new_submission.url = submission["repl"]["url"]
                new_submission.student.submissions.append(new_submission)
                if submission["repl"]["ioTestResults"]:
                    for result in submission["repl"]["ioTestResults"]:
                        new_test = TestResult(result["id"], result["status"])
                        new_submission.test_results.append(new_test)
                new_assignment.submissions.append(new_submission)
            self.assignments.append(new_assignment)


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


main_query = """
query Foo {
  
  team: teamByUsername (username: "[name]") {
    ... on Team {
      displayName
      members {
        id
        email
        user {
          displayName
          username
          firstName
          lastName
          id
        }
      }
      
      templates {
        id
        repl {
          title
          id
          url
        }
        submissions {
          id
          timeSubmitted
          timeLastReviewed
          author {
            id
            username
          }
          repl {
            id
            url
            ioTestResults {
                id
                status
            }
          }
        }
      }
    }
  }
}


"""

def build_team(team_id):
    print(f"Fetching data for {team_id}!")
    new_team = Team(team_id)
    new_team.update_team_data()
    return new_team



def setup_all_teams(cookie):
    g.years = config.years
    year_id = request.cookies.get('year_id')
    if not year_id:
        year_id = 0
    g.year = config.years[int(year_id)]
    global headers
    headers = {"X-Requested-With": "XMLHttpRequest", "Origin": "https://replit.com", "Cookie":cookie.replace("Cookie: ", "")}
    teams = []
    team_names = g.year.classroom_ids

    with concurrent.futures.ThreadPoolExecutor() as executor:
        jobs = []
        for team_name in team_names:
            jobs.append(executor.submit(build_team, team_name))
        for job in jobs:
            teams.append(job.result())

    #for team_name in team_names:
    #    new_team = Team(team_name)
    #    new_team.update_team_data()
    #    teams.append(new_team)
    g.classrooms = teams
    g.teams = teams
    g.classrooms_dict = {}
    for team in teams:
        g.classrooms_dict[team.team_name] = team
    g.teams_dict = g.classrooms_dict
    return teams


def run_graphql_query(query):
    response = requests.post("https://replit.com/graphql", json={"query": query}, headers=headers)
    return response.json()

