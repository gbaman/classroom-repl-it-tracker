from typing import List

from flask import g

import config

class YearGroup():
    def __init__(self, name, master_classroom_id, classroom_ids, required_exercise_ids):
        self.name = name
        self.master_classroom_id = master_classroom_id
        self.classroom_ids = classroom_ids
        self.required_exercise_ids = required_exercise_ids


class Email():
    def __init__(self, mail_to, mail_subject, mail_body):
        self.mail_to = mail_to
        self.mail_subject = mail_subject
        self.mail_body = mail_body


def get_students_missing_work(classrooms):
    for classroom in classrooms:
        students_missing_work = []
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
                classroom.filtered_students = students_missing_work
    return classrooms


def send_emails(emails: List[Email], username=config.email_username, password=config.email_password, mail_from=config.email_mail_from):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    mimemsgs = []
    for email in emails:
        mimemsg = MIMEMultipart()
        mimemsg['From'] = mail_from
        mimemsg['To'] = email.mail_to
        mimemsg['Subject'] = email.mail_subject
        mimemsg.attach(MIMEText(email.mail_body, 'plain'))
        mimemsgs.append(mimemsg)

    connection = smtplib.SMTP(host='smtp.office365.com', port=587)
    connection.starttls()
    connection.login(username, password)
    for mimemsg in mimemsgs:
        connection.send_message(mimemsg)
    connection.quit()