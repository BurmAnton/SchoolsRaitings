jQuery(document).ready(function ($) {
    (function ($) {
        $(function () {
            
            $('.tox-tinymce').css('height', '200px');
            var answer_type = $('#id_answer_type'),
                options = $('#options-group'),
                range_options = $('#range_options-group'),
                combinations = $('#optioncombination_set-group'),
                bool_points = $('.field-bool_points'),
                max_points = $('.field-max_points');

            function toggleVerified(value) {
                console.log(value)
                if (value === 'BL') {
                    bool_points.show();
                    options.hide();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'LST') {
                    bool_points.hide();
                    options.show();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'PRC') {
                    bool_points.hide();
                    options.hide();
                    range_options.show();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'NMBR') {
                    bool_points.hide();
                    options.hide();
                    range_options.show();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'MULT') {
                    bool_points.hide();
                    options.show();
                    range_options.hide();
                    combinations.show();
                    max_points.show();
                } else {
                    bool_points.hide();
                    options.hide();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                }
            }

            // show/hide on load based on pervious value of selectField
            
            toggleVerified(answer_type.val());

            // show/hide on change
            answer_type.change(function () {
                console.log($(this))
                toggleVerified($(this).val());
            });

            // Функция для управления отображением inlines на основе типа ответа
            function toggleInlines() {
                var answerType = document.getElementById('id_answer_type');
                if (!answerType) return;

                var selectedValue = answerType.value;
                
                // Получаем контейнеры инлайн-форм
                var optionInline = document.querySelector('.option-inline-related');
                var rangeOptionInline = document.querySelector('.rangeoption-inline-related');
                var combinationInline = document.querySelector('.optioncombination-inline-related');
                
                // Скрываем все по умолчанию
                if (rangeOptionInline) rangeOptionInline.style.display = 'none';
                if (combinationInline) combinationInline.style.display = 'none';
                
                // Показываем нужные инлайны в зависимости от типа ответа
                if (selectedValue === 'LST' || selectedValue === 'MULT') {
                    if (optionInline) optionInline.style.display = 'block';
                    
                    // Только для множественного выбора показываем комбинации
                    if (combinationInline) {
                        combinationInline.style.display = selectedValue === 'MULT' ? 'block' : 'none';
                    }
                    
                    // Скрываем колонку "Зона" для множественного выбора
                    if (selectedValue === 'MULT') {
                        const zoneHeaders = document.querySelectorAll('.option-inline-related th:nth-child(4)');
                        const zoneCells = document.querySelectorAll('.option-inline-related td:nth-child(4)');
                        
                        zoneHeaders.forEach(header => {
                            header.style.display = 'none';
                        });
                        
                        zoneCells.forEach(cell => {
                            cell.style.display = 'none';
                        });
                    }
                } else if (selectedValue === 'NMBR' || selectedValue === 'PRC') {
                    if (rangeOptionInline) rangeOptionInline.style.display = 'block';
                    if (optionInline) optionInline.style.display = 'none';
                } else if (selectedValue === 'BL') {
                    if (optionInline) optionInline.style.display = 'none';
                }
            }
            
            // Вызываем функцию при загрузке страницы
            toggleInlines();
            
            // Добавляем обработчик события при изменении типа ответа
            var answerType = document.getElementById('id_answer_type');
            if (answerType) {
                answerType.addEventListener('change', toggleInlines);
            }
        });
    })(django.jQuery);
});