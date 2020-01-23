#!/bin/sh
# Riptide Docker entrypoint script.
#
# Responsible for running some important pre-start operations.
# Afterwards runs the original entrypoint and/or command in (more or less) the same way Docker would.
# The original entrypoint may be specified in the environment variable RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT (see below)
# The original command may be specified by being passed as arguments to this script.
#
# Behaviour is controlled by environment variables.
#
# RIPTIDE__DOCKER_NO_STDOUT_REDIRECT:
#   If set, Riptide will NOT redirect all stdout/stderr output to /riptide_stdout or /riptide_stderr respectively
#
# RIPTIDE__DOCKER_USER:
#   If set, Riptide will try to create a user named "riptide" with this id.
#
# RIPTIDE__DOCKER_GROUP:
#   If this and RIPTIDE__DOCKER_USER are set,
#   Riptide will try to add a group with this id (named riptide; only if not already exists)
#   and add $RIPTIDE__DOCKER_USER to this group.
#
# RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_USER:
#   If set, the original entrypoint and command are run via the RIPTIDE__DOCKER_USER_RUN user using su.
#
# RIPTIDE__DOCKER_USER_RUN:
#   (optional, defaults to RIPTIDE__DOCKER_USER)
#   User id to use for run. If this is different from RIPTIDE__DOCKER_USER, then the user with this id MUST exist.
#
# RIPTIDE__DOCKER_DONT_RUN_CMD:
#   If set, the command is not run, only the original entrypoint/nothing.
#
# RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT:
#   Contains the original entrypoint. Can be empty. Will be run and get the command passed
#   (if RIPTIDE__DOCKER_DONT_RUN_CMD is not set)
#
# RIPTIDE__DOCKER_NAMED_VOLUMES:
#   List of named volume mount paths (separated by :). These will be chowned to RIPTIDE__DOCKER_USER_RUN:RIPTIDE__DOCKER_GROUP.
#
# RIPTIDE__DOCKER_CMD_LOGGING_*:
#   Command logging.
#   All the vlaues of these environment variables will be started and their stdout redirected to /cmd_logs/*.
#
# RIPTIDE__DOCKER_HOST_SYSTEM_HOSTNAMES:
#   List of hostnames to add to the /etc/hosts. These hostnames must be routable to the host
#   system.
#
# RIPTIDE__DOCKER_OVERLAY_TARGETS:
#   Paths at these locations (separated by :), will be mounted via an overlayfs. Paths must be absolute.
#   To do this, the target is first bind-mounted to /riptide_overlayfs/lower and then an overlayfs is created
#   at the position in src with the lower part being the bind mount created in /riptide_overlayfs/lower.
#   Upper and workdirs are created in /riptide_overlayfs/tmp/upper and /riptide_overlayfs/tmp/work respecitively.
#   upper and work are kept in memory using tmpfs. Regular tmpfs restrictions apply.
#
# RIPTIDE__DOCKER_ON_LINUX:
#   "1": Docker is running natively on Linux
#   "0": Docker is running via a Linux VM.

if [ -z "$RIPTIDE__DOCKER_NO_STDOUT_REDIRECT" ]
then
    # redirect stdout and stderr to files
    exec >>/riptide_stdout
    exec 2>>/riptide_stderr
    chmod 666 /riptide_stdout
    chmod 666 /riptide_stderr

    echo="SERVICE RESTART - $(date) - Thank you for using Riptide!"
    echo $echo
    >&2 echo $echo
fi

# Start logging commands, prefixed RIPTIDE__DOCKER_CMD_LOGGING_
env | sed -n "s/^RIPTIDE__DOCKER_CMD_LOGGING_\(\S*\)=.*/\1/p" | while read -r name ; do
    eval "cmd=\${RIPTIDE__DOCKER_CMD_LOGGING_${name}}"
    # XXX: Currently waiting 5sec for service to start, make configurable?
    # The infinite sleep is required, because in some instances, the main command
    #   will exit otherwise if a logging command exits.
    nohup sh -c "sleep 5; ${cmd}; sleep infinity" > /cmd_logs/${name} &
done

# Create user and group
SU_PREFIX=""
SU_POSTFIX=""
if [ ! -z "$RIPTIDE__DOCKER_USER" ]; then
    # ADD GROUP
    if ! grep -q $RIPTIDE__DOCKER_GROUP /etc/group; then
        # groupadd might be called addgroup (alpine)
        if command -v groupadd > /dev/null; then
            groupadd -g $RIPTIDE__DOCKER_GROUP riptide
        else
            addgroup -g $RIPTIDE__DOCKER_GROUP riptide
        fi
    fi
    GROUP_NAME=$(getent group $RIPTIDE__DOCKER_GROUP  | awk -F\: '{ print $1 }' )
    # ADD USER
    if ! getent passwd $RIPTIDE__DOCKER_USER > /dev/null; then
        USERNAME="riptide"
        mkdir /home/riptide -p > /dev/null 2>&1
        chown $RIPTIDE__DOCKER_USER:$RIPTIDE__DOCKER_GROUP /home/riptide -R > /dev/null 2>&1
        # useradd might be called adduser (alpine)
        if command -v useradd > /dev/null; then
            useradd -ms /bin/sh --home-dir /home/riptide -u $RIPTIDE__DOCKER_USER -g $GROUP_NAME riptide 2> /dev/null
        else
            adduser -s /bin/sh -h /home/riptide -u $RIPTIDE__DOCKER_USER -G $GROUP_NAME -D riptide 2> /dev/null
        fi
    else
        # User already exists
        USERNAME=$(getent passwd "$RIPTIDE__DOCKER_USER" | cut -d: -f1)
        HOME_DIR=$(eval echo "~$USERNAME")
        usermod -a -G $RIPTIDE__DOCKER_GROUP $USERNAME 2> /dev/null # usermod might not exist, in this case we are out of luck :(
        # Symlink the other user directory to /home/riptide
        mkdir -p /home
        ln -s $HOME_DIR /home/riptide
        chown $RIPTIDE__DOCKER_USER:$RIPTIDE__DOCKER_GROUP /home/riptide -R > /dev/null 2>&1
    fi
    # Set the RIPTIDE__DOCKER_USER_RUN if unset
    if [ -z "$RIPTIDE__DOCKER_USER_RUN" ]; then
        RIPTIDE__DOCKER_USER_RUN=$RIPTIDE__DOCKER_USER
    fi
fi

# Chown all provided volume paths
OLD_IFS=$IFS
IFS=':'
for p in $RIPTIDE__DOCKER_NAMED_VOLUMES; do
  if [ ! -z "$RIPTIDE__DOCKER_GROUP" ]; then
    chown $RIPTIDE__DOCKER_USER_RUN:$RIPTIDE__DOCKER_GROUP $p
  else
    chown $RIPTIDE__DOCKER_USER_RUN $p
  fi
done
IFS=$OLD_IFS

# Apply overlayfs settings
apply_overlayfs() {
    mkdir /riptide_overlayfs
    mkdir /riptide_overlayfs/tmp
    mkdir /riptide_overlayfs/tmp/upper
    mkdir /riptide_overlayfs/tmp/work
    mount -t tmpfs none "/riptide_overlayfs/tmp"
    OLD_IFS=$IFS
    IFS=':'
    for p in $1; do
        if [ -d "$p" ]; then
            l="/riptide_overlayfs/lower$p"
            u="/riptide_overlayfs/tmp/upper$p"
            w="/riptide_overlayfs/tmp/work$p"
            mkdir -p "$l"
            mkdir -p "$u"
            mkdir -p "$w"
            mount --bind "$p" "$l"
            mount -t overlay overlay -o "lowerdir=$l,upperdir=$u,workdir=$w" $p
            # Because of the weird osxfs under Mac and propably also under Windows,
            # we have to properly set all permissions for these subdirectories
            RECURSIVE_FLAG=""
            if [ ! "$RIPTIDE__DOCKER_ON_LINUX" = "1" ]; then
              RECURSIVE_FLAG="-R"
            fi
            if [ ! -z "$RIPTIDE__DOCKER_GROUP" ]; then
              chown $RIPTIDE__DOCKER_USER_RUN:$RIPTIDE__DOCKER_GROUP $p $RECURSIVE_FLAG
            else
              chown $RIPTIDE__DOCKER_USER_RUN $p $RECURSIVE_FLAG
            fi
        fi
    done
    IFS=$OLD_IFS
}
if [ ! -z "$RIPTIDE__DOCKER_OVERLAY_TARGETS" ]; then
    apply_overlayfs $RIPTIDE__DOCKER_OVERLAY_TARGETS
fi

# PREPARE SU COMMAND AND ENV
if [ ! -z "$RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_USER" ]; then
    USERNAME=$(getent passwd "$RIPTIDE__DOCKER_USER_RUN" | cut -d: -f1)
    SU_PREFIX="su $USERNAME -m -c '"
    SU_POSTFIX="'"
    export HOME=/home/riptide
fi

# host.riptide.internal is supposed to be routable to the host.
if [ "$RIPTIDE__DOCKER_ON_LINUX" = "1" ]; then
    # TODO Resolve IP dynamically
    POSSIBLE_IP="172.17.0.1"
else
    LOOP=0
    while [ -z "$POSSIBLE_IP" ]; do
        POSSIBLE_IP="$(getent hosts host.docker.internal | awk '{ print $1 }')"
        LOOP=$(expr $LOOP + 1)
        if [ "$LOOP" = "10" ]; then
            echo "Riptide: Trying to determine host IP address... this is taking way longer than it should..."
        fi
        if [ "$LOOP" = "100" ]; then
            echo "Riptide: Failed to determine host IP address... giving up. The container might not be able to reach the host system!"
            POSSIBLE_IP="172.17.0.1"
        fi
    done
fi

# Add all host entries passed in to the /etc/hosts file
if [ ! -z "$RIPTIDE__DOCKER_HOST_SYSTEM_HOSTNAMES" ]; then
    echo "$POSSIBLE_IP  $RIPTIDE__DOCKER_HOST_SYSTEM_HOSTNAMES" >> /etc/hosts
fi

# ENV_PATH = PATH to make it consistent with the default Docker API
echo "
ENV_PATH PATH=$PATH
" > /etc/login.defs

# Wait just a little while... this has to do with some
# fun race conditions in resolving host names for commands
# because of adding the container to a network AFTER it's been started.
sleep 0.05

# Run original entrypoint and/or cmd
if [ -z "RIPTIDE__DOCKER_DONT_RUN_CMD" ]; then
    # Run entrypoint only directly
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $SU_POSTFIX
else
    # Run entrypoint (if exists) and command
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $@ $SU_POSTFIX
fi
