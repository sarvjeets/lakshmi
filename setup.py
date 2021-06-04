from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
  name='Lakshmi',
  version='1.0.0',
  author='Sarvjeet Singh',
  author_email='sarvjeet@gmail.com',
  description='Investing Tools.',
  long_description=long_description,
  long_description_content_type="text/markdown",
  url='https://github.com/sarvjeets/Lakshmi',
  install_requires=[
    'click~=8.0.1',
    'PyYAML~=5.4.1',
    'requests~=2.25.1',
    'tabulate~=0.8.9',
    'yfinance~=0.1.59',
  ],
  python_requires=">=3.9.6",
)