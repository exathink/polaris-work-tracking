# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2016) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from setuptools import setup
from os import path

# Suppose the package you are build is called polaris.x.y.z

# First create a package directory called polaris/x/y/z with a valid
# __init__.py in it. This is a Python 3 Namespace Package.

# UNCOMMENT 'import' line and import the name of the package you are defining.

import polaris.work_tracking

here = path.abspath(path.dirname(__file__))


setup(

    name='polaris.work_tracking',


    version=polaris.work_tracking.__version__,


    packages=[
        'polaris',
        'polaris.work_tracking',
        'polaris.work_tracking.db',
        'polaris.work_tracking.integrations',
        'polaris.work_tracking.integrations.atlassian',
        'polaris.work_tracking.service',
        'polaris.work_tracking.messages',
        'polaris.work_tracking.service.graphql'
    ],

    url='',
    license = 'Commercial',
    author='Krishna Kumar',
    author_email='kkumar@exathink.com',
    description='',
    long_description='',
    classifiers=[
        'Programming Language :: Python :: 3.5'
    ],
    # Run time dependencies - we will assume pytest is dependency of all packages.
    install_requires=[
        'pytest'
    ]
)
