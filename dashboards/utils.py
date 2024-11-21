from decimal import Decimal
import matplotlib.pyplot as plt
import io
import base64
from textwrap import fill
from django.utils.html import mark_safe
from django.db.models import Sum

from reports.models import Answer, Report, SchoolReport, Section
from reports.utils import count_points, count_points_field, count_section_points


# Function to generate chart for school report
def generate_school_report_chart(data, categories):
    plt.figure(figsize=(12, 5))  # Adjust figure size
    x = range(len(categories))
    width = 0.5 / len(data)  # Adjust width based on the number of years

    # Plot bars for each year
    for i, (year, values) in enumerate(data.items()):
        plt.bar([j + i * width for j in x], values, width=width, label=str(year), align="center", color="#a61849" if i % 2 == 0 else "#ffc600")
    
    # Wrap the category labels to prevent overlap
    wrapped_categories = [fill((f"{label.number }. { label.name }"), width=30) for label in categories]
    plt.xticks([i + (len(data) / 2 - 0.5) * width for i in x], wrapped_categories, ha="center", fontsize=10, fontweight="300")
    plt.ylabel("Баллы", fontsize=12, fontweight="300")
    plt.legend(fontsize=10, loc="upper right", frameon=True, fancybox=True, shadow=True)
    plt.tight_layout()
    
    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    image_png = buf.getvalue()
    buf.close()

    # Encode the image to base64 to use it in an HTML context
    image_base64 = base64.b64encode(image_png).decode("utf-8")
    return mark_safe(f'<img src="data:image/png;base64,{image_base64}"/>')

def calculate_stats_and_section_data(f_years, reports, sections, s_reports):
    stats = {}
    section_data = {}
    for year in f_years:
        stats[year] = {
            "green_zone": SchoolReport.objects.filter(zone="G", report__year=year).count(),
            "yellow_zone": SchoolReport.objects.filter(zone="Y", report__year=year).count(),
            "red_zone": SchoolReport.objects.filter(zone="R", report__year=year).count(),
        }
        section_data[year] = []
        for section in sections:
            section_obj = Section.objects.filter(name=section.name, report__in=reports, report__year=year)
            
            section_data[year].append(
                Answer.objects.filter(question__sections__in=section_obj, s_report__report__year=year).aggregate(points_sum=Sum("points"))["points_sum"] or Decimal(0)
            )
            stats[year][section.name] = {
                "green_zone": 0,
                "yellow_zone": 0,
                "red_zone": 0,
            }
            s_reports_year = s_reports.filter(report__year=year)
            for s_report in s_reports_year:
                color = count_section_points(s_report, section)
                if color == "G":
                    stats[year][section.name]["green_zone"] += 1
                elif color == "Y":
                    stats[year][section.name]["yellow_zone"] += 1
                elif color == "R":
                    stats[year][section.name]["red_zone"] += 1
    return stats, section_data

def calculate_stats(year, s_reports):
    stats = {}
    reports = Report.objects.filter(schools__in=s_reports).distinct()
    sections = Section.objects.filter(report__year=year, report__in=reports)
    overall_stats = {}
    overall_stats["green_zone"] = [0, "0.0%"]
    overall_stats["yellow_zone"] = [0, "0.0%"]
    overall_stats["red_zone"] = [0, "0.0%"]
    s_reports_year = s_reports.filter(report__year=year)
    for section in sections.order_by('id'):
        stats[section.name] = {
            "green_zone": [0, "0.0%"],
            "yellow_zone": [0, "0.0%"],
            "red_zone": [0, "0.0%"],
        }
        for s_report in s_reports_year:
            color = count_section_points(s_report, section)
            if color == "G":
                stats[section.name]["green_zone"][0] += 1
                stats[section.name]["green_zone"][1] = f'{stats[section.name]["green_zone"][0] / s_reports_year.count() * 100:.1f}%'
            elif color == "Y":
                stats[section.name]["yellow_zone"][0] += 1
                stats[section.name]["yellow_zone"][1] = f'{stats[section.name]["yellow_zone"][0] / s_reports_year.count() * 100:.1f}%'
            elif color == "R":
                stats[section.name]["red_zone"][0] += 1
                stats[section.name]["red_zone"][1] = f'{stats[section.name]["red_zone"][0] / s_reports_year.count() * 100:.1f}%'
    s_reports = s_reports.filter(report__in=reports)
    overall_stats["green_zone"][0] = sum([1 for s_report in s_reports if s_report.zone == "G"])
    overall_stats["yellow_zone"][0] = sum([1 for s_report in s_reports if s_report.zone == "Y"])
    overall_stats["red_zone"][0] = sum([1 for s_report in s_reports if s_report.zone == "R"])
    try:
        overall_stats["green_zone"][1] = f'{overall_stats["green_zone"][0] / s_reports_year.count() * 100:.1f}%'
        overall_stats["yellow_zone"][1] = f'{overall_stats["yellow_zone"][0] / s_reports_year.count() * 100:.1f}%'
        overall_stats["red_zone"][1] = f'{overall_stats["red_zone"][0] / s_reports_year.count() * 100:.1f}%'
    except ZeroDivisionError:
        pass
    return stats, overall_stats

def generate_ter_admins_report_csv(year, schools, s_reports):
    import xlsxwriter
    from django.http import HttpResponse
    from reports.models import Section, Field
    from io import BytesIO

    # Create an in-memory output file for the Excel workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })
    cell_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })

    # Write header row
    header = ['ТУ/ДО', 'Уровень образования', 'Школа', 'Итого баллов', ]
    
    sections = Section.objects.filter(report__year=year).distinct().order_by('number')
    for section in sections:
        header.append(f"{section.number}. {section.name}")

    for col, value in enumerate(header):
        worksheet.write(0, col, value, header_format)
        # Set column width based on text length
        text_length = len(value)
        width = min(max(text_length * 1.1, 20), 50)  # Scale by 1.2, min 20, max 50
        worksheet.set_column(col, col, width)
    # Add header for criteria count/percentage
    worksheet.merge_range(0, len(header), 0, len(header) + 1, 'Кол-во/доля критериев школы в зелёной зоне', header_format)
    header.extend(['Количество', 'Доля'])
    worksheet.merge_range(0, len(header), 0, len(header) + 1, 'Кол-во/доля критериев школы в жёлтой зоне', header_format)
    header.extend(['Количество', 'Доля'])
    worksheet.merge_range(0, len(header), 0, len(header) + 1, 'Кол-во/доля критериев школы в красной зоне', header_format)
    header.extend(['Количество', 'Доля'])   
    # Set row height based on longest text in header
    max_text_length = max(len(str(cell)) for cell in header)
    # Estimate ~15 chars per line at column width, add padding
    num_lines = (max_text_length / 15) + 1  
    row_height = num_lines * 15 # ~15 points per line
    worksheet.set_row(0, row_height)

    # Write data rows
    row_num = 1
    red_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter', 
        'text_wrap': True,
        'border': 1,
        'bg_color': '#FFC7CE'  # Light red
    })
    yellow_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True, 
        'border': 1,
        'bg_color': '#FFEB9C'  # Light yellow
    })
    green_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1,
        'bg_color': '#C6EFCE'  # Light green
    })
    for school in schools:
        school_reports = s_reports.filter(school=school, report__year=year)
        if not school_reports.exists():
            continue
            
        for report in school_reports:
            row = [
                school.ter_admin.__str__(),
                school.get_ed_level_display(),
                school.name,
                report.points
            ]
            
            # Add section points
            for section in sections:                
                points = Answer.objects.filter(question__in=section.fields.all(), s_report=report).aggregate(Sum('points'))['points__sum'] or 0
                row.append(points)

            for col, value in enumerate(row):
                if col < 3:  # School info columns
                    worksheet.write(row_num, col, value, cell_format)
                elif col == 3:  # Total points column
                    format_to_use = {
                        'R': red_format,
                        'Y': yellow_format,
                        'G': green_format,
                        'W': cell_format
                    }[report.zone]
                    worksheet.write(row_num, col, value, format_to_use)
                else:  # Section points columns
                    section = sections[col-4]
                    zone = count_section_points(report, section)
                    format_to_use = {
                        'R': red_format,
                        'Y': yellow_format,
                        'G': green_format,
                        'W': cell_format
                    }[zone]
                    worksheet.write(row_num, col, value, format_to_use)

            # Set row height to fit text
            # Calculate criteria counts and percentages
            total_criteria = Answer.objects.filter(s_report=report).count()
            green_count = Answer.objects.filter(s_report=report, zone='G').count()
            yellow_count = Answer.objects.filter(s_report=report, zone='Y').count() 
            red_count = Answer.objects.filter(s_report=report, zone='R').count()

            # Calculate percentages
            green_pct = f"{(green_count/total_criteria)*100:.1f}%" if total_criteria > 0 else "0.0%"
            yellow_pct = f"{(yellow_count/total_criteria)*100:.1f}%" if total_criteria > 0 else "0.0%"
            red_pct = f"{(red_count/total_criteria)*100:.1f}%" if total_criteria > 0 else "0.0%"

            # Write counts and percentages
            worksheet.write(row_num, len(header)-6, green_count, green_format)
            worksheet.write(row_num, len(header)-5, green_pct, green_format)
            worksheet.write(row_num, len(header)-4, yellow_count, yellow_format)
            worksheet.write(row_num, len(header)-3, yellow_pct, yellow_format)
            worksheet.write(row_num, len(header)-2, red_count, red_format)
            worksheet.write(row_num, len(header)-1, red_pct, red_format)
            worksheet.set_row(row_num, len(school.name) * 1)  # Auto-fit row height
            row_num += 1



    total = [
        'Итого',
        '',
        '',
        0,
    ]
    total_sum = 0
    for section in sections:
        section_total = Answer.objects.filter(question__in=section.fields.all(), s_report__in=s_reports).aggregate(Sum('points'))['points__sum'] or 0
        total.append(section_total)
        total_sum += section_total
    total[3] = total_sum
    for col, value in enumerate(total):
        worksheet.write(row_num, col, value, header_format)
    row_num += 1

    # Add count of schools in green zone
    worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в зелёной зоне', header_format)
    green_schools_count = len([r for r in s_reports if count_points(r)[0] == 'G'])
    green_schools = f"{green_schools_count} ({(green_schools_count/len(s_reports))*100:.1f}%)"
    worksheet.write(row_num, 3, green_schools, green_format)
    # Add count of schools in green zone for each section
    for col, section in enumerate(sections, start=4):
        green_section_count = len([r for r in s_reports if count_section_points(r, section) == 'G'])
        green_section_schools = f"{green_section_count} ({(green_section_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, col, green_section_schools, green_format)
    row_num += 1

    # Add count of schools in yellow zone
    worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в жёлтой зоне', header_format)
    yellow_schools_count = len([r for r in s_reports if count_points(r)[0] == 'Y'])
    yellow_schools = f"{yellow_schools_count} ({(yellow_schools_count/len(s_reports))*100:.1f}%)"
    worksheet.write(row_num, 3, yellow_schools, yellow_format)
    # Add count of schools in yellow zone for each section
    for col, section in enumerate(sections, start=4):
        yellow_section_count = len([r for r in s_reports if count_section_points(r, section) == 'Y'])
        yellow_section_schools = f"{yellow_section_count} ({(yellow_section_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, col, yellow_section_schools, yellow_format)
    row_num += 1

    # Add count of schools in red zone
    worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в красной зоне', header_format)
    red_schools_count = len([r for r in s_reports if count_points(r)[0] == 'R'])
    red_schools = f"{red_schools_count} ({(red_schools_count/len(s_reports))*100:.1f}%)"
    worksheet.write(row_num, 3, red_schools, red_format)
    # Add count of schools in red zone for each section
    for col, section in enumerate(sections, start=4):
        red_section_count = len([r for r in s_reports if count_section_points(r, section) == 'R'])
        red_section_schools = f"{red_section_count} ({(red_section_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, col, red_section_schools, red_format)
    row_num += 1

    # Add section field details
    row_num += 1
    for section in sections:
        # Write section header
        worksheet.write(row_num, 0, f'Раздел {section.number}', header_format)
        row_num += 1

        # Write field headers
        worksheet.write(row_num, 0, 'ТУ/ДО', header_format) 
        worksheet.write(row_num, 1, 'Уровень образования', header_format)
        worksheet.write(row_num, 2, 'Школа', header_format)
        worksheet.write(row_num, 3, 'Всего баллов', header_format)
        
        fields = section.fields.all()
        for col, field in enumerate(fields, start=4):
            worksheet.write(row_num, col, field.name, header_format)
        row_num += 1
        # Set row height based on longest text in header
        max_text_length = max(len(str(cell)) for cell in header)
        # Estimate ~15 chars per line at column width, add padding
        num_lines = (max_text_length / 15) + 1  
        row_height = num_lines * 15 # ~15 points per line
        worksheet.set_row(row_num-1, row_height)

        # Write data for each school
        for report in s_reports:
            school = report.school
            row = [
                school.ter_admin.__str__(),
                school.get_ed_level_display(),
                school.name,
                0
            ]
            
            section_total = 0
            for field in fields:
                answer = Answer.objects.filter(question=field, s_report=report).first()
                points = answer.points if answer else 0
                zone = answer.zone if answer else 'W'
                row.append(points)

                section_total += points
            if section_total < section.yellow_zone_min:
                section_zone = red_format
            elif section_total >= section.green_zone_min:
                section_zone = green_format
            elif section_total >= section.yellow_zone_min:
                section_zone = yellow_format
            
            row[3] = section_total

            for col, value in enumerate(row):
                if col < 3:  # School info and total columns
                    worksheet.write(row_num, col, value, cell_format)
                elif col == 3:
                    worksheet.write(row_num, col, section_total, section_zone)
                else:  # Field points columns
                    field = fields[col-4]
                    answer = Answer.objects.filter(question=field, s_report=report).first()
                    zone = answer.zone if answer else 'W'
                    format_to_use = {
                        'R': red_format,
                        'Y': yellow_format,
                        'G': green_format,
                        'W': cell_format
                    }[zone]

                    worksheet.write(row_num, col, value, format_to_use)

            worksheet.set_row(row_num, len(school.name) * 1)
            row_num += 1

        # Write totals for this section
        total = ['Итого', '', '', 0]
        total_sum = 0
        for field in fields:
            field_total = Answer.objects.filter(question=field, s_report__in=s_reports).aggregate(Sum('points'))['points__sum'] or 0
            total.append(field_total)
            total_sum += field_total
        total[3] = total_sum

        # Add count of schools in green zone
        worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в зелёной зоне', header_format)
        green_schools_count = len([r for r in s_reports if count_points(r)[0] == 'G'])
        green_schools = f"{green_schools_count} ({(green_schools_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, 3, green_schools, green_format)
        # Add count of schools in green zone for each field
        for col, field in enumerate(fields, start=4):
            green_field_count = len([r for r in s_reports if Answer.objects.filter(question=field, s_report=r).first() and Answer.objects.filter(question=field, s_report=r).first().zone == 'G'])
            green_field_schools = f"{green_field_count} ({(green_field_count/len(s_reports))*100:.1f}%)"
            worksheet.write(row_num, col, green_field_schools, green_format)
        row_num += 1

        # Add count of schools in yellow zone
        worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в жёлтой зоне', header_format)
        yellow_schools_count = len([r for r in s_reports if count_points(r)[0] == 'Y'])
        yellow_schools = f"{yellow_schools_count} ({(yellow_schools_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, 3, yellow_schools, yellow_format)
        # Add count of schools in yellow zone for each field
        for col, field in enumerate(fields, start=4):
            yellow_field_count = len([r for r in s_reports if Answer.objects.filter(question=field, s_report=r).first() and Answer.objects.filter(question=field, s_report=r).first().zone == 'Y'])
            yellow_field_schools = f"{yellow_field_count} ({(yellow_field_count/len(s_reports))*100:.1f}%)"
            worksheet.write(row_num, col, yellow_field_schools, yellow_format)
        row_num += 1

        # Add count of schools in red zone
        worksheet.merge_range(row_num, 0, row_num, 2, 'Кол-во школ в красной зоне', header_format)
        red_schools_count = len([r for r in s_reports if count_points(r)[0] == 'R'])
        red_schools = f"{red_schools_count} ({(red_schools_count/len(s_reports))*100:.1f}%)"
        worksheet.write(row_num, 3, red_schools, red_format)
        # Add count of schools in red zone for each field
        for col, field in enumerate(fields, start=4):
            red_field_count = len([r for r in s_reports if Answer.objects.filter(question=field, s_report=r).first() and Answer.objects.filter(question=field, s_report=r).first().zone == 'R'])
            red_field_schools = f"{red_field_count} ({(red_field_count/len(s_reports))*100:.1f}%)"
            worksheet.write(row_num, col, red_field_schools, red_format)
        
        row_num += 2

    # Close workbook and prepare response
    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="ter_admins_report_{year}.xlsx"'

    return response