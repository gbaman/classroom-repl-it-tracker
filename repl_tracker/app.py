import os
import traceback

from flask import Flask, render_template, request, make_response, redirect, flash, g

import forms
import repl_classroom
import repl_teams
import json
import csv

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/old_landing')
def old_landing():
    cookie = repl_classroom.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms = repl_teams.setup_all_teams(cookie)
            return render_template("main.html", classrooms=classrooms, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)
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
            teams = repl_teams.setup_all_teams(cookies)
            #repl.create_classroom("Testing321")
            return render_template("main.html", classrooms=teams, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)



@app.route("/incomplete")
def show_only_required():
    cookie = repl_classroom.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms = repl_classroom.setup_classrooms(cookie)
            for classroom in classrooms:
                students_missing_work = []
                for student in classroom.students:
                    for required in g.year.required_exercise_ids:
                        for submission in student.submissions:
                            if submission.assignment.exercise_code == required:
                                if not submission.completed:
                                    submission.important = True
                                    if student not in students_missing_work:
                                        students_missing_work.append(student)
                                break
                classroom.filtered_students = students_missing_work
            return render_template("main.html", classrooms=classrooms, title="Students with incomplete work", email=True)
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)
    return resp


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
        cookies, response = repl_classroom.get_login_cookie(form.username.data, form.password.data)
        if cookies:
            resp = make_response(redirect('/'))
            for key in cookies.keys():
                resp.set_cookie(str(key), str(cookies[key]))
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
    classrooms = repl_classroom.setup_classrooms(cookies)

    form = forms.CloneForm(request.form)
    if request.method == 'POST':# and form.validate():
        master_classroom:repl_classroom.Classroom = g.master_classroom
        for classroom_id in form.classrooms.data:
            classroom:repl_classroom.Classroom = g.classrooms_dict[int(classroom_id)]
            for assignment_id in form.assignments.data:
                assignment = g.master_classroom.assignments_dict[int(assignment_id)]
                master_classroom.assignments_dict[assignment.assignment_id].safe_clone(classroom)

        # Handle publishing from draft of new activities
        classrooms = repl_classroom.setup_classrooms(cookies)
        for classroom_id in form.classrooms.data:
            classroom: repl_classroom.Classroom = g.classrooms_dict[int(classroom_id)]
            for assignment_id in form.assignments.data:
                assignment = g.master_classroom.assignments_dict[int(assignment_id)]
                for classroom_assignment in classroom.assignments:
                    if classroom_assignment.assignment_name == assignment.assignment_name:
                        classroom_assignment.publish()
                        classroom_assignment.set_due_date(form.time_due.data)
                        break

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
    classrooms = repl_classroom.setup_classrooms(cookies)
    # Setup csv writer and file
    with open('data.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile, dialect='excel-tab')
        for classroom in classrooms:
            # Create blank row and classroom name row for each classroom
            csv_writer.writerow([""])
            csv_writer.writerow([classroom.classroom_name])
            # Create assignments name row for each classroom
            assignments = ["First name", "Surname"]
            for assignment in classroom.assignments_sorted:
                assignments.append(assignment.exercise_code)
            csv_writer.writerow(assignments)
            # For each student in the class, create a row with their data
            for student in classroom.selected_students_sorted_surname:
                student_row = [student.student_first_name, student.student_surname]
                for submission in student.submissions_sorted:
                    # Check if repl has returned a submission, if not, just add no submission
                    if submission.submission_status:
                        student_row.append(submission.submission_status)
                    else:
                        student_row.append("No submission")
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
