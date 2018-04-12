#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='django-botmanager',
    version='0.0.6',
    description='Async tasks for django',
    author='Dimoha',
    author_email='dimoha@controlstyle.ru',
    url='https://github.com/dimoha/django-botmanager',
    install_requires=[
        "Django>=1.9.1",
        "setproctitle==1.1.10",
        "jsonfield==1.0.3"
    ],
    packages=find_packages(),
)