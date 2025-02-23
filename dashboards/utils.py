from decimal import Decimal
from django.db.models import Sum, Avg, Max
from common.utils import get_cache_key

from reports.models import Answer, Report, SchoolReport, Section, SectionSreport, Field
from reports.utils import count_points, count_points_field

def calculate_stats_and_section_data(f_years, reports, sections, s_reports):
    stats = {}
    section_data = {}
    
    # Get distinct sections by number
    distinct_sections = sections.distinct('number').order_by('number')
    
    for year in f_years:
        stats[year] = {
            "green_zone": SchoolReport.objects.filter(zone="G", report__year=year).count(),
            "yellow_zone": SchoolReport.objects.filter(zone="Y", report__year=year).count(),
            "red_zone": SchoolReport.objects.filter(zone="R", report__year=year).count(),
        }
        section_data[year] = []
        
        for section in distinct_sections:
            # Get all sections with the same number for this year
            year_sections = Section.objects.filter(
                number=section.number,
                report__in=reports,
                report__year=year
            )
            
            # Calculate points for all fields in these sections
            points_sum = Answer.objects.filter(
                question__sections__in=year_sections,
                s_report__report__year=year
            ).aggregate(points_sum=Sum("points"))["points_sum"] or Decimal(0)
            
            section_data[year].append(points_sum)
            
            # Initialize stats for this section
            stats[year][section.name] = {
                "green_zone": 0,
                "yellow_zone": 0,
                "red_zone": 0,
            }
            
            # Calculate zone stats
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
                continue

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

def generate_school_report_csv(year, school, s_reports, sections):
    import xlsxwriter
    from django.http import HttpResponse
    from io import BytesIO

    # Create workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
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
        }),
        'section_header': workbook.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1, 'bg_color': '#E7E6E6'
        })
    }

    # Create main worksheet
    worksheet = workbook.add_worksheet("Сводный отчет")

    # Write headers
    header = ['Год', 'ТУ/ДО', 'Уровень образования', 'Школа', 'Итого баллов']
    
    # Add section headers
    for section in sections:
        header.append(f"{section.number}. {section.name}")

    # Write header row and set column widths
    for col, value in enumerate(header):
        worksheet.write(0, col, value, formats['header'])
        width = min(max(len(value) * 1.1, 20), 50)
        worksheet.set_column(col, col, width)

    # Write summary data rows
    row_num = 1
    for s_report in s_reports:
        # Basic report info
        row = [
            s_report.report.year,
            str(school.ter_admin),
            school.get_ed_level_display(),
            school.__str__(),
            s_report.points
        ]

        # Add section points
        for section in sections:
            section_report = SectionSreport.objects.filter(
                s_report=s_report,
                section__number=section.number
            ).first()
            points = section_report.points if section_report else 0
            row.append(points)

        # Write row data with appropriate formatting
        for col, value in enumerate(row):
            format_key = 'cell'
            if col == 4:  # Total points column
                format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(s_report.zone, 'cell')
            elif col >= 5:  # Section columns
                section = sections[col-5]
                section_report = SectionSreport.objects.filter(
                    s_report=s_report,
                    section__number=section.number
                ).first()
                if section_report:
                    format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(section_report.zone, 'cell')
            
            worksheet.write(row_num, col, value, formats[format_key])

        row_num += 1

    # Create detailed worksheets for each section
    for section in sections:
        worksheet = workbook.add_worksheet(f"Раздел {section.number}")
        
        # Write section header
        worksheet.merge_range(0, 0, 0, 4, f"{section.number}. {section.name}", formats['section_header'])
        
        # Write column headers
        headers = ['Год', 'ТУ/ДО', 'Школа', 'Показатель', 'Баллы']
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, formats['header'])
            worksheet.set_column(col, col, 20)
        
        row_num = 2
        for s_report in s_reports:
            # Get all fields (questions) for this section
            fields = Field.objects.filter(sections=section).distinct('number').order_by('number')
            
            for field in fields:
                answer = Answer.objects.filter(
                    question=field,
                    s_report=s_report
                ).first()
                
                row = [
                    s_report.report.year,
                    str(school.ter_admin),
                    school.__str__(),
                    f"{section.number}.{field.number}. {field.name}",
                    answer.points if answer else 0
                ]
                
                # Write row with appropriate formatting
                format_key = 'cell'
                if answer:
                    format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(answer.zone, 'cell')
                
                for col, value in enumerate(row):
                    worksheet.write(row_num, col, value, formats['cell' if col < 4 else format_key])
                
                row_num += 1
            
            # Add a blank row between years
            row_num += 1

    # Close workbook
    workbook.close()
    output.seek(0)
    
    # Generate response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="school_report_{school.id}_{year}.xlsx"'
    
    return response

def generate_closters_report_csv(year, schools, s_reports):
    import xlsxwriter
    from django.http import HttpResponse
    from io import BytesIO

    # Create workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
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
        }),
        'section_header': workbook.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1, 'bg_color': '#E7E6E6'
        })
    }

    # Create summary worksheet
    worksheet = workbook.add_worksheet("Итоговые баллы")

    # Write school info headers for summary
    headers = ['Показатель', 'Максимум', 'Среднее']
    for s_report in s_reports:
        school = s_report.school
        headers.append(f"{school.ter_admin} - {school}")

    # Write headers and set column widths
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, formats['header'])
        width = min(max(len(header) * 1.2, 15), 40)
        worksheet.set_column(col, col, width)

    # Get sections
    sections = Section.objects.filter(report__year=year).distinct('number').order_by('number')
    
    # Write data for each section in summary
    row_num = 1
    for section in sections:
        # Write section name
        worksheet.write(row_num, 0, f"{section.number}. {section.name}", formats['section_header'])
        
        # Calculate max and average for section
        section_stats = SectionSreport.objects.filter(
            s_report__in=s_reports,
            section__number=section.number
        ).aggregate(
            max_points=Max('points'),
            avg_points=Avg('points')
        )
        
        # Write max and average
        worksheet.write(row_num, 1, section_stats['max_points'] or 0, formats['cell'])
        worksheet.write(row_num, 2, round(section_stats['avg_points'] or 0, 1), formats['cell'])
        
        # Write points for each school
        for col, s_report in enumerate(s_reports, 3):
            section_report = SectionSreport.objects.filter(
                s_report=s_report,
                section__number=section.number
            ).first()
            points = section_report.points if section_report else 0
            format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(
                section_report.zone if section_report else '', 'cell'
            )
            
            worksheet.write(row_num, col, points, formats[format_key])
        
        row_num += 1

    # Create worksheet for each section
    for section in sections:
        worksheet = workbook.add_worksheet(f"Раздел {section.number}")
        
        # Write headers for section worksheet
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, formats['header'])
            worksheet.set_column(col, col, width)

        row_num = 1
        
        # Write section total row
        worksheet.write(row_num, 0, f"{section.number}. {section.name}", formats['section_header'])
        
        # Calculate and write section totals
        section_stats = SectionSreport.objects.filter(
            s_report__in=s_reports,
            section__number=section.number
        ).aggregate(
            max_points=Max('points'),
            avg_points=Avg('points')
        )
        
        worksheet.write(row_num, 1, section_stats['max_points'] or 0, formats['cell'])
        worksheet.write(row_num, 2, round(section_stats['avg_points'] or 0, 1), formats['cell'])
        
        for col, s_report in enumerate(s_reports, 3):
            section_report = SectionSreport.objects.filter(
                s_report=s_report,
                section__number=section.number
            ).first()
            
            points = section_report.points if section_report else 0
            format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(
                section_report.zone if section_report else '', 'cell'
            )
            
            worksheet.write(row_num, col, points, formats[format_key])
        
        row_num += 2  # Add blank row after section total

        # Write field data
        fields = Field.objects.filter(sections=section).distinct('number').order_by('number')
        for field in fields:
            worksheet.write(row_num, 0, f"{section.number}.{field.number}. {field.name}", formats['cell'])
            
            # Calculate max and average for field
            field_stats = Answer.objects.filter(
                question=field,
                s_report__in=s_reports
            ).aggregate(
                max_points=Max('points'),
                avg_points=Avg('points')
            )
            
            # Write max and average
            worksheet.write(row_num, 1, field_stats['max_points'] or 0, formats['cell'])
            worksheet.write(row_num, 2, round(field_stats['avg_points'] or 0, 1), formats['cell'])
            
            # Write points for each school
            for col, s_report in enumerate(s_reports, 3):
                answer = Answer.objects.filter(
                    question=field,
                    s_report=s_report
                ).first()
                
                points = answer.points if answer else 0
                format_key = {'R': 'red', 'Y': 'yellow', 'G': 'green'}.get(
                    answer.zone if answer else '', 'cell'
                )
                
                worksheet.write(row_num, col, points, formats[format_key])
            
            row_num += 1

    # Close workbook
    workbook.close()
    output.seek(0)
    
    # Generate response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="closters_report_{year}.xlsx"'
    
    return response

