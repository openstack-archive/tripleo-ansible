#!/bin/bash
set -euxo pipefail
# Used by Zuul CI to perform extra bootstrapping

# Workaround for a potential:
# Got permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
# See https://docs.docker.com/install/linux/linux-postinstall/
newgrp docker || true
