|Riptide|
=========

.. |Riptide| image:: https://riptide-docs.readthedocs.io/en/latest/_images/logo.png
    :alt: Riptide

.. class:: center

    ======================  ===================  ===================  ===================
    *Main packages:*        lib_                 proxy_               cli_
    *Container-Backends:*   **engine_docker**
    *Database Drivers:*     db_mysql_            db_mongo_
    *Plugins:*              php_xdebug_
    *Kubernetes:*           k8s_client_          k8s_controller_
    *Related Projects:*     configcrunch_
    *More:*                 docs_                repo_                docker_images_
    ======================  ===================  ===================  ===================

.. _lib:            https://github.com/theCapypara/riptide-lib
.. _cli:            https://github.com/theCapypara/riptide-cli
.. _proxy:          https://github.com/theCapypara/riptide-proxy
.. _configcrunch:   https://github.com/theCapypara/configcrunch
.. _engine_docker:  https://github.com/theCapypara/riptide-engine-docker
.. _db_mysql:       https://github.com/theCapypara/riptide-db-mysql
.. _db_mongo:       https://github.com/theCapypara/riptide-db-mongo
.. _docs:           https://github.com/theCapypara/riptide-docs
.. _repo:           https://github.com/theCapypara/riptide-repo
.. _docker_images:  https://github.com/theCapypara/riptide-docker-images
.. _php_xdebug:     https://github.com/theCapypara/riptide-plugin-php-xdebug
.. _k8s_client:     https://github.com/theCapypara/riptide-k8s-client
.. _k8s_controller: https://github.com/theCapypara/riptide-k8s-controller

|build| |docs| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions|

.. |build| image:: https://img.shields.io/github/actions/workflow/status/theCapypara/riptide-engine-docker/build-test-publish.yml
    :target: https://github.com/theCapypara/riptide-engine-docker/actions
    :alt: Build Status

.. |docs| image:: https://readthedocs.org/projects/riptide-docs/badge/?version=latest
    :target: https://riptide-docs.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |pypi-version| image:: https://img.shields.io/pypi/v/riptide-engine-docker
    :target: https://pypi.org/project/riptide-engine-docker/
    :alt: Version

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/riptide-engine-docker
    :target: https://pypi.org/project/riptide-engine-docker/
    :alt: Downloads

.. |pypi-license| image:: https://img.shields.io/pypi/l/riptide-engine-docker
    :alt: License (MIT)

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/riptide-engine-docker
    :alt: Supported Python versions

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

It can be installed via pip by installing ``riptide-engine-docker``.

Tests
-----

Inside the riptide_engine_docker.tests package are unit tests for the engine backend.

``riptide_engine_docker.tests.integration`` contains an implementation of the integration
test interface used by the Riptide lib package. To run integration tests for the engine backend,
run the Riptide lib integration tests with this backend installed.

Documentation
-------------

The complete documentation for Riptide can be found at `Read the Docs <https://riptide-docs.readthedocs.io/en/latest/>`_.