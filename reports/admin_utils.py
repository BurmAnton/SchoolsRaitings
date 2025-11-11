from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.safestring import mark_safe


class ColumnWidthMixin:
    """
    Миксин для управления шириной столбцов в административной панели Django.
    
    Использование:
    1. Добавьте этот миксин к вашему классу ModelAdmin
    2. Определите column_width_settings в вашем классе как словарь с именами полей
       и соответствующими классами CSS для ширины столбцов
    
    Пример:
    
    class MyModelAdmin(ColumnWidthMixin, admin.ModelAdmin):
        list_display = ['id', 'name', 'description', 'status']
        column_width_settings = {
            'id': 'column-width-xs',
            'name': 'column-width-md',
            'description': 'column-width-lg column-wrap',
            'status': 'column-width-sm column-align-center',
        }
    """
    
    column_width_settings = {}  # Переопределите это в вашем ModelAdmin
    
    class CustomChangeList(ChangeList):
        """Кастомный ChangeList с поддержкой настроек ширины столбцов"""
        
        def __init__(self, model_admin, *args, **kwargs):
            """Сохраняем ссылку на model_admin для доступа к настройкам ширины столбцов"""
            self.model_admin_width = model_admin
            super().__init__(model_admin, *args, **kwargs)
            
        def get_results(self, *args, **kwargs):
            """Переопределяем метод для модификации результатов после основной обработки"""
            result = super().get_results(*args, **kwargs)
            
            # Проверяем наличие model_admin_width и column_width_settings
            if hasattr(self, 'model_admin_width') and hasattr(self.model_admin_width, 'column_width_settings'):
                column_settings = self.model_admin_width.column_width_settings
                
                # Применяем CSS-классы к ячейкам только если настройки не пустые
                if column_settings:
                    # Применяем настройки ширины к строкам результатов
                    for row in self.result_list:
                        # Добавляем dict для хранения CSS-классов для каждой ячейки
                        row._custom_column_classes = {}
                        
                        # Применяем CSS классы к каждой ячейке в строке
                        for i, field_name in enumerate(self.list_display):
                            if field_name in column_settings:
                                row._custom_column_classes[field_name] = column_settings[field_name]
            
            return result
    
    def get_changelist(self, request, **kwargs):
        """Возвращает кастомный ChangeList для управления шириной столбцов"""
        return self.CustomChangeList
    
    def changelist_view(self, request, extra_context=None):
        """
        Добавляем дополнительный контекст для настройки ширины столбцов
        """
        extra_context = extra_context or {}
        
        # Добавляем настройки ширины столбцов в контекст шаблона
        extra_context['column_width_settings'] = self.column_width_settings
        
        # Вызываем оригинальный метод
        response = super().changelist_view(request, extra_context)
        
        return response
    
    def result_row_attrs(self, result, index):
        """Метод для добавления атрибутов к строкам результата"""
        attrs = super().result_row_attrs(result, index) if hasattr(super(), 'result_row_attrs') else {}
        
        # Если у объекта есть кастомные классы для колонок
        if hasattr(result, '_custom_column_classes'):
            attrs['data-column-classes'] = ','.join(
                f"{field_name}:{css_class}" 
                for field_name, css_class in result._custom_column_classes.items()
            )
        
        return attrs


def add_custom_admin_css(cls):
    """
    Декоратор для добавления нашего CSS-файла в класс ModelAdmin
    
    Пример использования:
    
    @add_custom_admin_css
    class MyModelAdmin(ColumnWidthMixin, admin.ModelAdmin):
        ...
    """
    if not hasattr(cls, 'Media'):
        class Media:
            css = {
                'all': ('admin/css/column_width.css',)
            }
        cls.Media = Media
    else:
        if not hasattr(cls.Media, 'css'):
            cls.Media.css = {'all': ('admin/css/column_width.css',)}
        else:
            css_all = cls.Media.css.get('all', ())
            if isinstance(css_all, str):
                css_all = (css_all,)
            if 'admin/css/column_width.css' not in css_all:
                cls.Media.css['all'] = css_all + ('admin/css/column_width.css',)
    
    return cls 