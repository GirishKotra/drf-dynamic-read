"""
Some models for the tests. We are modelling a school.
"""
from django.db import models


class School(models.Model):
    """Schools just have teachers, no students."""
    name = models.CharField(max_length=500)


class Teacher(models.Model):
    """No fields, no fun."""
    school = models.ForeignKey(School, on_delete=models.SET_NULL)
