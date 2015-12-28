from setuptools import setup
from os.path import join, dirname

requirements = [
    'urllib3==1.7.1',
    'syncloud-lib==2'
]

version = open(join(dirname(__file__), 'version')).read().strip()
print(version)

setup(
    name='syncloud-sam',
    version=version,
    install_requires=requirements,
    packages=['syncloud_sam'],
    author='Syncloud',
    author_email='support@syncloud.it',
    url='https://github.com/syncloud/sam'
)