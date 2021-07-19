#!/usr/bin/env python
# -*- coding: utf-8

import os
import django
from django.core.management import call_command

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'  # noqa


def initalize(*test_args):
    django.setup()
    call_command("makemigrations")
    call_command("migrate")
    call_command("makemigrations", "tests")
    call_command("migrate", "tests")


def run_tests():
    pass


if __name__ == '__main__':
    initalize()
    run_tests()
