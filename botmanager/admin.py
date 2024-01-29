# -*- coding: utf-8 -*-
import os

from django.contrib import admin
from django.http import HttpResponseNotFound, FileResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from botmanager.models import Task
from botmanager import settings
from botmanager.management.commands.bot_manager import Command


class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_complete', 'in_process', 'is_failed',
                    'create_dt', 'finish_dt', 'error_field', 'attempt_period', 'attempt_count', 'input_field']
    list_filter = ('is_complete', 'is_failed', 'in_process', 'name')
    search_fields = ('id', 'name')
    change_form_template = 'botmanager/task/change_form.html'

    def get_queryset(self, request):
        qs = super(TaskAdmin, self).get_queryset(request)
        return qs

    def error_field(self, obj):
        err_max_len = 50
        if isinstance(obj.last_error, dict) and 'error' in obj.last_error:
            return "Failed dt: {0}<br />Failed action: {1}<br />Error: {2}".format(
                obj.last_error_dt.strftime("%Y-%m-%d %H:%M:%S"),
                obj.failed_action,
                '<span style="cursor:help" title="{0}">{1} ...</span>'.format(
                    escape(obj.last_error['error']),
                    escape(obj.last_error['error'][0:err_max_len])
                ) if len(obj.last_error['error']) > err_max_len else obj.last_error['error']
            )
        else:
            return None

    error_field.short_description = _("Ошибка")
    error_field.allow_tags = True

    def input_field(self, obj):
        return obj.input

    input_field.short_description = _("Вводные данные")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<path:task_id>/open-logfile/",
                 self.admin_site.admin_view(self.open_logfile),
                 name="botmanager_task_open_logfile"),
        ]
        return custom_urls + urls

    def open_logfile(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        imported_class = [
            Command.import_from_string(i) for i in settings.MAIN_CONFIG["tasks"].keys()
            if Command.import_from_string(i).name == task.name
        ]

        if not imported_class:
            return HttpResponseNotFound()

        filename = imported_class[0](task).get_log_file_name()
        dir = settings.MAIN_CONFIG["logs"]["dir"]
        file_path = os.path.join(dir, filename)

        if os.path.exists(file_path):
            return FileResponse(open(file_path, "rb"))
        else:
            return HttpResponseNotFound()

    open_logfile.short_description = _(u"Открыть файл")


admin.site.register(Task, TaskAdmin)
