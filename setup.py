from setuptools import find_packages, setup

from pip.req import parse_requirements

from pedant import __version__


setup(
    name='counsyl-django-pedant',
    version=__version__,
    author='Lucas Wiman',
    author_email='lucaswiman@counsyl.com',
    maintainer='Counsyl',
    maintainer_email='root@counsyl.com',
    description='Make django templates fail fast on errors',
    long_description=open('README.md', 'r').read(),
    url='https://github.counsyl.com/lucaswiman/django-pedant',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        str(ir.req) for ir in parse_requirements('./requirements.txt')],
    zip_safe=False,
)
