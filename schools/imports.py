import math

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from openpyxl import load_workbook
from django.core.exceptions import ObjectDoesNotExist

from email_validator import validate_email, EmailNotValidError

from .models import School, TerAdmin, SchoolType


def get_sheet(form):
    workbook = load_workbook(form.cleaned_data['import_file'])
    sheet = workbook.active
    return sheet


def cheak_col_match(sheet, fields_names_set):
    i = 0
    col_count = sheet.max_column
    sheet_fields = []
    sheet_col = {}
    if sheet[f"A2"].value is None:
        return {"status": "Error", "error_type": "EmptySheet"}
    try:
        for col_header in range(1, col_count+1):
            if sheet.cell(row=1,column=col_header).value is not None:
                sheet_fields.append(sheet.cell(row=1,column=col_header).value)
                sheet_col[col_header] = sheet.cell(row=1,column=col_header).value
        missing_fields = []
        for field in fields_names_set:
            if field not in sheet_fields:
                missing_fields.append(field)
        if len(missing_fields) != 0:
            return {"status": "Error", "error_type": "MissingFieldsError", "missing_fields": missing_fields}
    except IndexError:
        return {"status": "Error", "error_type": IndexError}
    return {"status": "OK", "sheet_col": sheet_col}


def load_worksheet_dict(sheet, fields_names_set):
    row_count = sheet.max_row
    sheet_dict = {}
    for col in fields_names_set:
        sheet_dict[fields_names_set[col]] = []
        for row in range(2, row_count+1): 
            snils = sheet[f"A{row}"].value
            if snils != None:
                cell_value = sheet.cell(row=row,column=col).value
                try: cell_value = str(math.floor(cell_value))
                except (ValueError, TypeError): pass
                sheet_dict[fields_names_set[col]].append(cell_value)
    return sheet_dict


def schools(form):
    try:
        sheet = get_sheet(form)
    except IndexError:
        return ['Import', 'IndexError']
 
    #Требуемые поля таблицы
    fields_names = {
        "ИНН", 
        "Полное наименование",
        "Сокращенное наименование",
        "Номер школы",
        "Тип школы",
        "Email",
        "ТУ/ДО",
        "Населённый пункт"
    }
    
    cheak_col_names = cheak_col_match(sheet, fields_names)
    if cheak_col_names["status"] == "Error":
        return cheak_col_names

    sheet = load_worksheet_dict(sheet, cheak_col_names["sheet_col"])

    missing_fields = []
    added_schools = 0
    updated_schools = 0
    for row in range(len(sheet['ИНН'])):
        responce = load_school(sheet, row)
        if responce[0] == 'MissingField':
            missing_fields.append(responce)
        elif responce[1]: added_schools += 1
        else: updated_schools += 1

    return {
        "status": "OK",
        "added_schools": added_schools,
        "updated_schools": updated_schools,
        "missing_fields": missing_fields
    }


def is_missing(field):
    if field != "" and field != None:
        return field.strip()
    return True

    
def load_school(sheet, row):
    missing_fields = []

    inn = is_missing(sheet["ИНН"][row])
    if inn == True: missing_fields.append("ИНН")
    email = is_missing(sheet["Email"][row])
    try: email = validate_email(email)["email"]
    except EmailNotValidError: missing_fields.append("Email")
    name = is_missing(sheet["Полное наименование"][row])
    if name == True: missing_fields.append("Полное наименование")
    short_name = is_missing(sheet["Сокращенное наименование"][row])
    if short_name == True: missing_fields.append("Сокращенное наименование")
    city = is_missing(sheet["Населённый пункт"][row])
    if city == True: missing_fields.append("Населённый пункт")
    number = is_missing(sheet["Сокращенное наименование"][row])
    if number == True or not(number.isnumeric()): number = None
    else: number = int(number)
    
    ter_admin = is_missing(sheet["ТУ/ДО"][row])
    try: ter_admin = TerAdmin.objects.get(name=ter_admin)
    except ObjectDoesNotExist: missing_fields.append("ТУ/ДО")
    school_type = is_missing(sheet["Тип школы"][row])
    try: school_type = SchoolType.objects.get(short_name=school_type)
    except ObjectDoesNotExist: school_type = None

    if len(missing_fields) > 0:
        return ['MissingField', missing_fields, row+2]
    
    school, is_new = School.objects.get_or_create(
        inn=inn,
        ter_admin=ter_admin
    )
    school.email = email
    school.name = name
    school.short_name = short_name
    school.city = city
    school.number = number
    school.save()

    return ['OK', is_new]