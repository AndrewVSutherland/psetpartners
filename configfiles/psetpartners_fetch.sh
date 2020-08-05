#!/usr/bin/env bash
date

for branch in master test; do
  if [ -d "/home/psetpartners/psetpartners-git-${branch}" ]; then
    pushd /home/psetpartners/psetpartners-git-$branch
    git fetch
    git checkout origin/$branch -f
    git submodule update
    popd
  fi
done
