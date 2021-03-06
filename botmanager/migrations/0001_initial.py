# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-12-07 21:54
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, verbose_name='\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435')),
                ('create_dt', models.DateTimeField(auto_now=True, verbose_name='\u0414\u0430\u0442\u0430 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f \u0437\u0430\u0434\u0430\u0447\u0438')),
                ('finish_dt', models.DateTimeField(null=True, verbose_name='\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f')),
                ('is_complete', models.BooleanField(default=False, verbose_name='\u0412\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0430')),
                ('is_failed', models.BooleanField(default=False, verbose_name='\u0410\u0432\u0430\u0440\u0438\u0439\u043d\u043e\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u0435')),
                ('in_process', models.BooleanField(default=False, verbose_name='\u0412 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0435')),
                ('input', jsonfield.fields.JSONField(null=True)),
                ('output', jsonfield.fields.JSONField(null=True)),
                ('queue_key', models.CharField(max_length=32, verbose_name='\u041a\u043b\u044e\u0447 \u0433\u0440\u0443\u043f\u043f\u0438\u0440\u043e\u0432\u043a\u0438 \u0437\u0430\u0434\u0430\u0447')),
                ('failed_action', models.CharField(max_length=32, null=True, verbose_name='Action, \u043d\u0430 \u043a\u043e\u0442\u043e\u0440\u043e\u043c \u043f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430')),
                ('retry_count', models.SmallIntegerField(default=0, verbose_name='\u0421\u0447\u0435\u0442\u0447\u0438\u043a \u043f\u043e\u043f\u044b\u0442\u043e\u043a')),
                ('last_retry_dt', models.DateTimeField(null=True, verbose_name='\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u043f\u043e\u043f\u044b\u0442\u043a\u0430 \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e\u0433\u043e \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f')),
                ('max_retry_count', models.IntegerField(null=True, verbose_name='\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435 \u043a\u043e\u043b-\u0432\u043e \u043f\u043e\u043f\u044b\u0442\u043e\u043a \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u043a\u0430 (\u0435\u0441\u043b\u0438 None, \u0442\u043e \u0431\u0435\u0441\u043a\u043e\u043d\u0435\u0447\u043d\u043e)')),
                ('retry_period', models.DurationField(verbose_name='Retry \u043f\u0435\u0440\u0438\u043e\u0434')),
            ],
            options={
                'db_table': 'botmanager_task',
                'verbose_name': '\u0417\u0430\u0434\u0430\u0447\u0430 \u0434\u043b\u044f BotManager',
                'verbose_name_plural': '\u0417\u0430\u0434\u0430\u0447\u0438 \u0434\u043b\u044f BotManager',
            },
        ),
    ]
