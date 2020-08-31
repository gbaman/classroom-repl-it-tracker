from wtforms import StringField, PasswordField, Form, validators, SelectMultipleField
from flask import g
class LoginForm(Form):
    username = StringField("Username", [validators.DataRequired()])
    password = PasswordField("Password", [validators.DataRequired()])


class CloneForm(Form):
    classrooms = SelectMultipleField("Classrooms", choices=[])

    assignments = SelectMultipleField("Assignments", choices=[])

    def __init__(self, *args, **kwargs):
        super(CloneForm, self).__init__(*args, **kwargs)
        classrooms = g.classrooms
        for classroom in classrooms:
            self.classrooms.choices.append([classroom.classroom_id, classroom.classroom_name])
        self.classrooms.choices = sorted(self.classrooms.choices, key=lambda x: x[1])

        master_classroom = g.master_classroom
        for assignment in master_classroom.assignments:
            self.assignments.choices.append([assignment.assignment_id, assignment.assignment_name])
        self.assignments.choices = sorted(self.assignments.choices, key=lambda x: x[1])
