from setuptools import find_packages, setup

from lakshmi.constants import NAME, VERSION

with open('README.md', 'r', encoding='utf-8') as fh:
    # Replace relative links to absolute links.
    long_description = (
        fh.read()
        .replace('](./', '](https://sarvjeets.github.io/lakshmi/')
        .replace('lak.md', 'lak.html'))

setup(
    name=NAME,
    version=VERSION,
    author='Sarvjeet Singh',
    author_email='sarvjeet@gmail.com',
    description=('Investing library and command-line interface '
                 'inspired by the Bogleheads philosophy'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sarvjeets/lakshmi',
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
    py_modules=['lakshmi'],
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=[
        'click~=8.0',
        'PyYAML~=5.4',
        'requests~=2.25',
        'tabulate~=0.8',
        'yfinance~=0.1',
    ],
    entry_points={
        'console_scripts': [
            'lak = lakshmi.lak:lak',
        ],
    },
    test_suite='tests',
    python_requires='>=3.9.5',
)
