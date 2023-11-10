import datetime
import os
import traceback
from typing import List

from flask import Flask, render_template, request, make_response, redirect, flash, g

import forms
import repl_classroom
import repl_teams
import json
import csv

import config
import helpers

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/old_landing')
def old_landing():
    cookie = repl_classroom.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms, status = repl_teams.setup_all_teams(cookie)
            return render_template("main.html", classrooms=classrooms, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=datetime.datetime.now() + datetime.timedelta(days=60))
            resp.set_cookie("connect.sid", "", expires=datetime.datetime.now() + datetime.timedelta(days=60))
    return resp

@app.route("/")
def home():
    cookies = repl_classroom.check_cookie()
    resp = make_response()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    else:
        try:
            teams, status = repl_teams.setup_all_teams(cookies)
            #repl.create_classroom("Testing321")
            return render_template("main.html", classrooms=teams, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=datetime.datetime.now() + datetime.timedelta(days=60))
            resp.set_cookie("connect.sid", "", expires=datetime.datetime.now() + datetime.timedelta(days=60))
            return redirect("/login")



@app.route("/incomplete")
def show_only_required():
    cookies = repl_classroom.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookies:
        try:
            classrooms, status = repl_teams.setup_all_teams(cookies)
            classrooms = helpers.get_students_missing_work(classrooms)

            return render_template("main.html", classrooms=classrooms, title="Students with incomplete work", email=True)
        except:
            print(traceback.print_exc())
            #resp.set_cookie("ajs_user_id", "", expires=0)
            #resp.set_cookie("connect.sid", "", expires=0)
    return resp


@app.route("/incomplete_reminder/<team_name>")
def send_incomplete_reminders(team_name):
    cookies = repl_classroom.check_cookie()
    if cookies:
        classrooms, status = repl_teams.setup_all_teams(cookies)
        classrooms = helpers.get_students_missing_work(classrooms, days_offset=1)
        emails_to_send = []
        for classroom in classrooms:
            if classroom.team_name == team_name:
                for student in classroom.filtered_students:
                    if not student.student_first_name:
                        continue
                    subject_line = f"Incomplete Computer Science Homework ({classroom.class_group} {classroom.teacher_initials}) - {student.student_first_name.capitalize()} {student.student_surname.capitalize()}"
                    outstanding_activities = []
                    for submission in student.submissions_sorted:
                        if not submission.completed and submission.important:
                            if submission.assignment.datetime_due:
                                outstanding_activities.append(f"- {submission.assignment.assignment_name} (Due {submission.assignment.datetime_due.strftime('%A %d/%m/%Y')}) | {submission.completed_symbol_without_important[1]}")
                            else:
                                outstanding_activities.append(  f"- {submission.assignment.assignment_name}")
                    outstanding_activities_str = "\n".join(outstanding_activities)
                    body = f"""Dear {student.student_first_name.capitalize()},

Our check on your progress has brought up that you have {len(outstanding_activities)} incomplete exercise/s on replit, that had been set for homework. Please see the list below for the exercises that you have outstanding.
{outstanding_activities_str}

If you are having issues with these exercises, please email Miss Page or Mr Mulholland for further help.

- Computer Science Department
"""
                    #emails_to_send.append(helpers.Email(student.student_email, subject_line, body))
                    emails_to_send.append(helpers.Email(student.student_email, subject_line, body))
        else:
            print(f"No classroom found by that name {team_name}")
        teacher_cc_email = []
        for teacher_cc in config.email_cced:
            if teacher_cc[0] in team_name:
                teacher_cc_email.append(teacher_cc[1])
        helpers.send_emails(emails_to_send, cced_addresses=teacher_cc_email)
        flash(f"Reminder emails successfully sent to {len(emails_to_send)} students!", "success")
        return redirect("/")



@app.route("/login", methods=['POST', 'GET'])
def login():
    g.year = 0
    cookie_value = request.cookies.get("repl_token")
    if cookie_value:
        valid = True
        if valid:
            return redirect('/')

    form = forms.LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        captcha_key = request.form.get('h-captcha-response')
        cookies, response = repl_teams.get_teams_login_cookie(form.username.data, form.password.data, captcha_key)
        if cookies:
            resp = make_response(redirect('/'))
            for key in cookies.keys():
                resp.set_cookie(str(key), str(cookies[key]), expires=datetime.datetime.now() + datetime.timedelta(days=60))
            return resp
        flash(f"Login failed. This may be due to issues with the credentials, or you need to log into repl.it as usual on your computer at least once. The error was \"{json.loads(response.text)['message']}\".", "danger")
        return render_template("login.html", form=form, title="Login")
    return render_template("login.html", next=next, form=form, title="Login")


@app.route("/clone", methods=['POST', 'GET'])
def clone():
    cookies = repl_classroom.check_cookie()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    teams, status = repl_teams.setup_all_teams(cookies)
    g.teams = teams

    form = forms.CloneForm(request.form)
    if request.method == 'POST':# and form.validate():
        #for team_name in form.teams.data:
            #repl_teams.copy_templates_share_links(g.year.master_team_name, team_name, form.assignments.data)

        for team_id in form.teams.data:
            repl_teams.copy_templates(team_id, form.assignments.data)

        flash("Clone successful", "success")

    return render_template("clone.html", form=form, title="Clone")


@app.route("/change_year/<year>")
def change_year(year):
    resp = make_response(redirect("/"))
    resp.set_cookie('year_id', year)
    return resp


@app.route("/export_assignments")
def export_assignments():
    return "Page not enabled"
    cookies = repl_classroom.check_cookie()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    classrooms, status = repl_teams.setup_all_teams(cookies)
    # Setup csv writer and file
    with open('data.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile, dialect='excel')
        for classroom in classrooms:
            # Create blank row and classroom name row for each classroom
            csv_writer.writerow([""])
            csv_writer.writerow([classroom.team_name])
            # Create assignments name row for each classroom
            assignments = ["First name", "Surname"]
            for assignment in classroom.assignments_sorted:
                assignments.append(assignment.exercise_code)
            csv_writer.writerow(assignments)
            # For each student in the class, create a row with their data
            for student in classroom.selected_students_sorted_surname:
                student_row = [student.student_first_name, student.student_surname]
                for submission in student.submissions_sorted:
                    student_row.append(submission.completed)
                csv_writer.writerow(student_row)
    return "A CSV file has been created with all the data titled data.csv"





@app.route("/run_task")
def run_task():
    return "Page not enabled"
    cookies = repl_classroom.check_cookie()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    classrooms = repl_classroom.setup_classrooms(cookies)
    import tasks
    tasks.add_sam()



if __name__ == '__main__':
    app.run(port=4999)
