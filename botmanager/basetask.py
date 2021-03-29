# -*- coding: utf-8 -*-
import logging
import logging.config
import os
import traceback
import json
from botmanager import settings
from botmanager.models import Task
from django.conf import settings as project_settings
from django.db import connection
from datetime import datetime, timedelta
from hashlib import md5
from botmanager import BotManagerTaskError
from django.utils import timezone


LOGGING = settings.TASKS_LOGGING


class StopTaskSuccess(BotManagerTaskError):
    pass


class BotManagerBaseTask(object):

    actions = []
    name = 'unknown'
    DEFAULT_ATTEMPT_PERIOD = 1
    SELF_SUPPORT = True

    def __init__(self, task):
        self.task = task
        self.config = settings.MAIN_CONFIG
        if self.config['logs']['task_logs_separated']:
            self.set_task_logger()
        self._on_init()

    def get_log_file_name(self):
        return u"task{0}".format(self.task.id)

    @classmethod
    def prepare(cls):
        pass

    def _on_init(self):
        pass

    @classmethod
    def get_queue_key(cls, task_input):
        return md5('{}_{}'.format(cls.name, json.dumps(task_input)).encode('utf-8')).hexdigest()

    @classmethod
    def create(cls, **kwargs):
        attempt_period = kwargs.pop('attempt_period', timedelta(hours=cls.DEFAULT_ATTEMPT_PERIOD))
        is_unique = kwargs.pop('is_unique', False)

        main_params = kwargs.copy()
        main_params.update({
            'name': cls.name,
            'queue_key': cls.get_queue_key(kwargs.get('input')),
        })
        if is_unique:
            task, created = Task.objects.get_or_create(
                defaults={
                    'attempt_period': attempt_period,
                },
                is_complete=False,
                **main_params
            )
        else:
            task = Task.objects.create(
                attempt_period=attempt_period,
                **main_params
            )
            created = True

        if created:
            logging.info('Task created. Name {}. id {}. args {}'.format(cls.name, task.pk, task.input))
        else:
            logging.info('Task already exists and not finished. Name {}. id {}. args {}'.format(
                cls.name, task.pk, task.input
            ))

        return task, created

    def set_task_logger(self):
        level = self.config['logs']['level'] if 'level' in self.config['logs'] else settings.DEFAULT_LOG_LEVEL

        task_file_dir = os.path.join(self.config['logs']['dir'], self.name)
        task_file_path = os.path.join(task_file_dir, u'{0}.log'.format(self.get_log_file_name()))
        log_handler_name = 'botmanager.{0}'.format(self.name)

        if not os.path.exists(task_file_dir):
            os.mkdir(task_file_dir)

        # create task logger
        LOGGING.setdefault('handlers', {})
        LOGGING['handlers'][self.name] = {
            'level': level,
            'class': 'logging.FileHandler',
            'filename': task_file_path,
            'formatter': 'default',
            'encoding': 'utf-8',
        }
        LOGGING.setdefault('loggers', {})
        handlers = ['common_errors', 'common', self.name]

        if project_settings.DEBUG:
            handlers.append('console')

        sentry_enabled = self.config['logs'].get('sentry_enabled', False)
        if sentry_enabled:
            handlers.append('sentry')

        LOGGING['loggers'][log_handler_name] = {
            'handlers': handlers,
            'level': 'INFO',
            'propagate': False
        }

        logging.config.dictConfig(LOGGING)

        # copy task logger handlers to root logger
        root_logger = logging.getLogger()
        root_logger.handlers = logging.getLogger(log_handler_name).handlers
        root_logger.setLevel(logging.INFO)

    def _set_output(self, data):
        self.task.output = data
        self.task.save(update_fields=('output',))

    @classmethod
    def set_tasks(cls, **kwargs):
        pass

    def _handle_error(self, e):
        pass

    def _on_finish(self, is_success=True, is_complete=True):
        pass

    def _log_task_finish(self, is_success):
        logging.info('Task {0} FINISHED: success={1}, now={2}, args {3}'.format(
            self.task.pk, is_success, datetime.now(), self.task.input
        ))

    def _on_start(self):
        pass

    def is_valid_input_or_success(self):
        u""" Если в задачу пришли невалидные параметры - задача считается успешно выполненой """
        return True

    def should_skip_action(self, action):
        pass

    def run(self):
        logging.info('Run task {} {}'.format(self.name, self.task.pk))
        self._on_start()

        if self.task.input is None:
            self.task.input = {}
        if self.task.output is None:
            self.task.output = {}

        is_failed = False
        is_error_handled = False

        if self.is_valid_input_or_success():
            for action in self.actions:

                if self.should_skip_action(action):
                    logging.info('Skipping action because we should {}'.format(action))
                    continue

                if self.task.failed_action and self.task.failed_action != action:
                    logging.info('Task has failed action {}. ID {}. Skipping {}'.format(
                        self.task.failed_action, self.task.pk, action
                    ))
                    continue

                self.task.failed_action = None

                logging.info(u"Start action {}. id {}".format(action, self.task.pk))
                action_method = getattr(self, action)
                try:
                    action_method()
                    logging.info(u'End action {}. id {}'.format(action, self.task.pk))
                except StopTaskSuccess:
                    logging.info(u'Stop actions because StopTaskSuccess caught')
                    break
                except Exception as e:
                    logging.exception(e)
                    self.task.failed_action = action
                    is_error_handled = self._handle_error(e)
                    self.task.last_error_dt = timezone.now()
                    self.task.last_error = {
                        'error': str(e),
                        'trace': traceback.format_exc(),
                    }
                    logging.info('Exception caught and handled {}'.format(str(e)))
                    is_failed = not is_error_handled
                    break
        else:
            logging.warning(u'Task input is invalid and task marker as success.')

        self.task.is_failed = is_failed

        self.task.attempt_count += 1
        if is_failed and self.task.is_persistent:
            if self.task.max_attempt_count is None:
                is_complete = False
            else:
                if self.task.attempt_count < self.task.max_attempt_count:
                    is_complete = False
                else:
                    is_complete = True
        else:
            is_complete = True

        now = timezone.now()

        self.task.is_complete = is_complete
        if is_complete:
            self.task.finish_dt = now

        logging.info('Set task in_process False. id {}'.format(self.task.pk))
        self.task.in_process = False
        self.task.last_attempt_dt = now

        is_success = not is_failed or is_error_handled
        self._on_finish(is_success=is_success, is_complete=is_complete)
        self.task.save()
        logging.info('Closing connection to DB...')
        connection.close()
        logging.info('End run task {} id {}'.format(self.name, self.task.pk))
