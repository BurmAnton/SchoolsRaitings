import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import Mock, patch

from reports.models import Answer, Field, Option, Report, SchoolReport, Section
from reports.report_handlers import (
    process_answer_by_type,
    handle_ajax_request,
    get_report_context,
    handle_send_report,
    clear_caches_for_report
)
from schools.models import School, TerAdmin, SchoolCloster
from users.models import Group


class ReportHandlersTestCase(TestCase):
    """
    Тесты для консолидированных функций обработки отчетов
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # Создаем группу для школ
        self.school_group = Group.objects.create(name='Представитель школы')
        self.user.groups.add(self.school_group)
        
        # Создаем ТУ/ДО
        self.ter_admin = TerAdmin.objects.create(name='Test TerAdmin')
        
        # Создаем кластер
        self.closter = SchoolCloster.objects.create(name='Test Closter')
        
        # Создаем школу
        self.school = School.objects.create(
            name='Test School',
            ter_admin=self.ter_admin,
            closter=self.closter,
            ed_level='primary'
        )
        self.user.school = self.school
        self.user.save()
        
        # Создаем отчет
        self.report = Report.objects.create(
            name='Test Report',
            closter=self.closter,
            ed_level='primary',
            is_published=True
        )
        
        # Создаем отчет школы
        self.s_report = SchoolReport.objects.create(
            report=self.report,
            school=self.school
        )
        
        # Создаем раздел
        self.section = Section.objects.create(
            name='Test Section',
            number=1,
            report=self.report
        )
        
        # Создаем поле (вопрос)
        self.field = Field.objects.create(
            name='Test Field',
            number=1,
            answer_type='LST'
        )
        self.field.sections.add(self.section)
        
        # Создаем опцию
        self.option = Option.objects.create(
            field=self.field,
            name='Test Option',
            points=10,
            zone='G'
        )
        
        # Создаем ответ
        self.answer = Answer.objects.create(
            s_report=self.s_report,
            question=self.field
        )
        
        self.client = Client()

    def test_process_answer_by_type_lst(self):
        """Тест обработки ответа типа LST"""
        data = {'value': str(self.option.id)}
        
        result = process_answer_by_type(self.answer, self.field, data)
        
        self.assertEqual(result.option, self.option)
        self.assertEqual(result.points, 10)
        self.assertEqual(result.zone, 'G')

    def test_process_answer_by_type_bl_true(self):
        """Тест обработки ответа типа BL (True)"""
        bool_field = Field.objects.create(
            name='Boolean Field',
            number=2,
            answer_type='BL',
            bool_points=5
        )
        bool_field.sections.add(self.section)
        
        bool_answer = Answer.objects.create(
            s_report=self.s_report,
            question=bool_field
        )
        
        data = {'value': True}
        
        result = process_answer_by_type(bool_answer, bool_field, data)
        
        self.assertEqual(result.bool_value, True)
        self.assertEqual(result.points, 5)
        self.assertEqual(result.zone, 'G')

    def test_process_answer_by_type_bl_false(self):
        """Тест обработки ответа типа BL (False)"""
        bool_field = Field.objects.create(
            name='Boolean Field',
            number=3,
            answer_type='BL',
            bool_points=5
        )
        bool_field.sections.add(self.section)
        
        bool_answer = Answer.objects.create(
            s_report=self.s_report,
            question=bool_field
        )
        
        data = {'value': False}
        
        result = process_answer_by_type(bool_answer, bool_field, data)
        
        self.assertEqual(result.bool_value, False)
        self.assertEqual(result.points, 0)
        self.assertEqual(result.zone, 'R')

    def test_get_report_context(self):
        """Тест формирования контекста отчета"""
        mock_request = Mock()
        current_section = ''
        message = 'Test message'
        
        context = get_report_context(
            mock_request, 
            self.s_report, 
            current_section, 
            message
        )
        
        self.assertEqual(context['school'], self.school)
        self.assertEqual(context['report'], self.s_report)
        self.assertEqual(context['message'], message)
        self.assertEqual(context['s_report'], self.s_report)
        self.assertIn('answers', context)
        self.assertIn('is_readonly', context)

    def test_handle_send_report(self):
        """Тест обработки отправки отчета"""
        result = handle_send_report(self.s_report, 'A')
        
        # Перезагружаем объект из БД
        self.s_report.refresh_from_db()
        
        self.assertEqual(self.s_report.status, 'A')
        self.assertEqual(result, 'SendToTerAdmin')

    @patch('reports.report_handlers.cache.delete')
    def test_clear_caches_for_report(self, mock_cache_delete):
        """Тест очистки кешей"""
        clear_caches_for_report(self.school, self.s_report)
        
        # Проверяем, что cache.delete был вызван
        self.assertTrue(mock_cache_delete.called)
        self.assertEqual(mock_cache_delete.call_count, 2)  # Два типа кешей


class ReportViewsIntegrationTestCase(TestCase):
    """
    Интеграционные тесты для рефакторенных view функций
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # Создаем группу для школ
        self.school_group = Group.objects.create(name='Представитель школы')
        self.user.groups.add(self.school_group)
        
        # Создаем ТУ/ДО
        self.ter_admin = TerAdmin.objects.create(name='Test TerAdmin')
        
        # Создаем кластер
        self.closter = SchoolCloster.objects.create(name='Test Closter')
        
        # Создаем школу
        self.school = School.objects.create(
            name='Test School',
            ter_admin=self.ter_admin,
            closter=self.closter,
            ed_level='primary'
        )
        self.user.school = self.school
        self.user.save()
        
        # Создаем отчет
        self.report = Report.objects.create(
            name='Test Report',
            closter=self.closter,
            ed_level='primary',
            is_published=True
        )
        
        # Создаем отчет школы
        self.s_report = SchoolReport.objects.create(
            report=self.report,
            school=self.school
        )
        
        self.client = Client()
        self.client.force_login(self.user)

    def test_report_view_get(self):
        """Тест GET запроса к view отчета"""
        url = reverse('report', args=[self.report.id, self.school.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test School')
        self.assertContains(response, 'Test Report')

    def test_mo_report_view_get(self):
        """Тест GET запроса к view отчета МинОбр"""
        url = reverse('mo_report', args=[self.s_report.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_ter_admin_report_view_get(self):
        """Тест GET запроса к view отчета ТУ/ДО"""
        url = reverse('ter_admin_report', args=[self.ter_admin.id, self.s_report.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class ReportHandlersPerformanceTestCase(TestCase):
    """
    Тесты производительности для проверки оптимизации
    """
    
    def setUp(self):
        """Настройка данных для тестов производительности"""
        # Создаем тестовые данные аналогично предыдущим тестам
        self.user = User.objects.create_user(username='perfuser', password='perfpass')
        self.school_group = Group.objects.create(name='Представитель школы')
        self.user.groups.add(self.school_group)
        
        self.ter_admin = TerAdmin.objects.create(name='Perf TerAdmin')
        self.closter = SchoolCloster.objects.create(name='Perf Closter')
        self.school = School.objects.create(
            name='Perf School',
            ter_admin=self.ter_admin,
            closter=self.closter,
            ed_level='primary'
        )
        self.user.school = self.school
        self.user.save()
        
        self.report = Report.objects.create(
            name='Perf Report',
            closter=self.closter,
            ed_level='primary',
            is_published=True
        )
        
        self.s_report = SchoolReport.objects.create(
            report=self.report,
            school=self.school
        )

    def test_context_generation_performance(self):
        """Тест производительности генерации контекста"""
        import time
        
        mock_request = Mock()
        
        start_time = time.time()
        for _ in range(100):
            context = get_report_context(mock_request, self.s_report, '', None)
        end_time = time.time()
        
        # Проверяем, что 100 вызовов выполняются менее чем за 1 секунду
        self.assertLess(end_time - start_time, 1.0) 