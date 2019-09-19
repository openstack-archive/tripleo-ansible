#!/usr/bin/env bash
# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


## Shell Opts ----------------------------------------------------------------

set -o pipefail
set -eu

## Vars ----------------------------------------------------------------------

export PROJECT_DIR="$(dirname $(readlink -f ${BASH_SOURCE[0]}))/../"

## Main ----------------------------------------------------------------------

echo 'Checking for broken symlinks: '
find ${PROJECT_DIR} -type l ! -exec test -e {} \; -print 2>&1 | grep . && exit 1 || (echo clear && exit 0)
