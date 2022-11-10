import csv
import datetime
import tempfile
from typing import List

import requests
from flask import g
import repl_teams

import config
import repl_teams


class Email():
    def __init__(self, mail_to, mail_subject, mail_body):
        self.mail_to = mail_to
        self.mail_subject = mail_subject
        self.mail_body = mail_body


def get_students_missing_work(classrooms:List["repl_teams.Team"], days_offset: int = 0):

    for classroom in classrooms:
        students_missing_work = []
        classroom.filtered_students = []
        classroom.filtered = True
        for student in classroom.students:
            if student.student_username in config.ignored_usernames:
                continue
            for required in g.year.required_exercise_ids:
                for submission in student.submissions:
                    if submission.assignment and submission.assignment.exercise_code == str(required):
                        if not submission.completed:
                            submission.important = True
                            if student not in students_missing_work:
                                students_missing_work.append(student)
                        break
            for submission in student.submissions:
                if submission.assignment.datetime_due and submission.assignment.datetime_due.replace(tzinfo=None) < datetime.datetime.now().replace(tzinfo=None) + datetime.timedelta(days=days_offset) and not submission.completed:
                    submission.important = True
                    if student not in students_missing_work:
                        students_missing_work.append(student)
        for student in classroom.students:
            student.hide = True
        for student in students_missing_work:
            student.hide = False
        classroom.filtered_students = students_missing_work
    return classrooms


def send_emails(emails: List[Email], username=config.email_username, password=config.email_password, mail_from=config.email_mail_from, cced_addresses=config.email_cced):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    mimemsgs = []

    for email in emails:
        mimemsg = MIMEMultipart()
        mimemsg['From'] = mail_from
        mimemsg['To'] = email.mail_to
        mimemsg['Subject'] = email.mail_subject
        mimemsg['Cc'] = ','.join(cced_addresses)
        mimemsg.attach(MIMEText(email.mail_body, 'plain'))
        mimemsgs.append(mimemsg)

    connection = smtplib.SMTP(host='smtp.office365.com', port=587)
    connection.starttls()
    connection.login(username, password)
    for mimemsg in mimemsgs:
        connection.send_message(mimemsg)
    connection.quit()


def read_csv_students(csv_path, students: List["repl_teams.Student"]):
    with requests.Session() as s:
        download = s.get(csv_path)

        decoded_content = download.content.decode('utf-8')

        csv_reader = csv.reader(decoded_content.splitlines(), delimiter=',', dialect='excel')
        #csv_reader = csv.reader(csvfile, dialect='excel')
        for line in list(csv_reader)[1:]:
            if line:
                email_address = line[0]
                for student in students:
                    if student.student_email == email_address:
                        student.group_name = line[1]
                        break
        return students

