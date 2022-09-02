import datetime

from wtforms import StringField, PasswordField, Form, validators, SelectMultipleField, DateTimeField
from wtforms.fields import DateField
from flask import g
class LoginForm(Form):
    username = StringField("Email address", [validators.DataRequired()])
    password = PasswordField("Password", [validators.DataRequired()])


class CloneForm(Form):
    teams = SelectMultipleField("Teams", choices=[])

    assignments = SelectMultipleField("Assignments", choices=[])
    time_due = DateField("Due - Not working right now" )


    def __init__(self, *args, **kwargs):
        super(CloneForm, self).__init__(*args, **kwargs)
        teams = g.teams
        for team in teams:
            if not team.error:
                self.teams.choices.append([team.team_id, team.team_name])
        self.teams.choices = sorted(self.teams.choices, key=lambda x: x[1])

        master_team = g.master_team
        for assignment in master_team.assignments:
            self.assignments.choices.append([assignment.assignment_id, assignment.assignment_name])
        self.assignments.choices = sorted(self.assignments.choices, key=lambda x: x[1])
        self.time_due.data = datetime.datetime.now() + datetime.timedelta(weeks=2)
