# `ripsu`

`ripsu` is a tiny static su-like command that executes a command as another user. It is very basic
and not generally secure. It is only suitable for use in Riptide's entrypoint (../entrypoint.sh).

Usage: `ripsu USER ...`, where `...` is the command to execute and its arguments. `USER` must be the username.

This is based on `static-sudo` by `remram44`, licensed under MIT:
https://github.com/remram44/static-sudo/blob/master/LICENSE.txt
