import traceback

from flask import Flask, render_template, request, make_response

import repl
from config import required_exercise_ids

app = Flask(__name__)


def check_cookie():
    if "ajs_user_id" in request.cookies:
        cookie_to_return = ""
        for cookie in request.cookies.items():
            cookie_to_return = f"{cookie_to_return}{cookie[0]}={cookie[1]};"
        return cookie_to_return
    else:
        return False


@app.route('/')
def hello_world():
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


if __name__ == '__main__':
    app.run()
