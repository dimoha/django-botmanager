# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from jsonfield import JSONField
from datetime import timedelta, datetime
from django.utils import timezone


class Task(models.Model):

    STATUS_NEW = 'NEW'
    STATUS_IN_PROCESS = 'IN_PROCESS'
    STATUS_OK = 'OK'

    STATUSES = (
        (STATUS_NEW, u'В ожидании'),
        (STATUS_IN_PROCESS, u'Идет загрузка'),
        (STATUS_OK, u'Данные загружены'),
    )

    name = models.CharField(max_length=256, verbose_name=u'Название')
    create_dt = models.DateTimeField(verbose_name=u"Дата создания задачи", auto_now_add=True)
    finish_dt = models.DateTimeField(verbose_name=u"Дата завершения", null=True, blank=True)
    is_complete = models.BooleanField(verbose_name=u"Выполнена", default=False)
    is_failed = models.BooleanField(verbose_name=u"Аварийное завершение", default=False)
    is_persistent = models.BooleanField(verbose_name=u"Выполнять пока не завершится успешно", default=True)
    in_process = models.BooleanField(verbose_name=u"В процессе", default=False)

    input = JSONField(null=True, blank=True)
    output = JSONField(null=True, blank=True)
    last_error = JSONField(null=True, blank=True)
    extra_params = JSONField(null=True, blank=True)

    last_error_dt = models.DateTimeField(verbose_name=u"Дата последнего fail-а", null=True, blank=True)
    queue_key = models.CharField(max_length=32, verbose_name=u'Ключ группировки задач')
    failed_action = models.CharField(max_length=256, verbose_name=u'Action, на котором произошла ошибка', null=True, blank=True)
    attempt_count = models.SmallIntegerField(verbose_name=u'Счетчик попыток', default=0)
    last_attempt_dt = models.DateTimeField(verbose_name=u"Последняя попытка выполнения", null=True, blank=True)
    max_attempt_count = models.IntegerField(
        verbose_name=u"Максимальное кол-во попыток выполнение (если None, то бесконечно)", null=True, blank=True
    )
    attempt_period = models.DurationField(verbose_name=u'Период между попытками', default=timedelta(hours=1))
    parent = models.ForeignKey('self', verbose_name=u'Родительская задача', null=True, blank=True, related_name='child_tasks', on_delete=models.CASCADE)
    priority = models.SmallIntegerField(default=0)

    def __unicode__(self):
        return "Task {0} #{1}".format(self.name, self.id)

    @property
    def can_execute(self):
        if not self.is_complete and not self.in_process:
            if self.is_failed:
                if self.last_attempt_dt + self.attempt_period > timezone.now():
                    return False
                else:
                    if self.max_attempt_count is None:
                        return True
                    else:
                        if self.attempt_count < self.max_attempt_count:
                            return True
                        else:
                            return False  # надо пофиксить is_complete ?
            else:
                return True
        else:
            return False

    class Meta:
        db_table = 'botmanager_task'
        verbose_name = u"Задача для BotManager"
        verbose_name_plural = u"Задачи для BotManager"