from decimal import Decimal
import matplotlib.pyplot as plt
import io
import base64
from textwrap import fill
from django.utils.html import mark_safe
from django.db.models import Sum

from reports.models import Answer, Report, SchoolReport, Section, SectionSreport, Field
from reports.utils import count_points, count_points_field


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

def calculate_stats(year, s_reports_year, sections):
    stats = {}
    # Initialize stats
    overall_stats = {
        "green_zone": [0, "0.0%"],
        "yellow_zone": [0, "0.0%"], 
        "red_zone": [0, "0.0%"]
    }

    # Prefetch related data in a single query

    s_reports_count = s_reports_year.count()

    # Create lookup dict for section stats
    for section in sections:
        stats[section.number] = {
            "green_zone": [0, "0.0%"],
            "yellow_zone": [0, "0.0%"],
            "red_zone": [0, "0.0%"]
        }

    # Calculate all stats in a single pass through the data
    for s_report in s_reports_year:
        # Overall stats
        if s_report.zone in ["G", "Y", "R"]:
            zone = {"G": "green_zone", "Y": "yellow_zone", "R": "red_zone"}[s_report.zone]
            overall_stats[zone][0] += 1

        # Section stats
        for section_sreport in s_report.sections.all():
            try:
                if section_sreport.zone in ["G", "Y", "R"]:
                    zone = {"G": "green_zone", "Y": "yellow_zone", "R": "red_zone"}[section_sreport.zone]
                    stats[section_sreport.section.number][zone][0] += 1
            except:
                breakpoint()

    # Calculate all percentages
    if s_reports_count > 0:
        # Overall percentages
        for zone in ["green_zone", "yellow_zone", "red_zone"]:
            overall_stats[zone][1] = f'{overall_stats[zone][0] / s_reports_count * 100:.1f}%'
            
        # Section percentages
        for section_stats in stats.values():
            for zone in ["green_zone", "yellow_zone", "red_zone"]:
                section_stats[zone][1] = f'{section_stats[zone][0] / s_reports_count * 100:.1f}%'

    return stats, overall_stats

def generate_ter_admins_report_csv(year, schools, s_reports):
    import xlsxwriter
    from django.http import HttpResponse
    from django.db.models import Sum
    from reports.models import Section, Field, Answer
    from io import BytesIO

    # Create workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Define formats
    formats = {
        'header': workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1
        }),
        'cell': workbook.add_format({
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1
        }),
        'red': workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            'border': 1, 'bg_color': '#FFC7CE'
        }),
        'yellow': workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            'border': 1, 'bg_color': '#FFEB9C'
        }),
        'green': workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            'border': 1, 'bg_color': '#C6EFCE'
        })
    }

    # Write headers
    header = ['ТУ/ДО', 'Уровень образования', 'Школа', 'Итого баллов']
    sections = Section.objects.filter(report__year=year).distinct('number').order_by('number')
    
    for section in sections:
        header.append(f"{section.number}. {section.name}")

    # Write header row and set column widths
    for col, value in enumerate(header):
        worksheet.write(0, col, value, formats['header'])
        width = min(max(len(value) * 1.1, 20), 50)
        worksheet.set_column(col, col, width)

    # Add zone headers
    zone_headers = [
        ('Кол-во/доля критериев школы в зелёной зоне', ['Количество', 'Доля']),
        ('Кол-во/доля критериев школы в жёлтой зоне', ['Количество', 'Доля']), 
        ('Кол-во/доля критериев школы в красной зоне', ['Количество', 'Доля'])
    ]

    col = len(header)
    for title, columns in zone_headers:
        worksheet.merge_range(0, col, 0, col + 1, title, formats['header'])
        header.extend(columns)
        col += 2

    # Set row height
    max_text_len = max(len(str(cell)) for cell in header)
    num_lines = (max_text_len / 15) + 1
    worksheet.set_row(0, num_lines * 15)

    # Write data rows
    row_num = 1
    for school in schools:
        school_reports = s_reports.filter(school=school, report__year=year)
        if not school_reports.exists():
            continue

        for report in school_reports:
            # Basic school info
            row = [
                str(school.ter_admin),
                school.get_ed_level_display(),
                school.__str__(),
                report.points
            ]

            # Add section points
            section_points = []
            for section in sections:
                sections_objs = Section.objects.filter(name=section.name)
                fields = Field.objects.filter(sections__in=sections_objs).distinct('number').prefetch_related('answers')
                points = Answer.objects.filter(
                    question__in=fields, 
                    s_report=report
                ).aggregate(Sum('points'))['points__sum'] or 0
                section_points.append(points)
                row.append(points)

            # Write row data with appropriate formatting
            for col, value in enumerate(row):
                format_key = 'cell'
                if col == 3:
                    format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(report.zone, 'cell')
                elif col >= 4:
                    section = sections[col-4]
                    zone = count_section_points(report, section)
                    format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(zone, 'cell')
                
                worksheet.write(row_num, col, value, formats[format_key])

            # Calculate and write zone statistics
            answers = Answer.objects.filter(s_report=report)
            total = answers.count()
            zone_counts = {
                'G': answers.filter(zone='G').count(),
                'Y': answers.filter(zone='Y').count(),
                'R': answers.filter(zone='R').count()
            }

            col = len(header) - 6
            for zone, count in zone_counts.items():
                pct = f"{(count/total)*100:.1f}%" if total else "0.0%"
                format_key = {'G': 'green', 'Y': 'yellow', 'R': 'red'}[zone]
                worksheet.write(row_num, col, count, formats[format_key])
                worksheet.write(row_num, col + 1, pct, formats[format_key])
                col += 2

            worksheet.set_row(row_num, len(school.__str__()))
            row_num += 1

    # Write summary rows
    write_summary_rows(worksheet, row_num, s_reports, sections, formats)

    # Write detailed section analysis
    write_section_details(worksheet, row_num + 2, sections, s_reports, formats)

    # Generate response
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="ter_admins_report_{year}.xlsx"'
    
    return response

def write_section_details(worksheet, row_num, sections, s_reports, formats):
    for section in sections:
        # Write section header
        worksheet.write(row_num, 0, f'Раздел {section.number}. {section.name}', formats['header'])
        row_num += 1

        # Write field headers
        headers = ['ТУ/ДО', 'Уровень образования', 'Школа', 'Всего баллов']
        sections_objs = Section.objects.filter(name=section.name)
        fields = Field.objects.filter(sections__in=sections_objs).distinct('number').prefetch_related('answers')
        fields = sorted(fields, key=lambda x: [int(n) for n in str(x.number).split('.')])
        for field in fields:
            headers.append(f'{field.number}. {field.name}')

        for col, header in enumerate(headers):
            worksheet.write(row_num, col, header, formats['header'])
        row_num += 1

        # Write school data for each field
        for s_report in s_reports:
            school = s_report.school
            row = [
                str(school.ter_admin),
                school.get_ed_level_display(),
                school.__str__(),
                s_report.points
            ]
            
            for field in fields:
                answer = Answer.objects.filter(question=field, s_report=s_report).first()
                points = answer.points if answer else "-"
                zone = answer.zone if answer else 'W'
                format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(zone, 'cell')
                row.append(points)
                worksheet.write(row_num, len(row)-1, points, formats[format_key])
            
            for col in range(4):
                worksheet.write(row_num, col, row[col], formats['cell'])
            row_num += 1
        
        row_num += 1

    return row_num

def write_summary_rows(worksheet, row_num, s_reports, sections, formats):
    # Write totals row
    total_row = ['Итого', '', '', 0]
    total_sum = 0
    
    for section in sections:
        sections_objs = Section.objects.filter(name=section.name)
        fields = Field.objects.filter(sections__in=sections_objs).distinct('number').prefetch_related('answers')
        fields = sorted(fields, key=lambda x: [int(n) for n in str(x.number).split('.')])
        section_total = Answer.objects.filter(
            question__in=fields, 
            s_report__in=s_reports
        ).aggregate(Sum('points'))['points__sum'] or 0
        total_row.append(section_total)
        total_sum += section_total
    
    total_row[3] = total_sum
    
    for col, value in enumerate(total_row):
        worksheet.write(row_num, col, value, formats['header'])
    
    return row_num + 1


def count_section_points(s_report, section):
    from reports.models import Answer
    try:
        section_obj = Section.objects.filter(number=section.number, report=s_report.report).first()
        points__sum = Answer.objects.filter(question__in=section_obj.fields.all(), s_report=s_report).aggregate(Sum('points'))['points__sum']
        if points__sum < section_obj.yellow_zone_min:
            return "R"
        elif points__sum >= section_obj.green_zone_min:
            return "G"
        return "Y"
    except:
        return "R"

