from django.conf import settings
import copy
import sys
import os

MAIN_CONFIG = copy.copy(getattr(settings, 'BOTMANAGER_CONFIG', {}))

if 'fetch_period' not in MAIN_CONFIG:
    MAIN_CONFIG['fetch_period'] = 5

if 'logs' not in MAIN_CONFIG:
    MAIN_CONFIG['logs'] = {}
if 'tasks' not in MAIN_CONFIG:
    MAIN_CONFIG['tasks'] = []

if 'task_logs_separated' not in MAIN_CONFIG['logs']:
    MAIN_CONFIG['logs']['task_logs_separated'] = False
if MAIN_CONFIG['logs']['task_logs_separated'] and 'logs_life_hours' not in MAIN_CONFIG['logs']:
    MAIN_CONFIG['logs']['logs_life_hours'] = 7*24
if 'success_tasks_life_hours' not in MAIN_CONFIG['logs']:
    MAIN_CONFIG['logs']['success_tasks_life_hours'] = 7*24

DEFAULT_LOG_LEVEL = 'INFO'

if 'dir' in MAIN_CONFIG['logs'] and MAIN_CONFIG['logs']['dir'] is not None:

    log_conf = MAIN_CONFIG['logs']
    max_bytes = log_conf['maxBytes'] if 'maxBytes' in log_conf and log_conf['maxBytes'] else 1024*1024*100
    backupCount = log_conf['backupCount'] if 'backupCount' in log_conf and log_conf['backupCount'] else 10
    level = log_conf['level'] if 'level' in log_conf and log_conf['level'] else DEFAULT_LOG_LEVEL
    sentry_enabled = log_conf.get('sentry_enabled', False)

    handlers = ['console', 'common_errors', 'common']

    if sentry_enabled:
        handlers.append('sentry')

    if 'mail_admins' in log_conf and log_conf['mail_admins']:
        handlers.append('mail_admins')

    TASKS_LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'sentry': {
                'level': 'ERROR',
                'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            },
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
            },
            'console': {
                'level': level,
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': sys.stdout
            },
            'common_errors': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_conf['dir'], 'botmanager_errors.log'),
                'maxBytes': max_bytes,
                'formatter': 'default',
                'encoding': 'utf-8',
                'backupCount': backupCount,
            },
            'common': {
                'level': level,
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_conf['dir'], 'botmanager.log'),
                'maxBytes': max_bytes,
                'formatter': 'default',
                'encoding': 'utf-8',
                'backupCount': backupCount,
            }
        },
        'loggers': {
            'default': {
                'handlers': handlers,
                'level': level,
                'propagate': False
            },
        }
    }
else:
    TASKS_LOGGING = None
