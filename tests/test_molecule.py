# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess

import pytest
import yaml

BASECMD = ['python', '-m', 'molecule']


def set_proper_molecule_config(role_path):
    mol_config_file = "config.yml"
    if os.path.exists(os.path.join(role_path, 'molecule', 'default/molecule.yml')):
        molecule_path = os.path.join(role_path, 'molecule', 'default/molecule.yml')
        with open(molecule_path) as content:
            data = yaml.safe_load(content)
        if 'driver' in data.keys() and data['driver']['name'] == 'podman':
            mol_config_file = "config_podman.yml"

    root_path = os.path.dirname(os.path.abspath(__file__)).split('/tests')[0]
    mol_config = os.path.join(root_path, '.config/molecule', mol_config_file)
    return mol_config


def test_molecule(pytestconfig):
    cmd = BASECMD
    cmd.extend(['--base-config', set_proper_molecule_config(os.getcwd())])
    scenario = pytestconfig.getoption("scenario")
    ansible_args = pytestconfig.getoption("ansible_args")

    if ansible_args:
        cmd.append('converge')
        if scenario:
            cmd.extend(['--scenario-name', scenario])
        cmd.append('--')
        cmd.extend(ansible_args.split())
    else:
        cmd.append('test')
        if scenario:
            cmd.extend(['--scenario-name', scenario])
        else:
            cmd.append('--all')

    try:
        assert subprocess.call(cmd) == 0
    finally:
        if ansible_args:
            cmd = BASECMD
            cmd.extend(['--base-config', set_proper_molecule_config(os.getcwd())])
            cmd.append('destroy')
            if scenario:
                cmd.extend(['--scenario-name', scenario])
            subprocess.call(cmd)
