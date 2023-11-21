#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='django-botmanager',
    version='0.2.17',
    description='Async tasks for django',
    author='Dimoha',
    author_email='dimoha@controlstyle.ru',
    url='https://github.com/dimoha/django-botmanager',
    install_requires=[
        "setproctitle==1.1.10",
        "jsonfield==3.1.0",
        "psutil==5.8.0"
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['locale/*/LC_MESSAGES/*.mo', 'locale/*/LC_MESSAGES/*.po'],
    }
)