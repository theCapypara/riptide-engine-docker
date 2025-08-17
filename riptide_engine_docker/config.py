import os

ENV_DOCKER_DEFAULT_PLATFORM = "DOCKER_DEFAULT_PLATFORM"


def get_image_platform() -> str | None:
    """Get the configured image platform to use, reads env variable DOCKER_DEFAULT_PLATFORM"""
    if ENV_DOCKER_DEFAULT_PLATFORM in os.environ:
        return os.environ[ENV_DOCKER_DEFAULT_PLATFORM]
    return None
