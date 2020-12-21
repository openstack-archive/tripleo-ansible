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

from tripleo_ansible.ansible_plugins.modules import tripleo_deploy_artifacts
from tripleo_ansible.tests import base as tests_base

from unittest import mock


class TestTripleoDeployArtifacts(tests_base.TestCase):
    @mock.patch('tripleo_ansible.ansible_plugins.modules.'
                'tripleo_deploy_artifacts.deploy_targz')
    @mock.patch('tripleo_ansible.ansible_plugins.modules.'
                'tripleo_deploy_artifacts.deploy_rpm')
    @mock.patch('tripleo_ansible.ansible_plugins.modules.'
                'tripleo_deploy_artifacts._get_filetype')
    @mock.patch('urllib.request.urlretrieve')
    def test_run(self, mock_urlretrieve, mock_filetype, mock_rpm, mock_tgz):
        module = mock.MagicMock()
        module.params = {'artifact_urls': ['myrpm', 'mytgz']}
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        mock_filetype.side_effect = ['rpm', 'targz']
        mock_urlretrieve.side_effect = [('foo', None), ('bar', None)]
        tripleo_deploy_artifacts.run(module)
        self.assertEqual(mock_filetype.call_count, 2)
        mock_filetype.has_calls([mock.call('myrpm'), mock.call('mytgz')])
        mock_rpm.assert_called_once_with('foo')
        mock_tgz.assert_called_once_with('bar')
        mock_exit.assert_called_once_with(changed=True)

    @mock.patch('urllib.request.urlretrieve')
    def test_run_fail(self, mock_urlretrieve):
        module = mock.MagicMock()
        module.params = {'artifact_urls': ['myrpm', 'mytgz']}
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        mock_urlretrieve.side_effect = Exception('meh')
        tripleo_deploy_artifacts.run(module)
        mock_exit.assert_called_once_with(changed=False, error=mock.ANY,
                                          failed=True,
                                          msg='Unhandled exception: meh')

    @mock.patch('tripleo_ansible.ansible_plugins.modules.'
                'tripleo_deploy_artifacts._get_filetype')
    @mock.patch('urllib.request.urlretrieve')
    def test_run_unknown(self, mock_urlretrieve, mock_filetype):
        module = mock.MagicMock()
        module.params = {'artifact_urls': ['bad']}
        mock_filetype.return_value = 'UNKNOWN'
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        mock_urlretrieve.return_value = ('foo', None)
        tripleo_deploy_artifacts.run(module)
        mock_exit.assert_called_once_with(changed=False,
                                          error='Invalid file format',
                                          failed=True,
                                          msg=('Unable to determine file '
                                               'format for bad'))

    @mock.patch('subprocess.run')
    def test_get_filetype_rpm(self, mock_run):
        mock_rc = mock.MagicMock()
        mock_rc.stdout = 'RPM v3.0 bin i386/x86_64 foo-0.0.1'
        mock_run.return_value = mock_rc
        self.assertEqual('rpm', tripleo_deploy_artifacts._get_filetype('foo'))
        mock_run.assert_called_once_with('file -b foo', shell=True, stderr=-1,
                                         stdout=-1, universal_newlines=True)

    @mock.patch('subprocess.run')
    def test_get_filetype_targz(self, mock_run):
        mock_rc = mock.MagicMock()
        mock_rc.stdout = ('gzip compressed data, last modified: Fri Mar 13 '
                          '22:10:46 2020, from Unix, original size modulo '
                          '2^32 4280320')
        mock_run.return_value = mock_rc
        self.assertEqual('targz',
                         tripleo_deploy_artifacts._get_filetype('foo'))
        mock_run.assert_called_once_with('file -b foo', shell=True, stderr=-1,
                                         stdout=-1, universal_newlines=True)

    @mock.patch('subprocess.run')
    def test_get_filetype_unknown(self, mock_run):
        mock_rc = mock.MagicMock()
        mock_rc.stdout = 'ASCII File'
        mock_run.return_value = mock_rc
        self.assertEqual('UNKNOWN',
                         tripleo_deploy_artifacts._get_filetype('foo'))
        mock_run.assert_called_once_with('file -b foo', shell=True, stderr=-1,
                                         stdout=-1, universal_newlines=True)

    @mock.patch('subprocess.run')
    def test_get_filetype_fail(self, mock_run):
        mock_run.side_effect = Exception('meh')
        self.assertRaises(Exception,
                          tripleo_deploy_artifacts._get_filetype,
                          'foo')

    @mock.patch('os.rename')
    @mock.patch('subprocess.run')
    def test_deploy_rpm(self, mock_run, mock_rename):
        tripleo_deploy_artifacts.deploy_rpm('foo')
        mock_run.assert_called_once_with('dnf install -y foo.rpm', check=True,
                                         shell=True, stderr=-1,
                                         universal_newlines=True)

    @mock.patch('os.unlink')
    @mock.patch('os.path.exists')
    @mock.patch('os.rename')
    @mock.patch('subprocess.run')
    def test_deploy_rpm_fail(self, mock_run, mock_rename, mock_exists,
                             mock_unlink):
        mock_run.side_effect = Exception('meh')
        mock_exists.return_value = True
        self.assertRaises(Exception,
                          tripleo_deploy_artifacts.deploy_rpm,
                          'foo')
        mock_unlink.assert_called_once_with('foo.rpm')

    @mock.patch('subprocess.run')
    def test_deploy_targz(self, mock_run):
        tripleo_deploy_artifacts.deploy_targz('foo')
        mock_run.assert_called_once_with('tar xvz -C / -f foo', check=True,
                                         shell=True, stderr=-1,
                                         universal_newlines=True)

    @mock.patch('os.unlink')
    @mock.patch('os.path.exists')
    @mock.patch('subprocess.run')
    def test_deploy_targz_fail(self, mock_run, mock_exists, mock_unlink):
        mock_run.side_effect = Exception('meh')
        mock_exists.return_value = True
        self.assertRaises(Exception,
                          tripleo_deploy_artifacts.deploy_targz,
                          'foo')
        mock_unlink.assert_called_once_with('foo')
