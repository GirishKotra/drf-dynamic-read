"""
For the tests.
"""
from rest_framework import serializers
from .models import Teacher, School
from dynamic_read.serializers import DynamicReadSerializerMixin


class SchoolSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = School
        fields = "__all__"


class TeacherSerializer(DynamicReadSerializerMixin, serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = "__all__"
