|Riptide|
=========

.. |Riptide| image:: https://riptide-docs.readthedocs.io/en/latest/_images/logo.png
    :alt: Riptide

.. class:: center

    ===================  ===================  ===================  ===================
    *Main packages:*     lib_                 proxy_               cli_
    *Engine-Backends:*   **engine_docker**
    *Database Drivers:*  db_mysql_
    *Related Projects:*  configcrunch_
    *More:*              docs_                repo_
    ===================  ===================  ===================  ===================

.. _lib:            https://github.com/Parakoopa/riptide-lib
.. _cli:            https://github.com/Parakoopa/riptide-cli
.. _proxy:          https://github.com/Parakoopa/riptide-proxy
.. _configcrunch:   https://github.com/Parakoopa/configcrunch
.. _engine_docker:  https://github.com/Parakoopa/riptide-engine-docker
.. _db_mysql:       https://github.com/Parakoopa/riptide-db-mysql
.. _docs:           https://github.com/Parakoopa/riptide-docs
.. _repo:           https://github.com/Parakoopa/riptide-repo

|build| |integration| |docs|

.. |build| image:: http://jenkins.riptide.parakoopa.de:8080/buildStatus/icon?job=riptide-engine-docker%2Fmaster
    :target: http://jenkins.riptide.parakoopa.de:8080/blue/organizations/jenkins/riptide-engine-docker/activity
    :alt: Build Status (Unit & Deployment)

.. |integration| image:: http://jenkins.riptide.parakoopa.de:8080/buildStatus/icon?subject=integration&job=riptide-lib%2Fmaster
    :target: http://jenkins.riptide.parakoopa.de:8080/blue/organizations/jenkins/riptide-lib/activity
    :alt: Build Status (Integration)

.. |docs| image:: https://readthedocs.org/projects/riptide-docs/badge/?version=latest
    :target: https://riptide-docs.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Riptide is a set of tools to manage development environments for web applications.
It's using container virtualization tools, such as `Docker <https://www.docker.com/>`_
to run all services needed for a project.

It's goal is to be easy to use by developers.
Riptide abstracts the virtualization in such a way that the environment behaves exactly
as if you were running it natively, without the need to install any other requirements
the project may have.

Engine-Backend: Docker
----------------------

This repository implements the Riptide engine backend by using the Docker container engine.

It uses both the Docker API and the Docker CLI to communicate with Docker. The Docker Host must be installed and
running on the same machine as Riptide. The Docker CLI must also be installed.

It can be installed via pip by installing ``riptide_engine_docker``.

Tests
-----

Inside the riptide_engine_docker.tests package are unit tests for the engine backend.

``riptide_engine_docker.tests.integration`` contains an implementation of the integration
test interface used by the Riptide lib package. To run integration tests for the engine backend,
run the Riptide lib integration tests with this backend installed.

Documentation
-------------

The complete documentation for Riptide can be found at `Read the Docs <https://riptide-docs.readthedocs.io/en/latest/>`_.