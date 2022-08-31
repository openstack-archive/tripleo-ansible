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


def set_proper_molecule_config(role_path, scenario='default'):
    mol_config_file = "config.yml"
    if os.path.exists(os.path.join(role_path, 'molecule',
                      f'{scenario}/molecule.yml')):
        molecule_path = os.path.join(
            role_path, 'molecule', f'{scenario}/molecule.yml')
        with open(molecule_path) as content:
            data = yaml.safe_load(content)
        if 'driver' in data.keys() and data['driver']['name'] == 'podman':
            mol_config_file = "config_podman.yml"

    root_path = os.path.dirname(os.path.abspath(__file__)).split('/tests')[0]
    mol_config = os.path.join(root_path, '.config/molecule', mol_config_file)
    return mol_config


def set_molecule_tags(role_path, scenario='default'):
    mol_tags = []
    if os.path.exists(os.path.join(role_path, 'molecule',
                                   f'{scenario}/test_vars.yml')):
        test_vars_path = os.path.join(role_path, 'molecule',
                                      f'{scenario}/test_vars.yml')
        with open(test_vars_path) as content:
            data = yaml.safe_load(content)

        if not data:
            return []
        if ('test_skip_tags' in data.keys() and data['test_skip_tags']
           and data.get('molecule_skip_tags_enforce', True)):
            mol_tags.append('--skip-tags')
            if type(data['test_skip_tags']) == str:
                mol_tags.append(data['test_skip_tags'])
            elif type(data['test_skip_tags']) == list:
                mol_tags.append(",".join(data['test_skip_tags']))

        if ('test_tags' in data.keys() and data['test_tags']
           and data.get('molecule_tags_enforce', True)):
            mol_tags.append('--tags')
            if type(data['test_tags']) == str:
                mol_tags.append(data['test_tags'])
            elif type(data['test_tags']) == list:
                mol_tags.append(",".join(data['test_tags']))
        return mol_tags


def run_molecule(pytestconfig, scenario=None):
    cmd = ['python', '-m', 'molecule']
    if not scenario:
        scenario = 'default'
    ansible_args = pytestconfig.getoption("ansible_args")
    cmd.extend(['--base-config', set_proper_molecule_config(os.getcwd(),
                                                            scenario)])

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

    alltags = set_molecule_tags(os.getcwd(), scenario)
    if alltags:
        if '--' not in cmd:
            cmd.append('--')
        cmd.extend(alltags)

    try:
        assert subprocess.call(cmd) == 0
    finally:
        if ansible_args:
            cmd = ['python', '-m', 'molecule', 'destroy']
            cmd.extend(['--base-config',
                        set_proper_molecule_config(os.getcwd())])
            if scenario:
                cmd.extend(['--scenario-name', scenario])
            subprocess.call(cmd)


def get_molecule_scenario(role_path):
    mol_scenario = []
    if os.path.exists(os.path.join(role_path, 'molecule')):
        mol_dir = os.path.join(role_path, 'molecule')
        dirs = os.listdir(mol_dir)
        mol_scenario = [d for d in dirs if os.path.exists(
            os.path.join(mol_dir, d, 'molecule.yml'))]
        return mol_scenario


def test_molcule(pytestconfig):
    scenarios = get_molecule_scenario(os.getcwd())
    for scenario in scenarios:
        run_molecule(pytestconfig, scenario)
