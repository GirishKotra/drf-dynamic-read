from setuptools import setup

with open("README.rst", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='drf_dynamic_read',
    version='0.1.1',
    description='A utility to improve and optimise read operations(querying and serialization of data) for Django Rest Framework based applications',
    author='Girish Kotra',
    author_email='girish934@gmail.com',
    url='https://github.com/GirishKotra/drf-dynamic-read',
    packages=['drf_dynamic_read'],
    zip_safe=True,
    include_package_data=True,
    license='MIT',
    keywords='drf restframework rest_framework django_rest_framework serializers',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    python_requires=">=3.6",
    install_requires=[
        "Django>=1.11.16",
        "djangorestframework>=3.6.4"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Environment :: Web Environment',
    ],
)
