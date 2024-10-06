from decimal import Decimal
import matplotlib.pyplot as plt
import io
import base64
from textwrap import fill
from django.utils.html import mark_safe
from django.db.models import Sum

from reports.models import Answer, Report, SchoolReport, Section
from reports.utils import count_section_points


# Function to generate chart for school report
def generate_school_report_chart(data, categories):
    plt.figure(figsize=(12, 5))  # Adjust figure size
    x = range(len(categories))
    width = 0.5 / len(data)  # Adjust width based on the number of years

    # Plot bars for each year
    for i, (year, values) in enumerate(data.items()):
        plt.bar([j + i * width for j in x], values, width=width, label=str(year), align='center', color='#a61849' if i % 2 == 0 else '#ffc600')
    
    # Wrap the category labels to prevent overlap
    wrapped_categories = [fill((f'{label.number }. { label.name }'), width=30) for label in categories]
    plt.xticks([i + (len(data) / 2 - 0.5) * width for i in x], wrapped_categories, ha='center', fontsize=10, fontweight='300')
    plt.ylabel('Баллы', fontsize=12, fontweight='300')
    plt.legend(fontsize=10, loc='upper right', frameon=True, fancybox=True, shadow=True)
    plt.tight_layout()
    
    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_png = buf.getvalue()
    buf.close()

    # Encode the image to base64 to use it in an HTML context
    image_base64 = base64.b64encode(image_png).decode('utf-8')
    return mark_safe(f'<img src="data:image/png;base64,{image_base64}"/>')

def calculate_stats_and_section_data(f_years, reports, sections, s_reports):
    stats = {}
    section_data = {}
    for year in f_years:
        stats[year] = {
            'green_zone': SchoolReport.objects.filter(zone='G', report__year=year).count(),
            'yellow_zone': SchoolReport.objects.filter(zone='Y', report__year=year).count(),
            'red_zone': SchoolReport.objects.filter(zone='R', report__year=year).count(),
        }
        section_data[year] = []
        for section in sections:
            section_obj = Section.objects.filter(name=section.name, report__in=reports, report__year=year)
            
            section_data[year].append(
                Answer.objects.filter(question__sections__in=section_obj, s_report__report__year=year).aggregate(points_sum=Sum('points'))['points_sum'] or Decimal(0)
            )
            stats[year][section.name] = {
                'green_zone': 0,
                'yellow_zone': 0,
                'red_zone': 0,
            }
            s_reports_year = s_reports.filter(report__year=year)
            for s_report in s_reports_year:
                color = count_section_points(s_report, section)
                if color == 'G':
                    stats[year][section.name]['green_zone'] += 1
                elif color == 'Y':
                    stats[year][section.name]['yellow_zone'] += 1
                elif color == 'R':
                    stats[year][section.name]['red_zone'] += 1
    return stats, section_data

def calculate_stats(year, s_reports):
    stats = {}
    reports = Report.objects.filter(schools__in=s_reports).distinct()
    sections = Section.objects.filter(report__year=year, report__in=reports)
    overall_stats = {}
    overall_stats['green_zone'] = [0, "0.0%"]
    overall_stats['yellow_zone'] = [0, "0.0%"]
    overall_stats['red_zone'] = [0, "0.0%"]
    for section in sections:
        stats[section.name] = {
            'green_zone': [0, "0.0%"],
            'yellow_zone': [0, "0.0%"],
            'red_zone': [0, "0.0%"],
        }
        s_reports_year = s_reports.filter(report__year=year)
        for s_report in s_reports_year:
            color = count_section_points(s_report, section)
            if color == 'G':
                stats[section.name]['green_zone'][0] += 1
                stats[section.name]['green_zone'][1] = f'{stats[section.name]['green_zone'][0] / s_reports_year.count() * 100:.1f}%'
            elif color == 'Y':
                stats[section.name]['yellow_zone'][0] += 1
                stats[section.name]['yellow_zone'][1] = f'{stats[section.name]['yellow_zone'][0] / s_reports_year.count() * 100:.1f}%'
            elif color == 'R':
                stats[section.name]['red_zone'][0] += 1
                stats[section.name]['red_zone'][1] = f'{stats[section.name]['red_zone'][0] / s_reports_year.count() * 100:.1f}%'
    overall_stats['green_zone'][0] = sum([stats[section.name]['green_zone'][0] for section in sections])
    overall_stats['yellow_zone'][0] = sum([stats[section.name]['yellow_zone'][0] for section in sections])
    overall_stats['red_zone'][0] = sum([stats[section.name]['red_zone'][0] for section in sections])    
    return stats, overall_stats