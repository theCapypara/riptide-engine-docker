from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

setup(
    name='riptide_engine_docker',
    version='0.1.1',
    packages=find_packages(),
    include_package_data=True,
    description='Tool to manage development environments for web applications using containers - Docker Implementation',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/Parakoopa/riptide-engine-docker/',
    install_requires=[
        'riptide_lib >= 0.1, < 0.2',
        'docker >= 3.5'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points='''
        [riptide.engine]
        docker=riptide_engine_docker.engine:DockerEngine
        [riptide.engine.tests]
        docker=riptide_engine_docker.tests.integration.tester:DockerEngineTester
    ''',
)
