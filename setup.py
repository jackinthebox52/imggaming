from setuptools import setup, find_packages

setup(
    name='imggaming',
    version='0.1',
    packages=find_packages(),
    description='A python wrapper for the imggaming api.',
    author='jackinthebox52',
    author_email='jackmassey2000@gmail.com',
    url='https://github.com/jackinthebox52/imggaming',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'requests',
    ],
)