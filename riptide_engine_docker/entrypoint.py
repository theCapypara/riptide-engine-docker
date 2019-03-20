from riptide_engine_docker.constants import EENV_DONT_RUN_CMD, EENV_ORIGINAL_ENTRYPOINT


def parse_entrypoint(entrypoint):
    """
    Parse the original entrypoint of an image and return a map of variables for the riptide entrypoint script.
    RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT: Original entrypoint as string to be used with exec.
                                         Empty if original entrypoint is not set.
    RIPTIDE__DOCKER_DONT_RUN_CMD:        true or unset.
                                         When the original entrypoint is a string, the command does not get run.
                                         See table at https://docs.docker.com/engine/reference/builder/#shell-form-entrypoint-example
    """
    # Is the original entrypoint set?
    if not entrypoint:
        return {EENV_ORIGINAL_ENTRYPOINT: ""}
    # Is the original entrypoint shell or exec format?
    if isinstance(entrypoint, list):
        # exec format
        # Turn the list into a string, but quote all arguments
        command = entrypoint.pop(0)
        arguments = " ".join(['"%s"' % entry for entry in entrypoint])
        return {
            EENV_ORIGINAL_ENTRYPOINT: command + " " + arguments
        }
    else:
        # shell format
        return {
            EENV_ORIGINAL_ENTRYPOINT: "/bin/sh -c " + entrypoint,
            EENV_DONT_RUN_CMD: "true"
        }
    pass