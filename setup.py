from setuptools import setup

readme = open('README.rst').read()

setup(
    name='drf_dynamic_read',
    version='0.0.1a',
    description='A utility to improve and optimise read operations(querying and serialization of data) for Django Rest Framework based applications',
    author='Girish Kotra',
    author_email='girish934@gmail.com',
    url='https://github.com/GirishKotra/drf-dynamic-read',
    packages=['drf_dynamic_read'],
    zip_safe=True,
    include_package_data=True,
    license='MIT',
    keywords='drf restframework rest_framework django_rest_framework serializers',
    long_description=readme,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Environment :: Web Environment',
    ],
)
