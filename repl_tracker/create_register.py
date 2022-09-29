# Simple tool to create a student_register file for subgroups of students

import openpyxl
import csv

HEADING_ROW_ID = 3
MARKBOOK_PATH = "LS_2024_Markbook.xlsx"
OUTPUT_PATH = "student_register.csv"

markbook = openpyxl.load_workbook(MARKBOOK_PATH)
markbook_sheet = markbook.active

lines = [["Student Email", "Class"]]


def find_column_by_heading(heading_str):
    for cell_index, cell in enumerate(markbook_sheet[HEADING_ROW_ID]):
        if cell.value == heading_str:
            found_column_id = cell_index
            break
    else:
        raise Exception("Unable to find column id!")
    return found_column_id

for index, row in enumerate(markbook_sheet.iter_rows()):
    if index >= HEADING_ROW_ID:
        student_email = row[find_column_by_heading("Email")].value
        student_set = row[find_column_by_heading("Set")].value
        student_teacher = row[find_column_by_heading("Teacher")].value
        lessons = row[find_column_by_heading("Lessons")].value
        lines.append([student_email, f"{student_set} ({student_teacher}) : {lessons}"])


with open(OUTPUT_PATH, 'w', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerows(lines)