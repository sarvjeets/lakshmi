from setuptools import setup, find_packages
from lakshmi.constants import NAME, VERSION

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name=NAME,
    version=VERSION,
    author='Sarvjeet Singh',
    author_email='sarvjeet@gmail.com',
    description='Investing Tools.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sarvjeets/lakshmi',
    platforms='any',
    py_modules=['lakshmi'],
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=[
        'click~=8.0.1',
        'PyYAML~=5.4.1',
        'requests~=2.25.1',
        'tabulate~=0.8.9',
        'yfinance~=0.1.59',
    ],
    entry_points={
        'console_scripts': [
            'lak = lakshmi.lak:lak',
        ],
    },
    test_suite='tests',
    python_requires='>=3.9.5',
)
