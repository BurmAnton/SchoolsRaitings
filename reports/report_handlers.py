import json
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache

from reports.models import Answer, Field, Option, OptionCombination, ReportFile, ReportLink, Section, Report
from reports.utils import count_points, select_range_option, count_section_points
from schools.models import School
from common.utils import get_cache_key


def process_answer_by_type(answer, question, data):
    """
    Универсальная функция для обработки ответов разных типов
    """
    if question.answer_type == "LST":
        try:
            option = Option.objects.get(id=data['value'])
            answer.option = option
            answer.points = option.points
            answer.zone = option.zone
        except:
            answer.option = None
            answer.points = 0
            answer.zone = "R"
    elif question.answer_type == "BL":
        answer.bool_value = data['value']
        answer.points = question.bool_points if answer.bool_value else 0
        answer.zone = "G" if answer.bool_value else "R"
    elif question.answer_type in ['NMBR', 'PRC']:
        answer.number_value = float(data['value'])
        r_option = select_range_option(question.range_options.all(), answer.number_value)
        if r_option == None: 
            answer.points = 0
            answer.zone = "R"
        else: 
            answer.points = r_option.points
            answer.zone = r_option.zone
    elif question.answer_type == 'MULT':
        # Обработка множественного выбора
        if 'multiple_values' in data:
            # Очищаем предыдущие выбранные опции
            answer.selected_options.clear()
            selected_options_ids = data['multiple_values']
            
            if selected_options_ids:
                # Получаем объекты Option по их ID
                selected_options = list(Option.objects.filter(id__in=selected_options_ids))
                
                # Добавляем выбранные опции
                answer.selected_options.add(*selected_options)
                
                # Сортируем номера опций для проверки комбинаций
                option_numbers = sorted([str(opt.number) for opt in selected_options])
                option_numbers_str = ','.join(option_numbers)
                
                # Проверяем, есть ли точное совпадение с комбинацией
                try:
                    combination = OptionCombination.objects.get(
                        field=question, 
                        option_numbers=option_numbers_str
                    )
                    answer.points = combination.points
                except OptionCombination.DoesNotExist:
                    # Если нет точного совпадения, суммируем баллы выбранных опций
                    total_points = sum(opt.points for opt in selected_options)
                    
                    # Проверяем, не превышает ли сумма максимальное значение (если оно задано)
                    if question.max_points is not None and total_points > question.max_points:
                        total_points = question.max_points
                        
                    answer.points = total_points
                
                # Определяем зону на основе баллов и настроек показателя
                field = question
                if field.yellow_zone_min is not None and field.green_zone_min is not None:
                    if answer.points < field.yellow_zone_min:
                        answer.zone = 'R'
                    elif answer.points >= field.green_zone_min:
                        answer.zone = 'G'
                    else:
                        answer.zone = 'Y'
                else:
                    # Если в показателе не заданы зоны, попробуем использовать зоны из раздела
                    section = field.sections.first()
                    if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                        if answer.points < section.yellow_zone_min:
                            answer.zone = 'R'
                        elif answer.points >= section.green_zone_min:
                            answer.zone = 'G'
                        else:
                            answer.zone = 'Y'
                    else:
                        # Если нигде не заданы зоны, то определяем по наличию баллов
                        answer.zone = 'G' if answer.points > 0 else 'R'
            else:
                # Если ничего не выбрано, обнуляем баллы
                answer.points = 0
                answer.zone = 'R'
    
    return answer


def handle_file_upload(request, question, s_report):
    """
    Обработка загрузки файлов
    """
    file = request.FILES.get("file")
    answers = Answer.objects.filter(question=question, s_report=s_report)
    if answers.count() == 0:
        answer = Answer.objects.create(
            s_report=s_report,
            question=question,
        )
    elif answers.count() == 1:
        answer = answers.first()
    else:
        answer = answers.first()
        answers.exclude(id=answer.id).delete()

    # Проверка разрешения на редактирование (для ТУ/ДО)
    if hasattr(request.user, 'ter_admin') and answer.is_checked:
        if answer.checked_by != request.user and not request.user.is_superuser:
            return JsonResponse({
                "error": f"Поле проверено пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}. Загрузка файлов запрещена."
            }, status=403)

    file = ReportFile.objects.create(
        s_report=answer.s_report,
        answer=answer,
        file=file
    )
    return JsonResponse({
        "message": "File updated/saved successfully.",
        "question_id": question.id,
        "file_link": file.file.url,
        "filename": file.file.name,
        "file_id": file.id
    }, status=201)


def handle_link_upload(request, data, question, s_report):
    """
    Обработка добавления ссылок
    """
    link = data['value']
    answers = Answer.objects.filter(question=question, s_report=s_report)
    if answers.count() == 0:
        answer = Answer.objects.create(
            s_report=s_report,
            question=question,
        )
    elif answers.count() == 1:
        answer = answers.first()
    else:
        answer = answers.first()
        answers.exclude(id=answer.id).delete()
        
    # Проверка разрешения на редактирование (для ТУ/ДО)
    if hasattr(request.user, 'ter_admin') and answer.is_checked:
        if answer.checked_by != request.user and not request.user.is_superuser:
            return JsonResponse({
                "error": f"Поле проверено пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}. Добавление ссылок запрещено."
            }, status=403)
        
    link = ReportLink.objects.create(
        s_report=answer.s_report,
        answer=answer,
        link=link,
    )
    link.save()
    return JsonResponse({
        "message": "Link updated/saved successfully.",
        "question_id": question.id,
        "link": link.link,
        "link_id": link.id
    }, status=201)


def clear_caches_for_report(school, s_report):
    """
    Очистка кешей при обновлении отчета
    """
    # Clear dashboard caches when answer is updated
    cache_key = get_cache_key('ter_admins_dash',
        year=s_report.report.year,
        schools=','.join(sorted(str(s.id) for s in School.objects.filter(ter_admin=school.ter_admin, is_archived=False))),
        reports=','.join(sorted(str(r.id) for r in Report.objects.filter(year=s_report.report.year)))
    )
    cache.delete(cache_key)
    
    # Clear closters_report cache
    cache_key = get_cache_key('closters_report_data',
        year=s_report.report.year,
        ter_admin=str(school.ter_admin.id),
        closters=str(school.closter.id) if school.closter else '',
        ed_levels=school.ed_level
    )
    cache.delete(cache_key)


def process_answer_update(request, data, s_report, user_type):
    """
    Основная функция обработки обновления ответов
    user_type: 'school', 'ter_admin', 'mo'
    """
    try:
        question = Field.objects.get(id=data['id'].replace('check_', ''))
    except Field.DoesNotExist:
        return JsonResponse({"error": "Поле не найдено"}, status=404)
        
    answers = Answer.objects.filter(question=question, s_report=s_report)
    if answers.count() == 0:
        answer = Answer.objects.create(
            s_report=s_report,
            question=question,
        )
    elif answers.count() == 1:
        answer = answers.first()
    else:
        answer = answers.first()
        answers.exclude(id=answer.id).delete()
    
    # Проверка разрешения на редактирование для ТУ/ДО
    if user_type == 'ter_admin' and answer.is_checked:
        # Если поле проверено другим пользователем, запрещаем редактирование
        if answer.checked_by != request.user and not request.user.is_superuser:
            return JsonResponse({
                "error": f"Поле проверено пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}. Редактирование запрещено."
            }, status=403)
    
    # Обработка ответа по типу
    answer = process_answer_by_type(answer, question, data)
    
    # Установка флагов модификации в зависимости от типа пользователя
    if user_type == 'mo':
        answer.is_mod_by_mo = True
    elif user_type == 'ter_admin':
        answer.is_mod_by_ter = True
    
    answer.save()

    # Проверка готовности отчета
    list_answers = Answer.objects.filter(s_report=s_report, question__answer_type='LST', option=None)
    s_report.is_ready = len(list_answers) == 0
    
    # Пересчет баллов и зон
    zone, points_sum = count_points(s_report)
    
    if zone != 'W':
        s_report.zone = zone
        a_zone = answer.zone
    else:
        a_zone = 'W'

    s_report.points = points_sum
    s_report.save()

    # Очистка кешей
    clear_caches_for_report(s_report.school, s_report)

    section = Section.objects.get(fields=question.id, report=s_report.report)

    return JsonResponse({
        "message": "Question changed successfully.", 
        "points": str(answer.points), 
        "ready": s_report.is_ready,
        "zone": zone, 
        "report_points": s_report.points,
        "answer_z": a_zone,
        "section_z": count_section_points(s_report, section),
    }, status=201)


def handle_ajax_request(request, s_report, user_type='school'):
    """
    Универсальная обработка AJAX запросов для всех типов отчетов
    user_type: 'school', 'ter_admin', 'mo'
    """
    data = json.loads(request.body.decode("utf-8"))
    
    # Обработка удаления файлов
    if 'file_id' in data:
        file_id = data['file_id']
        try:
            report_file = ReportFile.objects.get(id=file_id)
            answer = report_file.answer
            
            # Проверка разрешения на удаление (для ТУ/ДО)
            if user_type == 'ter_admin' and answer.is_checked:
                if answer.checked_by != request.user and not request.user.is_superuser:
                    return JsonResponse({
                        "error": f"Поле проверено пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}. Удаление файлов запрещено."
                    }, status=403)
            
            report_file.delete()
            return JsonResponse({"message": "File deleted successfully."}, status=201)
        except ReportFile.DoesNotExist:
            return JsonResponse({"error": "Файл не найден"}, status=404)
    
    # Обработка удаления ссылок
    elif 'link_id' in data:
        link_id = data['link_id']
        try:
            report_link = ReportLink.objects.get(id=link_id)
            answer = report_link.answer
            
            # Проверка разрешения на удаление (для ТУ/ДО)
            if user_type == 'ter_admin' and answer.is_checked:
                if answer.checked_by != request.user and not request.user.is_superuser:
                    return JsonResponse({
                        "error": f"Поле проверено пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}. Удаление ссылок запрещено."
                    }, status=403)
            
            report_link.delete()
            return JsonResponse({"message": "Link deleted successfully."}, status=201)
        except ReportLink.DoesNotExist:
            return JsonResponse({"error": "Ссылка не найдена"}, status=404)
    
    # Обработка проверки ответов (только для ter_admin)
    elif 'check_answer' in data and user_type == 'ter_admin':
        answer_id = data['answer_id']
        is_checked = data['is_checked']

        try:
            answer = Answer.objects.get(id=answer_id)
            
            # Проверка доступа к снятию галочки
            if not is_checked and answer.is_checked:
                # Разрешаем снятие галочки только тому, кто её поставил, или админу
                if answer.checked_by != request.user and not request.user.is_superuser:
                    return JsonResponse({
                        "error": f"Снятие галочки проверки запрещено. Критерий был проверен пользователем {answer.checked_by.get_full_name() if answer.checked_by else 'Неизвестно'}."
                    }, status=403)
            
            answer.is_checked = is_checked
            if is_checked:
                answer.checked_by = request.user
                answer.checked_at = timezone.now()
            else:
                answer.checked_by = None
                answer.checked_at = None
            answer.save()
            return JsonResponse({
                "message": "Answer check status updated successfully.",
                "checked_by": answer.checked_by.get_full_name() if answer.checked_by else None,
                "checked_at": answer.checked_at.strftime("%d.%m.%Y %H:%M") if answer.checked_at else None
            }, status=201)
        except Answer.DoesNotExist:
            return JsonResponse({"error": "Ответ не найден"}, status=404)
    
    # Обработка добавления ссылок
    elif 'link' in data:
        try:
            question = Field.objects.get(id=data['id'])
        except Field.DoesNotExist:
            return JsonResponse({"error": "Поле не найдено"}, status=404)
        return handle_link_upload(request, data, question, s_report)
    
    # Обработка обновления ответов
    else:
        return process_answer_update(request, data, s_report, user_type)


def get_report_context(request, s_report, current_section, message=None, **extra_context):
    """
    Получение общего контекста для отчетов
    """
    answers = Answer.objects.filter(s_report=s_report)
    is_readonly = s_report.report.year.status == 'completed'
    
    if is_readonly and not message:
        message = "ReadOnly"
    
    if current_section == "":
        current_section = s_report.report.sections.all().first().id
    else:
        current_section = int(current_section)
    
    context = {
        'school': s_report.school,
        'report': s_report.report,
        'current_section': current_section,
        'message': message,
        's_report': s_report,
        'answers': answers,
        'is_readonly': is_readonly,
    }
    context.update(extra_context)
    return context


def handle_send_report(s_report, target_status):
    """
    Обработка отправки отчета с указанием целевого статуса
    """
    s_report.status = target_status
    s_report.save()
    
    status_messages = {
        'A': "SendToTerAdmin",
        'B': "SendToMinObr",
    }
    return status_messages.get(target_status, "ReportSent") 