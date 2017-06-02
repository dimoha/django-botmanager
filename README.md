# django-botmanager
Async tasks for django

1. pip install django-botmanager
2. run migrations
3. add BOTMANAGER_CONFIG to settings.py, for example

```
BOTMANAGER_CONFIG = {
    'tasks': {
        'my_app.tasks.example_tasks.ExampleTask1': 2,
        'my_app.tasks.example_tasks.ExampleTask2': 5,
        ....
    },
    'logs': {
        'dir': LOG_DIR,
        'logs_life_hours': 5*24,
        'task_logs_separated': True,
        'success_tasks_life_hours': 2,
        'level': 'INFO',
        'mail_admins': False,
        'sentry_enabled': True
    }
}
```