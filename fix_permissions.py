#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_ratings.settings')
django.setup()

from django.db import connection

def fix_permissions():
    with connection.cursor() as cursor:
        # Предоставляем права на схему public
        cursor.execute("GRANT ALL ON SCHEMA public TO school_rating_user;")
        
        # Предоставляем права на все таблицы в схеме public
        cursor.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO school_rating_user;")
        
        # Предоставляем права на все последовательности в схеме public
        cursor.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO school_rating_user;")
        
        # Устанавливаем владельца схемы public
        cursor.execute("ALTER SCHEMA public OWNER TO school_rating_user;")
        
        print("Права успешно обновлены")

if __name__ == "__main__":
    fix_permissions() 