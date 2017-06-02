from django.core.management.base import BaseCommand
from botmanager import settings
import logging
import logging.config


class BotManagerBaseCommandException(Exception):
    pass


class BotManagerBaseCommand(BaseCommand):

    def set_logging(self):
        if settings.TASKS_LOGGING is not None:
            logging.config.dictConfig(settings.TASKS_LOGGING)
            root_logger = logging.getLogger()
            root_logger.handlers = logging.getLogger('default').handlers
            root_logger.setLevel(settings.DEFAULT_LOG_LEVEL)
