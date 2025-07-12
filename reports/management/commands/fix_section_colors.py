from django.core.management.base import BaseCommand
from django.db.models import Sum
from reports.models import SchoolReport, SectionSreport, Section, Answer
from reports.utils import count_section_points


class Command(BaseCommand):
    help = 'Fix missing or incorrect SectionSreport objects for all SchoolReports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--report-id',
            type=int,
            help='Fix specific SchoolReport by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        if options['report_id']:
            # Fix specific report
            try:
                s_report = SchoolReport.objects.get(id=options['report_id'])
                reports = [s_report]
                self.stdout.write(f"Fixing specific report: {s_report}")
            except SchoolReport.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"SchoolReport with ID {options['report_id']} not found")
                )
                return
        else:
            # Fix all reports
            reports = SchoolReport.objects.all().select_related('report', 'school')
            self.stdout.write(f"Fixing {reports.count()} school reports...")

        created_count = 0
        updated_count = 0
        errors_count = 0

        for s_report in reports:
            try:
                # Get all sections for this report
                sections = Section.objects.filter(report=s_report.report)
                
                for section in sections:
                    # Get or create SectionSreport
                    section_sreport, created = SectionSreport.objects.get_or_create(
                        s_report=s_report,
                        section=section,
                        defaults={
                            'points': 0,
                            'zone': 'R'
                        }
                    )
                    
                    # Calculate correct points and zone
                    section_points = Answer.objects.filter(
                        question__in=section.fields.all(),
                        s_report=s_report
                    ).aggregate(Sum('points'))['points__sum'] or 0
                    
                    # Calculate zone correctly, considering is_counting flag
                    if s_report.report.is_counting == False:
                        section_zone = 'W'  # White zone when counting is disabled
                    else:
                        try:
                            if section_points < section.yellow_zone_min:
                                section_zone = "R"
                            elif section_points >= section.green_zone_min:
                                section_zone = "G"
                            else:
                                section_zone = "Y"
                        except:
                            section_zone = 'R'
                    
                    # Check if update is needed
                    needs_update = (
                        section_sreport.points != section_points or
                        section_sreport.zone != section_zone
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            f"Created SectionSreport for {s_report.school} - {section.name}"
                        )
                    
                    if needs_update:
                        if not options['dry_run']:
                            section_sreport.points = section_points
                            section_sreport.zone = section_zone
                            section_sreport.save()
                        
                        updated_count += 1
                        self.stdout.write(
                            f"{'Would update' if options['dry_run'] else 'Updated'} "
                            f"{s_report.school} - {section.name}: "
                            f"points {section_sreport.points}->{section_points}, "
                            f"zone {section_sreport.zone}->{section_zone}"
                        )
                        
            except Exception as e:
                errors_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing {s_report.school} - {s_report.report}: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"- Created: {created_count} SectionSreport objects\n"
                f"- Updated: {updated_count} SectionSreport objects\n"
                f"- Errors: {errors_count} errors\n"
                f"{'DRY RUN - No changes were made' if options['dry_run'] else 'Changes applied successfully'}"
            )
        ) 