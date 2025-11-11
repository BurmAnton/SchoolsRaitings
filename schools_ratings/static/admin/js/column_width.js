/**
 * JavaScript для обеспечения интерактивной работы с настройками ширины столбцов
 */
(function($) {
    'use strict';

    $(document).ready(function() {
        // Применяем CSS-классы из data-атрибутов к ячейкам
        function applyColumnClasses() {
            // Применяем CSS-классы к заголовкам таблицы
            $('table.result_list thead tr th').each(function(index) {
                var fieldName = $(this).data('field-name');
                var cssClass = $(this).data('css-class');
                
                if (cssClass) {
                    $(this).addClass(cssClass);
                }
            });
            
            // Применяем CSS-классы к ячейкам таблицы
            $('table.result_list tbody tr').each(function() {
                var rowClassData = $(this).data('column-classes');
                
                if (rowClassData) {
                    var columnClasses = rowClassData.split(',');
                    
                    columnClasses.forEach(function(classInfo) {
                        var parts = classInfo.split(':');
                        if (parts.length === 2) {
                            var fieldName = parts[0];
                            var cssClass = parts[1];
                            var index = $('table.result_list thead th[data-field-name="' + fieldName + '"]').index();
                            
                            if (index >= 0) {
                                $(this).find('td').eq(index).addClass(cssClass);
                            }
                        }
                    });
                }
            });
        }
        
        // Применяем классы из data-атрибутов для настройки ширины
        applyColumnClasses();
        
        // Добавляем интерактивность для ячеек с обрезанным текстом
        $('.column-width-xs, .column-width-sm, .column-width-md, .column-width-lg, .column-width-xl, .column-truncate').each(function() {
            var $cell = $(this);
            var cellContent = $cell.text().trim();
            
            // Добавляем title для отображения полного текста при наведении
            if (cellContent.length > 0) {
                $cell.attr('title', cellContent);
            }
            
            // Добавляем небольшой эффект при наведении для лучшего UX
            $cell.hover(
                function() {
                    // Если контент слишком длинный, показываем его в расширенном виде
                    if (this.scrollWidth > this.clientWidth) {
                        $(this).addClass('cell-expanded');
                    }
                },
                function() {
                    $(this).removeClass('cell-expanded');
                }
            );
        });
        
        // Добавляем CSS-классы к заголовкам и ячейкам таблицы из настроек по умолчанию
        function applyDefaultColumnWidths() {
            // Получаем настройки ширины из data-атрибута таблицы
            var columnWidthSettings = {};
            try {
                var settingsJson = $('table.result_list').data('column-settings');
                if (settingsJson) {
                    columnWidthSettings = JSON.parse(settingsJson);
                }
            } catch (e) {
                console.error('Error parsing column width settings:', e);
            }
            
            // Применяем настройки к заголовкам
            $('table.result_list thead th').each(function(index) {
                var fieldName = $(this).data('field-name');
                if (fieldName && columnWidthSettings[fieldName]) {
                    $(this).addClass(columnWidthSettings[fieldName]);
                    
                    // Применяем тот же класс ко всем ячейкам в этой колонке
                    $('table.result_list tbody tr').each(function() {
                        $(this).find('td').eq(index).addClass(columnWidthSettings[fieldName]);
                    });
                }
            });
        }
        
        // Применяем настройки ширины столбцов по умолчанию
        applyDefaultColumnWidths();
        
        // Добавляем возможность пользовательской настройки ширины столбцов
        // через контекстное меню в заголовке таблицы
        $('th').contextmenu(function(e) {
            e.preventDefault();
            
            var $th = $(this);
            var columnIndex = $th.index();
            var fieldName = $th.data('field-name');
            
            // Если нет field-name, не показываем меню
            if (!fieldName) {
                return;
            }
            
            // Создаем контекстное меню
            var $menu = $('<div class="column-width-menu"></div>');
            
            // Добавляем заголовок
            $menu.append('<div class="menu-header">Настройка ширины</div>');
            
            // Добавляем опции
            var widthOptions = [
                { name: 'XS (60px)', class: 'column-width-xs' },
                { name: 'SM (100px)', class: 'column-width-sm' },
                { name: 'MD (150px)', class: 'column-width-md' },
                { name: 'LG (200px)', class: 'column-width-lg' },
                { name: 'XL (300px)', class: 'column-width-xl' },
                { name: 'Auto', class: '' }
            ];
            
            widthOptions.forEach(function(option) {
                var $option = $('<div class="menu-item" data-class="' + option.class + '">' + option.name + '</div>');
                $menu.append($option);
                
                // Добавляем обработчик клика на опцию
                $option.click(function() {
                    var widthClass = $(this).data('class');
                    
                    // Удаляем все существующие классы ширины
                    $th.removeClass('column-width-xs column-width-sm column-width-md column-width-lg column-width-xl');
                    
                    // Применяем новый класс ширины, если он есть
                    if (widthClass) {
                        $th.addClass(widthClass);
                    }
                    
                    // Применяем тот же класс ко всем ячейкам в этой колонке
                    $('table.result_list tbody tr').each(function() {
                        var $td = $(this).find('td').eq(columnIndex);
                        $td.removeClass('column-width-xs column-width-sm column-width-md column-width-lg column-width-xl');
                        if (widthClass) {
                            $td.addClass(widthClass);
                        }
                    });
                    
                    // Сохраняем настройки в локальное хранилище
                    var storageKey = 'columnWidth_' + window.location.pathname + '_' + fieldName;
                    localStorage.setItem(storageKey, widthClass);
                    
                    // Закрываем меню
                    $menu.remove();
                });
            });
            
            // Добавляем дополнительные опции для обработки текста
            $menu.append('<div class="menu-divider"></div>');
            
            var textOptions = [
                { name: 'Обрезать', class: 'column-truncate' },
                { name: 'Переносить', class: 'column-wrap' },
                { name: 'По умолчанию', class: '' }
            ];
            
            textOptions.forEach(function(option) {
                var $option = $('<div class="menu-item" data-class="' + option.class + '">' + option.name + '</div>');
                $menu.append($option);
                
                // Добавляем обработчик клика на опцию
                $option.click(function() {
                    var textClass = $(this).data('class');
                    
                    // Удаляем все существующие классы обработки текста
                    $th.removeClass('column-truncate column-wrap');
                    
                    // Применяем новый класс обработки текста, если он есть
                    if (textClass) {
                        $th.addClass(textClass);
                    }
                    
                    // Применяем тот же класс ко всем ячейкам в этой колонке
                    $('table.result_list tbody tr').each(function() {
                        var $td = $(this).find('td').eq(columnIndex);
                        $td.removeClass('column-truncate column-wrap');
                        if (textClass) {
                            $td.addClass(textClass);
                        }
                    });
                    
                    // Сохраняем настройки в локальное хранилище
                    var storageKey = 'columnTextStyle_' + window.location.pathname + '_' + fieldName;
                    localStorage.setItem(storageKey, textClass);
                    
                    // Закрываем меню
                    $menu.remove();
                });
            });
            
            // Добавляем опции выравнивания
            $menu.append('<div class="menu-divider"></div>');
            
            var alignOptions = [
                { name: 'По левому краю', class: '' },
                { name: 'По центру', class: 'column-align-center' },
                { name: 'По правому краю', class: 'column-align-right' }
            ];
            
            alignOptions.forEach(function(option) {
                var $option = $('<div class="menu-item" data-class="' + option.class + '">' + option.name + '</div>');
                $menu.append($option);
                
                // Добавляем обработчик клика на опцию
                $option.click(function() {
                    var alignClass = $(this).data('class');
                    
                    // Удаляем все существующие классы выравнивания
                    $th.removeClass('column-align-center column-align-right');
                    
                    // Применяем новый класс выравнивания, если он есть
                    if (alignClass) {
                        $th.addClass(alignClass);
                    }
                    
                    // Применяем тот же класс ко всем ячейкам в этой колонке
                    $('table.result_list tbody tr').each(function() {
                        var $td = $(this).find('td').eq(columnIndex);
                        $td.removeClass('column-align-center column-align-right');
                        if (alignClass) {
                            $td.addClass(alignClass);
                        }
                    });
                    
                    // Сохраняем настройки в локальное хранилище
                    var storageKey = 'columnAlign_' + window.location.pathname + '_' + fieldName;
                    localStorage.setItem(storageKey, alignClass);
                    
                    // Закрываем меню
                    $menu.remove();
                });
            });
            
            // Добавляем кнопку сброса всех настроек
            $menu.append('<div class="menu-divider"></div>');
            var $resetButton = $('<div class="menu-item reset-button">Сбросить настройки</div>');
            $menu.append($resetButton);
            
            $resetButton.click(function() {
                // Удаляем все кастомные классы
                $th.removeClass('column-width-xs column-width-sm column-width-md column-width-lg column-width-xl column-truncate column-wrap column-align-center column-align-right');
                
                // Удаляем все классы у ячеек этой колонки
                $('table.result_list tbody tr').each(function() {
                    var $td = $(this).find('td').eq(columnIndex);
                    $td.removeClass('column-width-xs column-width-sm column-width-md column-width-lg column-width-xl column-truncate column-wrap column-align-center column-align-right');
                });
                
                // Удаляем настройки из локального хранилища
                var pathPrefix = 'column_' + window.location.pathname + '_' + fieldName;
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    if (key.indexOf(pathPrefix) === 0) {
                        localStorage.removeItem(key);
                    }
                }
                
                // Закрываем меню
                $menu.remove();
            });
            
            // Добавляем меню на страницу
            $('body').append($menu);
            
            // Позиционируем меню у места клика
            $menu.css({
                top: e.pageY + 'px',
                left: e.pageX + 'px'
            });
            
            // Закрываем меню при клике вне его
            $(document).one('click', function() {
                $menu.remove();
            });
        });
        
        // Восстанавливаем сохраненные настройки из локального хранилища
        $('table.result_list thead th').each(function() {
            var fieldName = $(this).data('field-name');
            if (!fieldName) return;
            
            var columnIndex = $(this).index();
            var $th = $(this);
            
            // Восстанавливаем ширину
            var widthClass = localStorage.getItem('columnWidth_' + window.location.pathname + '_' + fieldName);
            if (widthClass) {
                $th.addClass(widthClass);
                
                // Применяем к ячейкам
                $('table.result_list tbody tr').each(function() {
                    $(this).find('td').eq(columnIndex).addClass(widthClass);
                });
            }
            
            // Восстанавливаем стиль текста
            var textClass = localStorage.getItem('columnTextStyle_' + window.location.pathname + '_' + fieldName);
            if (textClass) {
                $th.addClass(textClass);
                
                // Применяем к ячейкам
                $('table.result_list tbody tr').each(function() {
                    $(this).find('td').eq(columnIndex).addClass(textClass);
                });
            }
            
            // Восстанавливаем выравнивание
            var alignClass = localStorage.getItem('columnAlign_' + window.location.pathname + '_' + fieldName);
            if (alignClass) {
                $th.addClass(alignClass);
                
                // Применяем к ячейкам
                $('table.result_list tbody tr').each(function() {
                    $(this).find('td').eq(columnIndex).addClass(alignClass);
                });
            }
        });
    });
    
    // Добавляем стили для контекстного меню
    var style = `
        .column-width-menu {
            position: absolute;
            background: white;
            border: 1px solid #ccc;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 9999;
            border-radius: 4px;
            min-width: 150px;
            padding: 5px 0;
        }
        .menu-header {
            padding: 5px 10px;
            font-weight: bold;
            border-bottom: 1px solid #eee;
            margin-bottom: 5px;
        }
        .menu-item {
            padding: 5px 10px;
            cursor: pointer;
        }
        .menu-item:hover {
            background-color: #f5f5f5;
        }
        .menu-divider {
            height: 1px;
            background-color: #eee;
            margin: 5px 0;
        }
        .reset-button {
            color: #d9534f;
        }
        .cell-expanded {
            position: absolute;
            background: white;
            z-index: 1000;
            border: 1px solid #ddd;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            padding: 5px;
            border-radius: 3px;
            white-space: normal;
            max-width: 300px;
        }
    `;
    
    $('head').append('<style>' + style + '</style>');
    
})(django.jQuery); 