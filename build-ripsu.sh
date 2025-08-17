#!/bin/sh
set -e

cd "$(dirname "$0")/riptide_engine_docker/assets/ripsu"

build() {
  plat=$1
  nixexpr=$2

  nix run "nixpkgs#pkgsCross.$2.pkgsStatic.stdenv.cc" -- -static \
      -Os -s \
      -fno-stack-protector -fomit-frame-pointer -ffunction-sections -fdata-sections -Wl,--gc-sections \
      -fno-unwind-tables -fno-asynchronous-unwind-tables \
      -fno-math-errno -fno-unroll-loops -fmerge-all-constants \
      -fno-ident -Wl,-z,norelro \
      -W -Wall -Wextra -Werror -pedantic \
      ripsu.c \
      -o ripsu-$1
  chmod +x ripsu-$1
  ls -lah ripsu-$1
  file ripsu-$1
}

build amd64 musl64
build arm64 aarch64-multiplatform-musl
