import os
import traceback

from flask import Flask, render_template, request, make_response, redirect, flash, g

import forms
import repl

app = Flask(__name__)
app.secret_key = os.urandom(24)


#@app.before_request


@app.route('/old_landing')
def old_landing():
    cookie = repl.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms = repl.setup_classrooms(cookie)
            return render_template("main.html", classrooms=classrooms, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)
    return resp

@app.route("/")
def home():
    cookies = repl.check_cookie()
    resp = make_response()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    else:
        try:
            classrooms = repl.setup_classrooms(cookies)
            #repl.create_classroom("Testing321")
            return render_template("main.html", classrooms=classrooms, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)



@app.route("/incomplete")
def show_only_required():
    cookie = repl.check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms = repl.setup_classrooms(cookie)
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
        cookies = repl.get_login_cookie(form.username.data, form.password.data)
        if cookies:
            resp = make_response(redirect('/'))
            for key in cookies.keys():
                resp.set_cookie(str(key), str(cookies[key]))
            return resp
        flash("Login failed. This may be due to issues with the credentials, or you need to log into repl.it as usual on your computer at least once.", "danger")
        return render_template("login.html", form=form, title="Login")
    return render_template("login.html", next=next, form=form, title="Login")


@app.route("/clone", methods=['POST', 'GET'])
def clone():
    cookies = repl.check_cookie()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    classrooms = repl.setup_classrooms(cookies)

    form = forms.CloneForm(request.form)
    if request.method == 'POST':# and form.validate():
        master_classroom:repl.Classroom = g.master_classroom
        for classroom_id in form.classrooms.data:
            classroom:repl.Classroom = g.classrooms_dict[int(classroom_id)]
            for assignment_id in form.assignments.data:
                assignment = g.master_classroom.assignments_dict[int(assignment_id)]
                master_classroom.assignments_dict[assignment.assignment_id].safe_clone(classroom)

        # Handle publishing from draft of new activities
        classrooms = repl.setup_classrooms(cookies)
        for classroom_id in form.classrooms.data:
            classroom: repl.Classroom = g.classrooms_dict[int(classroom_id)]
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


@app.route("/run_task")
def run_task():
    cookies = repl.check_cookie()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    classrooms = repl.setup_classrooms(cookies)
    import tasks
    tasks.add_sam()



if __name__ == '__main__':
    app.run(port=4999)
