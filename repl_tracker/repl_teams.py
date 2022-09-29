from __future__ import annotations
import concurrent.futures
import time
from dataclasses import dataclass
from json import JSONDecodeError
from typing import List, Dict
from datetime import timezone, datetime
from typing import List
import requests
from flask import request, g
import config
from dateutil import parser

import helpers

headers = {}

class TestResult():
    def __init__(self, test_id, test_status):
        self.test_id = test_id
        self.test_status = test_status


@dataclass
class Template():
    id: int
    name: str
    assignment: Assignment


@dataclass
class TemplateShareLink():
    id: int
    code: str
    time_created: datetime


class Submission():

    def __init__(self, submission_id=None, student_id=None, assignment_id=None, submission_text=None, submission_submitted_time=None, submission_status=None):
        self.submission_id = submission_id
        self.student_id = student_id
        self.assignment_id = assignment_id
        self.submission_text = submission_text
        self.submission_submitted_time = submission_submitted_time
        self.submission_status = submission_status
        self.student: Student = None
        self.assignment: Assignment = None
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
            return "🔶", "Submitted - All tests not passed"
        elif self.submission_status == "submitted_incomplete":
            return "🔴", "Need help - Automarked task"
        elif self.submission_status == "sent_back":
            return "⬅", "Task returned - Awaiting resubmission"
        elif self.important:
            return "❌", "Requirement missing"
        elif self.submission_id and self.submission_submitted_time:
            return "🔜", "Tests not run yet"
        elif self.submission_id and not self.submission_submitted_time and self.submission_id != -1:
            return "🟨", "Not submitted - All tests not passed"
        elif self.submission_status == None and (self.submission_id == None or self.submission_id == -1):
            return "✖️", "Task not started - Missing"
        else:
            return "⁉️", f"Unknown status... - {self.submission_status}"

    @property
    def completed(self):
        if self.all_tests_passed or self.last_reviewed:
            return True
        else:
            return False


    @property
    def completed_symbol_without_important(self):
        self.important = False
        return self.completed_symbol

    @property
    def download_file_name(self):
        return self.download_folder_name + ".zip"

    @property
    def download_folder_name(self):
        return self.url.replace("@", "").split("/")[2]


class Assignment():

    def __init__(self, assignment_id, assignment_name, team, time_published, datetime_due):
        self.assignment_id = assignment_id
        self.assignment_name = assignment_name
        self.team: Team = team
        if time_published:
            self.draft = False
        else:
            self.draft = True
        if datetime_due:
            self.datetime_due = parser.parse(datetime_due)
            #self.datetime_due.replace(tzinfo=timezone.utc)
        else:
            self.datetime_due = None
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
                if student_email and student_email.endswith("westminster.org.uk"):
                    self.student_first_name, self.student_surname = student_email.split("@")[0].split(".")
                else:
                    self.student_surname = self.student_username
        self.to_ignore = False
        self.group_name = None  # Used to store a sub-group (aka which class is the student in, in a shared Team)
        self.hide = False

    @property
    def submissions_sorted(self):
        return sorted(self.submissions, key=lambda s: s.assignment.exercise_code, reverse=False)

    @property
    def submissions_dict_by_assignment_id(self):
        submission_dict = {}
        for submission in self.submissions:
            submission_dict[submission.assignment_id] = submission
        return submission_dict


class Group():
    def __init__(self, group_name, students, team):
        self.group_name = group_name
        self.students: List[Student] = students
        self.team: Team = team
        #self.filtered_students = filtered_students

    @property
    def selected_students_sorted_surname(self) -> List[Student]:
        return sorted(self.students, key=lambda student: student.student_surname.lower(), reverse=False)


class Team():
    team_name = None

    def __init__(self, team_name):
        self.team_id = None
        self.team_name = team_name
        self.team_full_name = ""
        self.assignments: List[Assignment] = []
        self.students: List[Student] = []
        self.filtered_students: List[Student] = []
        self.filtered = False
        self.submissions: List[Submission] = []
        self.error = False

    def update_team_data(self):
        for retry in range(0, 3):
            try:
                raw_team_data = run_graphql_query(main_query.replace("{", "<").replace("}", ">").replace("[", "{").replace("]", "}").format(name=self.team_name).replace("<", "{").replace(">", "}"))
            except JSONDecodeError:
                print(f"Json decoding error for {self.team_name}!")
                continue
            if "data" in raw_team_data:
                team_data = raw_team_data["data"]["team"]
                break
            elif "status" in raw_team_data and raw_team_data["status"] == 503:
                print(f"Timed out trying to get data from {self.team_name}! So far {retry + 1} attempts have been made")
        else:
            print(f"Given up trying to get data from {self.team_name}!")
            team_data = {"students": [],
                         "templates": []}
        self.team_full_name = team_data["displayName"]
        self.team_id = team_data["id"]

        for student in team_data["members"]:
            new_student = Student(student["user"]["id"], student["user"]["firstName"], student["user"]["lastName"], student["user"]["username"], student["email"])
            if student["user"]["username"] in config.ignored_usernames:
                new_student.to_ignore = True

            self.students.append(new_student)
        if config.student_csv_file_path:
            helpers.read_csv_students(config.student_csv_file_path, self.students)

        for template in team_data["templates"]:
            new_assignment = Assignment(template["id"], template["repl"]["title"], self, True, template["dueDate"])


            submissions = {}
            for submission in template["submissions"]:
                submissions[submission["author"]["id"]] = submission
            for student in self.students:
                if student.student_id in submissions:
                    # If submission exists
                    submission = submissions[student.student_id]
                    new_submission = Submission(submission["id"], submission["author"]["id"],new_assignment.assignment_id, None, submission["timeSubmitted"])
                    new_submission.assignment = new_assignment
                    new_submission.last_reviewed = submission["timeLastReviewed"]
                    new_submission.student = self.students_dict[new_submission.student_id]
                    new_submission.url = submission["repl"]["url"]

                    if submission["repl"]["ioTestResults"]:
                        for result in submission["repl"]["ioTestResults"]:
                            new_test = TestResult(result["id"], result["status"])
                            new_submission.test_results.append(new_test)
                else:
                    # If a submission doesn't exist, make a blank one
                    new_submission = Submission(-1, student.student_id, new_assignment.assignment_id, None, None)
                    new_submission.assignment = new_assignment
                    new_submission.student = self.students_dict[new_submission.student_id]
                new_assignment.submissions.append(new_submission)
                student.submissions.append(new_submission)
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
        if self.filtered:
            return self.filtered_students
        return self.students

    @property
    def selected_students_sorted_surname(self) -> List[Student]:
        return sorted(self.selected_students, key=lambda student: student.student_surname.lower(), reverse=False)

    @property
    def groups(self)-> Dict[str, Group]:
        group_dict = {}
        for student in self.students:
            if not student.group_name in group_dict.keys():
                group_dict[student.group_name] = Group(student.group_name, [], self)
            group_dict[student.group_name].students.append(student)
        return group_dict

    @property
    def teacher_initials(self):
        for teacher_initial in config.teacher_initials:
            if teacher_initial in self.team_name:
                return teacher_initial
        return ""

    @property
    def class_group(self):
        if self.team_name[0].isdigit() and self.team_name[1].isalpha():
            return self.team_name[0:2]
        else:
            return ""


main_query = """
query Foo {
  
  team: teamByUsername (username: "[name]") {
    ... on Team {
      displayName
      id
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
        dueDate
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
        master_jobs = []
        for team_name in team_names:
            jobs.append(executor.submit(build_team, team_name))
            time.sleep(0.5)
        if g.year.master_team_name:
            master_jobs.append(executor.submit(build_team, g.year.master_team_name))
        for job in jobs:
            teams.append(job.result())
        for job in master_jobs:
            g.master_team = job.result()

    #for team_name in team_names:
    #    new_team = Team(team_name)
    #    print(f"Fetching data for {team_name}!")
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
    return run_graphql_raw_query({"query": query})


def run_graphql_raw_query(query):
    response = requests.post("https://replit.com/graphql", json=query, headers=headers)
    to_return = response.json()
    return to_return


def get_templates(team_name):
    templates = []
    team_data = run_graphql_query(
        main_query.replace("{", "<").replace("}", ">").replace("[", "{").replace("]", "}").format(
            name=team_name).replace("<", "{").replace(">", "}"))["data"]["team"]
    for template in team_data["templates"]:
        new_assignment = Assignment(template["id"], template["repl"]["title"],None, True, None)
        new_template = Template(template["id"], template["repl"]["title"], new_assignment)
        templates.append(new_template)
    return templates, team_data["id"]


def delete_template_share_link(team_id, template_share_link:TemplateShareLink):
    query = {"operationName":"DeleteTemplateShareLink","variables":{"linkId":template_share_link.id,"teamId":team_id},"query":"mutation DeleteTemplateShareLink($teamId: Int!, $linkId: Int!) {\n  deleteTemplateShareLink(teamId: $teamId, linkId: $linkId) {\n    id\n    ...TemplateCopyingLinksTeam\n    __typename\n  }\n}\n\nfragment TemplateCopyingLinksTeam on Team {\n  id\n  displayName\n  templates {\n    id\n    ...TemplateCopyingTemplate\n    __typename\n  }\n  templateShareLinks {\n    id\n    ...TemplateCopyingShareLink\n    __typename\n  }\n  __typename\n}\n\nfragment TemplateCopyingTemplate on ReplTemplate {\n  id\n  url\n  repl {\n    id\n    title\n    language\n    __typename\n  }\n  __typename\n}\n\nfragment TemplateCopyingShareLink on TeamTemplateShareLink {\n  id\n  code\n  templates {\n    id\n    ...TemplateCopyingTemplate\n    __typename\n  }\n  timeCreated\n  __typename\n}\n"}
    run_graphql_raw_query(query)


def create_template_link(team_id, template_objs):
    template_ids = [x.id for x in template_objs if x.assignment.exercise_code]
    query = {"operationName":"CreateTemplateShareLink","variables":{"teamId":team_id,"templateIds":template_ids},"query":"mutation CreateTemplateShareLink($teamId: Int!, $templateIds: [Int!]!) {\n  createTemplateShareLink(teamId: $teamId, templateIds: $templateIds) {\n    id\n    ...TemplateCopyingLinksTeam\n    __typename\n  }\n}\n\nfragment TemplateCopyingLinksTeam on Team {\n  id\n  displayName\n  templates {\n    id\n    ...TemplateCopyingTemplate\n    __typename\n  }\n  templateShareLinks {\n    id\n    ...TemplateCopyingShareLink\n    __typename\n  }\n  __typename\n}\n\nfragment TemplateCopyingTemplate on ReplTemplate {\n  id\n  url\n  repl {\n    id\n    title\n    language\n    __typename\n  }\n  __typename\n}\n\nfragment TemplateCopyingShareLink on TeamTemplateShareLink {\n  id\n  code\n  templates {\n    id\n    ...TemplateCopyingTemplate\n    __typename\n  }\n  timeCreated\n  __typename\n}\n"}
    response = run_graphql_raw_query(query)
    raw_share_links = response["data"]['createTemplateShareLink']['templateShareLinks']
    share_links = []
    for raw_share_link in raw_share_links:
        share_link = TemplateShareLink(raw_share_link["id"], raw_share_link["code"], parser.parse(raw_share_link["timeCreated"]))
        share_links.append(share_link)
    share_links.sort(key=lambda share_link: share_link.time_created)
    newest_share_link = share_links[-1]
    return newest_share_link


def import_templates_from_template_link(template_link:TemplateShareLink, team_id, template_ids: List[int]):
    query = {"operationName":"TemplateCopyingUseLink","variables":{"teamId":team_id,"code":template_link.code,"content":template_ids,"withDates":False},"query":"mutation TemplateCopyingUseLink($teamId: Int!, $withDates: Boolean!, $code: String!, $content: [Int!]!) {\n  useTemplateShareLink(\n    teamId: $teamId\n    withDates: $withDates\n    code: $code\n    content: $content\n  )\n}\n"}
    response = run_graphql_raw_query(query)
    return response


def copy_templates_share_links(initial_team_name, destination_team_name, template_ids):
    templates, initial_team_id = get_templates(initial_team_name)
    _, destination_team_id = get_templates(destination_team_name)
    share_link = create_template_link(initial_team_id, templates)
    #template_ids = [x.id for x in templates if x.assignment.exercise_code in exercise_codes]
    template_ids = [int(x) for x in template_ids]
    import_templates_from_template_link(share_link, destination_team_id, template_ids)
    delete_template_share_link(initial_team_id, share_link)


def copy_templates(destination_team_id, template_ids):
    for template_id in template_ids:
        query = [{"operationName":"CopyProjectModalCopyTeamTemplate","variables":{"input":{"templateId":template_id,"destinationTeamId":destination_team_id}},"query":"mutation CopyProjectModalCopyTeamTemplate($input: CopyTeamTemplateInput!) {\n  copyTeamTemplate(input: $input) {\n    ... on Team {\n      id\n      displayName\n      __typename\n    }\n    ... on UserError {\n      message\n      __typename\n    }\n    ... on UnauthorizedError {\n      message\n      __typename\n    }\n    ... on NotFoundError {\n      message\n      __typename\n    }\n    __typename\n  }\n}\n"}]
        response = run_graphql_raw_query(query)
        print()
