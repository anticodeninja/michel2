from setuptools import setup, find_packages

setup(
    name='michel-orgmode',
    version='0.1.0',
    maintainer='Mark Edgington',
    maintainer_email='edgimar@gmail.com',
    packages=find_packages(),
    url='https://bitbucket.org/edgimar/michel-orgmode',
    license=open('LICENSE.txt').read(),
    description='push/pull an org-mode file to a google-tasks task-list',
    long_description=open('README.md').read(),
    install_requires = ['google-api-python-client', 'pyxdg'],
    entry_points=("""
    [console_scripts]
    michel-orgmode = michel.michel:main
    """)
)
