document.addEventListener('DOMContentLoaded', function() {
    console.log(document.querySelector('.active'))
    try {
        document.querySelector('.active').classList.remove('active')
        document.querySelector('.dashboard-link').classList.add('active')
    } catch (error) {
    }

    const terAdminSelect = document.getElementById('TerAdminFilter');
    const schoolSelect = document.getElementById('SchoolFilter');

    if (terAdminSelect && schoolSelect) {
        terAdminSelect.addEventListener('change', function() {
            const selectedTerAdminId = this.value;
            
            // Показываем индикатор загрузки
            $(schoolSelect).prop('disabled', true);
            $(schoolSelect).selectpicker('refresh');
            
            // Формируем URL для AJAX запроса
            const ajaxUrl = '/dashboards/ajax/schools-by-ter-admin/';
            
            // Выполняем AJAX запрос
            fetch(ajaxUrl + '?ter_admin_id=' + encodeURIComponent(selectedTerAdminId), {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Очищаем текущие опции школ
                    $(schoolSelect).empty();
                    
                    // Добавляем опцию "Выберите школу"
                    $(schoolSelect).append('<option value="">Выберите школу</option>');
                    
                    // Добавляем школы
                    data.schools.forEach(function(school) {
                        $(schoolSelect).append(
                            '<option value="' + school.id + '">' + school.name + '</option>'
                        );
                    });
                    
                    // Включаем select обратно и обновляем
                    $(schoolSelect).prop('disabled', false);
                    $(schoolSelect).selectpicker('refresh');
                    
                } else {
                    console.error('Ошибка загрузки школ:', data.message);
                    
                    // В случае ошибки используем старый способ фильтрации
                    fallbackFilterSchools(selectedTerAdminId);
                }
            })
            .catch(error => {
                console.error('Ошибка AJAX запроса:', error);
                
                // В случае ошибки используем старый способ фильтрации
                fallbackFilterSchools(selectedTerAdminId);
            });
        });
    }
    
    // Функция для фильтрации школ без AJAX (запасной вариант)
    function fallbackFilterSchools(selectedTerAdminId) {
        // Если ничего не выбрано, показываем все школы
        if (!selectedTerAdminId) {
            $(schoolSelect).find('option').each(function() {
                $(this).prop('hidden', false).prop('disabled', false);
            });
        } else {
            // Фильтруем школы по выбранному ТУ/ДО
            $(schoolSelect).find('option').each(function() {
                const $option = $(this);
                const terAdminId = $option.attr('data-ter-admin-id');
                
                if (terAdminId && terAdminId !== selectedTerAdminId) {
                    $option.prop('hidden', true).prop('disabled', true);
                } else {
                    $option.prop('hidden', false).prop('disabled', false);
                }
            });
        }

        // Сбросить выбор
        schoolSelect.value = '';
        
        // Включаем select обратно и обновляем Bootstrap Selectpicker
        $(schoolSelect).prop('disabled', false);
        $(schoolSelect).selectpicker('refresh');
        
        // Сбросить заголовок до начального состояния
        $(schoolSelect).selectpicker('val', '');
    }
})