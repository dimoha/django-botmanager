import fcntl
import logging
import os
from django.conf import settings
from botmanager.models import Task
from django.db import transaction, DatabaseError


def management_lock(view_func):

    def wrapper_lock(*args, **kwargs):
        try:
            lock_file_path = os.path.join(settings.BASE_DIR, "{0}.lock".format(args[0].__class__.__module__.split('.')[-1]))
            f = open(lock_file_path, 'w')
            fcntl.lockf(f, fcntl.LOCK_EX + fcntl.LOCK_NB)
        except IOError:
            logging.debug("Process already is running.")
            os._exit(1)
        return view_func(*args, **kwargs)

    wrapper_lock.view_func = view_func.view_func if hasattr(view_func, 'view_func') else view_func
    return wrapper_lock


def lock_task(task_id):
    if not transaction.get_connection().in_atomic_block:
        raise Exception('check_can_run_task need transaction.atomic')

    try:
        task = Task.objects.select_for_update(nowait=True).get(pk=task_id)
        return task
    except DatabaseError:
        logging.info('task_id={} still in process'.format(task_id))
        return
