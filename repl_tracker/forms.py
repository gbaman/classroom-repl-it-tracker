from wtforms import StringField, PasswordField, Form, validators

class LoginForm(Form):
    username = StringField("Username", [validators.DataRequired()])
    password = PasswordField("Password", [validators.DataRequired()])