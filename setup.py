#!/usr/bin/env python
from setuptools import find_packages, setup

from django_x509 import get_version

def get_install_requires():
    """Parse requirements.txt, ignore links, exclude comments"""
    requirements = []
    with open('requirements.txt') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or line == '' or line.startswith('http') or line.startswith('git'):
                continue
            requirements.append(line)
    return requirements

setup(
    name='mywifipass',
    version=get_version(),
    license='BSD',
    author='Pablo Diz de la Cruz',
    description='MyWifiPass - Backend de gestión de certificados para TFG (Fork simplificado de django-x509)',
    packages=find_packages(exclude=['tests', 'docs']),
    include_package_data=True,
    zip_safe=False,
    install_requires=get_install_requires(),
)
