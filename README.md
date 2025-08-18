<h1>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://riptide-docs.readthedocs.io/en/latest/_images/logo_dark.png">
  <img alt="Riptide" src="https://riptide-docs.readthedocs.io/en/latest/_images/logo.png" width="300">
</picture>
</h1>

[<img src="https://img.shields.io/github/actions/workflow/status/theCapypara/riptide-engine-docker/build.yml" alt="Build Status">](https://github.com/theCapypara/riptide-engine-docker/actions)
[<img src="https://readthedocs.org/projects/riptide-docs/badge/?version=latest" alt="Documentation Status">](https://riptide-docs.readthedocs.io/en/latest/)
[<img src="https://img.shields.io/pypi/v/riptide-engine-docker" alt="Version">](https://pypi.org/project/riptide-engine-docker/)
[<img src="https://img.shields.io/pypi/dm/riptide-engine-docker" alt="Downloads">](https://pypi.org/project/riptide-engine-docker/)
<img src="https://img.shields.io/pypi/l/riptide-engine-docker" alt="License (MIT)">
<img src="https://img.shields.io/pypi/pyversions/riptide-engine-docker" alt="Supported Python versions">

Riptide is a set of tools to manage development environments for web applications.
It's using container virtualization tools, such as [Docker](https://www.docker.com/)
to run all services needed for a project.

Its goal is to be easy to use by developers.
Riptide abstracts the virtualization in such a way that the environment behaves exactly
as if you were running it natively, without the need to install any other requirements
the project may have.

Riptide consists of a few repositories, find the
entire [overview](https://riptide-docs.readthedocs.io/en/latest/development.html) in the documentation.

## Engine-Backend: Docker

This repository implements the Riptide engine backend by using the Docker container engine.

It uses both the Docker API and the Docker CLI to communicate with Docker. The Docker Host must be installed and
running on the same machine as Riptide. The Docker CLI must also be installed.

It can be installed via pip by installing `riptide-engine-docker`.

## Tests

Inside the riptide_engine_docker.tests package are unit tests for the engine backend.

`riptide_engine_docker.tests.integration` contains an implementation of the integration
test interface used by the Riptide lib package. To run integration tests for the engine backend,
run the Riptide lib integration tests with this backend installed.

## Documentation

The complete documentation for Riptide can be found at [Read the Docs](https://riptide-docs.readthedocs.io/en/latest/).
