# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tripleo_ansible.ansible_plugins.modules import tripleo_diff_exec
from tripleo_ansible.tests import base as tests_base
from unittest import mock


class TestTripleoDiffExec(tests_base.TestCase):
    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_first_run(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'environment': {'foo': 'bar'},
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.side_effect = [True, False]
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        mock_return = mock.MagicMock()
        mock_return.returncode = 0
        mock_run.return_value = mock_return
        tripleo_diff_exec.run(mock_module)
        mock_exit.assert_called_once_with(changed=True)
        mock_run.assert_called_once_with(
            'foo', shell=True, env={'foo': 'bar'}, stderr=-1, stdout=-1,
            universal_newlines=True)
        mock_copy2.assert_called_with('/tmp/foo', '/tmp/foo-previous')

    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_no_change(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.return_value = True
        mock_cmp.return_value = True
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        tripleo_diff_exec.run(mock_module)
        self.assertEqual(mock_run.call_count, 0)
        self.assertEqual(mock_copy2.call_count, 0)
        mock_exit.assert_called_once_with(changed=False)

    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_file_changed(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.return_value = True
        mock_cmp.return_value = False
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        mock_return = mock.MagicMock()
        mock_return.returncode = 0
        mock_run.return_value = mock_return
        tripleo_diff_exec.run(mock_module)
        mock_run.assert_called_once_with(
            'foo', shell=True, env={}, stderr=-1, stdout=-1,
            universal_newlines=True)
        mock_copy2.assert_called_with('/tmp/foo', '/tmp/foo-previous')
        mock_exit.assert_called_once_with(changed=True)

    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_missing_state(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.return_value = False
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        tripleo_diff_exec.run(mock_module)
        mock_exit.assert_called_once_with(changed=False,
                                          error='Missing state file',
                                          failed=True,
                                          msg=('State file does not exist: '
                                               '/tmp/foo'))

    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_exec_exception(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.side_effect = [True, False]
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        mock_run.side_effect = Exception('meh')
        tripleo_diff_exec.run(mock_module)
        mock_exit.assert_called_once_with(changed=False,
                                          error=mock.ANY,
                                          failed=True,
                                          msg='Unhandled exception: meh')

    @mock.patch.dict('os.environ', dict(), clear=True)
    @mock.patch('shutil.copy2')
    @mock.patch('subprocess.run')
    @mock.patch('filecmp.cmp')
    @mock.patch('os.path.exists')
    def test_exec_failed(self, mock_exists, mock_cmp, mock_run, mock_copy2):
        mock_module = mock.MagicMock()
        mock_module.params = {
            'command': 'foo',
            'return_codes': [0],
            'state_file': '/tmp/foo',
            'state_file_suffix': '-previous'
        }
        mock_exists.side_effect = [True, False]
        mock_exit = mock.MagicMock()
        mock_module.exit_json = mock_exit
        mock_return = mock.MagicMock()
        mock_return.returncode = 1
        mock_return.stdout = 'out'
        mock_return.stderr = 'err'
        mock_run.return_value = mock_return
        tripleo_diff_exec.run(mock_module)
        mock_exit.assert_called_once_with(
            changed=False, error='Failed running command', failed=True,
            msg=('Error running foo. rc: 1, stdout: out, stderr: err'))
