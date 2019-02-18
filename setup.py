from setuptools import setup, find_packages

setup(
    name='riptide_engine_docker',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # TODO
    ],
    entry_points='''
        [riptide.engine]
        docker=riptide_engine_docker.engine:DockerEngine
        [riptide.engine.tests]
        docker=riptide_engine_docker.tests.integration.tester:DockerEngineTester
    ''',
)