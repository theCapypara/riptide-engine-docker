#define _GNU_SOURCE
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pwd.h>
#include <string.h>

int main(int argc, char **argv)
{
    uid_t userid, groupid;
    char* username;

    if(argc < 3)
    {
        fprintf(stderr, "Usage: ripsu <user> <cmd> [arg0 [...]]\n");
        exit(1);
    }
    else
    {
        while (1) {
            struct passwd *user = getpwent();
            if (!user) {
                fprintf(stderr, "Riptide: ripsu: user not found\n");
                endpwent();
                exit(1);
            }
            if (strcmp(user->pw_name, argv[1]) == 0) {
                username = user->pw_name;
                userid = user->pw_uid;
                groupid = user->pw_gid;
                endpwent();
                break;
            }
        }
    }

    if(initgroups (username, groupid) == -1)
    {
        perror("Riptide: ripsu: couldn't set group list");
        exit(1);
    }
    endgrent();
    if(setregid(groupid, groupid) != 0)
    {
        perror("Riptide: ripsu: couldn't set gid");
        exit(1);
    }
    if(setreuid(userid, userid) != 0)
    {
        perror("Riptide: ripsu: couldn't set uid");
        exit(1);
    }

    if(execvp(argv[2], argv + 2) == -1)
        perror("Riptide: ripsu: exec failed");
    else
        fprintf(stderr, "Riptide: ripsu: exec returned\n");

    return 1;
}