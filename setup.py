from setuptools import setup, find_packages

setup(
    name='riptide_engine_docker',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    description='TODO',  # TODO
    long_description='TODO - Project will be available starting May/June',  # TODO
    install_requires=[
        'riptide_lib == 0.1',
        'docker >= 3.5'
    ],
    # TODO
    classifiers=[
        'Development Status :: 4 - Beta',
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
