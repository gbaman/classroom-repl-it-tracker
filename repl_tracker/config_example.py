# Rename this file to config.py first

from config_helper import YearGroup

# Example below of how to define a "year group".
# YearGroup("Year 10",      123456,           [123456, 123457, 123458, 123459],          ['1.0', '1.1', '1.2', '5.2'])
#           Name       Master classroom ID  All classroom IDs in this year group   Required exercises (using 1.1 etc format)
# The minimum required example below would be
# years = [YearGroup("YEAR-NAME", 123456, [123456], [])]

# System supports as many year groups as required.
# You can get the classroom ID from the URL on repl classroom.

years = [YearGroup("YEAR-NAME", 123456, [123456], []),

         ]

# If you want to ignore any users
ignored_usernames = []

# Used to create subgroups in a single Team. Format should be email_address, class_name
student_csv_file_path = ""

# Used for email reminders for students
email_username = ""
email_password = ""
email_mail_from = ""
