import fcntl
import logging
from django.db import connections
import os


def management_lock(view_func):

    def wrapper_lock(*args, **kwargs):
        try:
            lock_file_path = os.path.join('/tmp/', "{0}.lock".format(args[0].__class__.__module__.split('.')[-1]))
            f = open(lock_file_path, 'w')
            fcntl.lockf(f, fcntl.LOCK_EX + fcntl.LOCK_NB)
        except IOError:
            logging.debug("Process already is running.")
            os._exit(1)
        return view_func(*args, **kwargs)

    wrapper_lock.view_func = view_func.view_func if hasattr(view_func, 'view_func') else view_func
    return wrapper_lock
