# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2017-02-17 01:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('botmanager', '0005_task_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='priority',
            field=models.SmallIntegerField(default=0),
        ),
    ]
