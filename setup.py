# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function
from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

here = path.abspath(path.dirname(__file__))

if sys.version_info < (3, 3):
    print('Sorry, only python>=3.3 is supported', file=sys.stderr)
    sys.exit(1)

with open(path.join(here, 'LICENSE.txt'), encoding='utf-8') as f:
    license = f.read()
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='michel2',
    version='0.8.0',

    description='push/pull/sync an org-mode file to other task-list systems',
    long_description=long_description,

    url='https://github.com/anticodeninja/michel2',

    maintainer='anticodeninja',
    author='anticodeninja',

    license=license,

    packages=find_packages(),
    install_requires=[
        'google-api-python-client',
        'oauth2client'
    ],
    python_requires='>=3.3',

    entry_points={
        'console_scripts' : [
            'michel=michel:main',
        ],
    },
)
