CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379',
        'OPTIONS': {
            'db': '2',
            'parser_class': 'redis.connection.PythonParser',
            'pool_class': 'redis.connection.BlockingConnectionPool',
        }
    }
} 