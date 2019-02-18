# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.html import escape
from botmanager.models import Task


class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_complete', 'in_process', 'is_failed',
                    'create_dt', 'finish_dt', 'error_field', 'attempt_period', 'attempt_count', 'input_field']
    list_filter = ('is_complete', 'is_failed', 'in_process', 'name')
    search_fields = ('id', 'name')

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

    error_field.short_description = u"Ошибка"
    error_field.allow_tags = True

    def input_field(self, obj):
        return obj.input

    input_field.short_description = "Вводные данные"

admin.site.register(Task, TaskAdmin)
