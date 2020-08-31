import os
import traceback

from flask import Flask, render_template, request, make_response, redirect, flash

import forms
import repl
from config import required_exercise_ids

app = Flask(__name__)
app.secret_key = os.urandom(24)


def check_cookie():
    if "ajs_user_id" in request.cookies:
        cookie_to_return = ""
        for cookie in request.cookies.items():
            cookie_to_return = f"{cookie_to_return}{cookie[0]}={cookie[1]};"
        return cookie_to_return
    else:
        return False


@app.route('/old_landing')
def old_landing():
    cookie = check_cookie()
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
    cookies = check_cookie()
    resp = make_response()
    if not cookies:
        flash("Login credentials expired, please log in again", "warning")
        return redirect("/login")
    else:
        try:
            classrooms = repl.setup_classrooms(cookies)
            return render_template("main.html", classrooms=classrooms, title="All Student Data")
        except:
            print(traceback.print_exc())
            resp.set_cookie("ajs_user_id", "", expires=0)
            resp.set_cookie("connect.sid", "", expires=0)



@app.route("/incomplete")
def show_only_required():
    cookie = check_cookie()
    resp = make_response(render_template("missing_cookie.html"))
    if cookie:
        try:
            classrooms = repl.setup_classrooms(cookie)
            for classroom in classrooms:
                students_missing_work = []
                for student in classroom.students:
                    for required in required_exercise_ids:
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


if __name__ == '__main__':
    app.run(port=4999)
