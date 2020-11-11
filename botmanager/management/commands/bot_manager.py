# -*- coding: utf-8 -*-
import importlib
import logging
import os
import sys
from datetime import datetime, timedelta
from multiprocessing import Queue, Process
from time import sleep, time

import six
from django.db import connections
from django.db.models import Q
from django.utils import timezone

from botmanager import settings
from botmanager.management.commands import BotManagerBaseCommand, BotManagerBaseCommandException
from botmanager.models import Task
from botmanager.utils import management_lock

if six.PY2:
    from Queue import Empty as QueueEmpty
else:
    from queue import Empty as QueueEmpty

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: x


class BotManagerCommandException(BotManagerBaseCommandException):
    pass


class Command(BotManagerBaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='?', choices=('start', 'stop', 'restart'), default='start')
        parser.add_argument('--soft', action='store_true', default=False)
        parser.add_argument('--without_sheduller', action='store_true', default=False)
        parser.add_argument('--task_cls', type=str)

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

        self.config = settings.MAIN_CONFIG

        if 'tasks' not in self.config:
            raise BotManagerCommandException(u"settings.BOTMANAGER_CONFIG['tasks'] not found")

        if len(self.config['tasks']) == 0:
            raise BotManagerCommandException(u"settings.BOTMANAGER_CONFIG['tasks'] is empty")

    @staticmethod
    def import_from_string(val):
        try:
            parts = val.split('.')
            module_path, class_name = '.'.join(parts[:-1]), parts[-1]
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except ImportError as e:
            raise ImportError(
                u"Could not import '%s' for setting. %s: %s." % (val, e.__class__.__name__, e)
            )

    @staticmethod
    def start_service(service):
        logging.info(u"Start task manager {0}".format(service.process_name))
        connections.close_all()
        try:
            service.run()
        except KeyboardInterrupt:
            pass
        finally:
            connections.close_all()

    def handle(self, *args, **options):
        if options['action'] in ['stop', 'restart']:
            if options['soft']:
                raise NotImplementedError("Soft stopping is not implemented")
            else:
                logging.info("BotManager stopped.")
                if options['action'] == 'stop':
                    return
        logging.info(u"Try start BotManager...")
        sleep(1)
        self.run(*args, **options)

    def __clean_dir(self, dir_path, life_hours, full_clean=False):
        if os.path.isdir(dir_path):
            files = os.listdir(dir_path)
            for f in files:
                log_file_path = os.path.join(dir_path, f)
                if os.path.isfile(os.path.join(dir_path, f)):
                    hours = (int(time()) - int(os.path.getctime(log_file_path))) / 3600
                    if hours >= life_hours or full_clean:
                        logging.debug('clean file: {0} ({1} days)'.format(log_file_path, hours))
                        os.remove(log_file_path)

                elif os.path.isdir(log_file_path):
                    self.__clean_dir(log_file_path, life_hours, full_clean=full_clean)

    def remove_logs(self, logs_life_hours):
        log_config = self.config['logs']
        logs_dir = log_config['dir'] if 'dir' in log_config else None

        if logs_dir:
            logging.info("Start clean logs dir {0} with logs_life_hours={1}".format(
                logs_dir, logs_life_hours
            ))
            task_types = []
            for dir_name in os.listdir(logs_dir):
                dir_path = os.path.join(logs_dir, dir_name)
                if os.path.isdir(dir_path):
                    task_types.append(dir_name)

            for task_type in task_types:
                task_dir = os.path.join(logs_dir, task_type)
                self.__clean_dir(task_dir, life_hours=logs_life_hours)

    def remove_tasks(self, tasks_life_hours):
        Task.objects.filter(
            Q(parent=None) | Q(parent__is_complete=True),
            is_complete=True,
            finish_dt__lt=timezone.now() - timedelta(hours=tasks_life_hours)
        ).delete()

    @management_lock
    def run(self, *args, **options):

        self.set_logging()

        logging.info(u"Starting BotManager")
        setproctitle(u"BotManager.General")

        current_pid = os.getpid()

        processes = []
        queue_dict = {}
        for task_class_string, processes_count in self.config['tasks'].items():
            cls_name = task_class_string.split('.')[-1]
            if options['task_cls'] and cls_name != options['task_cls']:
                logging.info('Continue task class {}'.format(cls_name))
                continue
            task_class = Command.import_from_string(task_class_string)
            self._validate_task_class(task_class)
            # task_class.prepare()

            maxsize = processes_count * 10
            queue_dict[task_class.name] = Queue(maxsize=maxsize)
            queue_dict[task_class.name].maxsize = maxsize

            for i in range(processes_count):
                tm = TaskManager(task_class, queue_dict[task_class.name], i + 1, current_pid)
                p = Process(target=Command.start_service, args=(tm,))
                p.name = tm.process_name
                p.daemon = True
                p.start()
                processes.append(p)

        tf = TaskFetcher(queue_dict, current_pid)
        p = Process(target=Command.start_service, args=(tf,))
        p.name = tf.process_name
        p.daemon = True
        p.start()
        processes.append(p)

        if not options.get('without_sheduller'):
            ts = TaskSheduler(self.config, current_pid)
            p = Process(target=Command.start_service, args=(ts,))
            p.name = ts.process_name
            p.daemon = True
            p.start()
            processes.append(p)

        next_clean_logs_dt = next_clean_tasks_dt = datetime.now() + timedelta(seconds=10)
        logs_life_hours = self.config['logs']['logs_life_hours']
        tasks_life_hours = self.config['logs']['success_tasks_life_hours']
        need_remove_logs = self.config['logs']['task_logs_separated'] and logs_life_hours is not None
        need_remove_tasks = tasks_life_hours is not None

        logging.info("logs_life_hours={0}, tasks_life_hours={1}, need_remove_logs={2}, need_remove_tasks={3}".format(
            logs_life_hours, tasks_life_hours, need_remove_logs, need_remove_tasks
        ))

        connections.close_all()

        while True:
            statuses = set(map(lambda x: x.is_alive(), processes))
            if len(statuses) == 1 and list(statuses)[0] is False:
                break
            else:
                if need_remove_logs:
                    if next_clean_logs_dt <= datetime.now():
                        logging.info("Start delete old separated tasks logs...")
                        self.remove_logs(logs_life_hours)
                        next_clean_logs_dt += timedelta(hours=1)
                        logging.info("Delete old logs finished, next at {0}".format(next_clean_logs_dt))

                if need_remove_tasks:
                    if next_clean_tasks_dt <= datetime.now():
                        logging.info("Start delete old success tasks...")
                        self.remove_tasks(tasks_life_hours)
                        next_clean_tasks_dt += timedelta(hours=1)
                        logging.info("Delete old success tasks finished, next at {0}".format(next_clean_tasks_dt))
            sleep(5)

        logging.info(u"BotManager is stopped.")

    def _validate_task_class(self, _class):
        if not hasattr(_class, 'actions'):
            raise BotManagerCommandException('No actions in class {}'.format(_class.__name__))

        if not _class.actions:
            raise BotManagerCommandException('Empty actions in class {}'.format(_class.__name__))

        for action_str in _class.actions:
            if not hasattr(_class, action_str):
                raise BotManagerCommandException('Invalid action {} in class {}'.format(
                    action_str, _class.__name__
                ))


class TaskSheduler(object):
    SET_PERIOD_SECONDS = 5

    def __init__(self, config, parent_pid):
        self.process_name = "BotManager.TaskSheduler"
        self.config = config
        self.parent_pid = parent_pid
        self.shedule_cache = {}

    def run(self):
        setproctitle(self.process_name)
        while True:

            if os.getppid() != self.parent_pid:
                logging.info(u"Parent process is die. Exit..")
                break

            for task_class_string, processes_count in self.config['tasks'].items():
                task_class = Command.import_from_string(task_class_string)

                if self._time_to_set_tasks_for(task_class) and task_class.SELF_SUPPORT:
                    self.shedule_cache[task_class.name] = datetime.now()
                    try:
                        task_class.set_tasks()
                    except Exception as e:
                        logging.exception(e)

            sleep(self.SET_PERIOD_SECONDS)

    def _time_to_set_tasks_for(self, task_class):
        last_shedule_time = self.shedule_cache.get(task_class.name)
        shedule_period = getattr(task_class, 'SHEDULE_PERIOD_SECONDS', self.SET_PERIOD_SECONDS)
        return not last_shedule_time or datetime.now() > (last_shedule_time + timedelta(seconds=shedule_period))


class TaskFetcher(object):

    def __init__(self, queue_dict, parent_pid):
        self.process_name = "BotManager.TaskFetcher"
        self.queue_dict = queue_dict
        self.parent_pid = parent_pid
        self.config = settings.MAIN_CONFIG

    def run(self):
        """
        Сделано на скорую руку. На текущих объемах этого более чем достаточно, но при увеличении кол-ва тасков,
        а так же типов тасков, надо решить следующие задачи:

        1. Запрос к БД берет все невыполненные таски хотя размеры очередей ограничены,
           значит брать нужно лимитированное кол-во каждого типа таска (столько сколько может влезть).
        2. Если брать задачи каждого типа таска отдельно, чтоб учитывать лимиты из п1, то когда типов тасков будет
           много, например 100. то наполнение очереди будет отставать.
        3. Учитывать queue_key для группировки
        4. в данный момент берутся из БД заведомо лишние задачи, у которых can_execute==False
        5. in_process ставится отдельно на каждую взятую задачу а не разово на всех.
        """
        setproctitle(self.process_name)
        Task.objects.filter(in_process=True).update(in_process=False)
        while True:
            try:

                if os.getppid() != self.parent_pid:
                    logging.info(u"Parent process is die. Exit..")
                    break

                tasks = Task.objects.filter(
                    is_complete=False
                ).order_by('-priority', 'id')

                running_tasks = {}
                for task in tasks:
                    logging.info('Fetching task {}'.format(task))

                    if task.in_process:
                        logging.info('Task in process. Putting to running_tasks dict {} {}'.format(task, task.queue_key))
                        running_tasks[task.queue_key] = task.id
                        continue
                    else:
                        if task.queue_key in running_tasks:
                            logging.info(
                                u"Do not put to queue task {0}, because already queued "
                                u"task {1} with same queue_key".format(
                                    task.id, running_tasks[task.queue_key]
                                )
                            )
                            continue

                    if task.can_execute:
                        if task.name not in self.queue_dict:
                            logging.info('Task can execute but there is no queue_dict for task name {} {} {}. Passing...'.format(
                                task.name, task, task.queue_key
                            ))
                            pass
                            # logging.warning(U"Undefined task type {0} with id {1}".format(task.name, task.id))
                        else:
                            if self._get_qsize(task) < self.queue_dict[task.name].maxsize:
                                logging.info('Task can execute. Putting to queue_dict with key {} {}'.format(
                                    task.name, task
                                ))
                                task.in_process = True
                                task.save(update_fields=('in_process',))
                                running_tasks[task.queue_key] = task.id
                                self.queue_dict[task.name].put(task)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                logging.exception(e)

            sleep(self.config['fetch_period'])

    def _get_qsize(self, task):
        try:
            return self.queue_dict[task.name].qsize()
        except NotImplementedError:
            # Queue.qsize not working on Mac OS X
            from random import randint
            return randint(0, self.queue_dict[task.name].maxsize)


class TaskManager(object):
    def __init__(self, task_class, queue, process_num, parent_pid):
        self.task_class = task_class
        self.queue = queue
        self.process_num = process_num
        self.process_name = u"BotManager.{0}.{1}".format(self.task_class.name, self.process_num)
        self.parent_pid = parent_pid

    def __str__(self):
        return self.process_name

    def run_task(self, task):
        logging.info(u"Start {0}".format(task))
        self.task_class(task).run()

    def run(self):
        setproctitle(self.process_name)
        while True:
            try:

                if os.getppid() != self.parent_pid:
                    logging.info(u"Parent process is die. Exit..")
                    break

                task = self.queue.get_nowait()
                try:
                    self.run_task(task)
                except Exception as e:
                    logging.exception(u"Worker {0} catch exception on task {1}: {2}".format(
                        self, task.id, e
                    ))
                finally:
                    pass
            except QueueEmpty:
                sleep(1)
            except Exception as e:
                logging.exception(
                    u"Error in queue preparing: %s".format(e)
                )
