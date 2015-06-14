from setuptools import setup
from os.path import join, dirname

requirements = [
    'wget==2.2',
    'urllib3==1.7.1',
    'convertible==0.13',
    'requests==2.2.1',
    'syncloud-app==0.37'
]

version = open(join(dirname(__file__), 'version')).read().strip()
print(version)

setup(
    name='syncloud-sam',
    version=version,
    install_requires=requirements,
    packages=['syncloud', 'syncloud.sam'],
    namespace_packages=['syncloud'],
    py_modules=['syncloud-sam'],
    author='Syncloud',
    author_email='support@syncloud.it',
    url='https://github.com/syncloud/sam'
)