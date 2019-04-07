from setuptools import setup, find_packages

setup(
    name='riptide_engine_docker',
    version='0.1',
    packages=find_packages(),
    description='TODO',  # TODO
    long_description='TODO',  # TODO
    install_requires=[
        'riptide_lib == 0.1',
        'docker >= 3.5'
    ],
    # TODO
    classifiers=[
        'Programming Language :: Python',
    ],
    entry_points='''
        [riptide.engine]
        docker=riptide_engine_docker.engine:DockerEngine
        [riptide.engine.tests]
        docker=riptide_engine_docker.tests.integration.tester:DockerEngineTester
    ''',
)
