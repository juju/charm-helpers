import contextlib
import copy
import io
import os
import mock
import six
import unittest

from charmhelpers.contrib.openstack import policyd


if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'


class PolicydTests(unittest.TestCase):
    def setUp(self):
        super(PolicydTests, self).setUp()

    def test_is_policyd_override_valid_on_this_release(self):
        self.assertTrue(
            policyd.is_policyd_override_valid_on_this_release("queens"))
        self.assertTrue(
            policyd.is_policyd_override_valid_on_this_release("rocky"))
        self.assertFalse(
            policyd.is_policyd_override_valid_on_this_release("pike"))

    @mock.patch.object(policyd, "clean_policyd_dir_for")
    @mock.patch.object(policyd, "remove_policy_success_file")
    @mock.patch.object(policyd, "process_policy_resource_file")
    @mock.patch.object(policyd, "get_policy_resource_filename")
    @mock.patch.object(policyd, "is_policyd_override_valid_on_this_release")
    @mock.patch.object(policyd, "_policy_success_file")
    @mock.patch("os.path.isfile")
    @mock.patch.object(policyd.hookenv, "config")
    @mock.patch("charmhelpers.core.hookenv.log")
    def test_maybe_do_policyd_overrides(
        self,
        mock_log,
        mock_config,
        mock_isfile,
        mock__policy_success_file,
        mock_is_policyd_override_valid_on_this_release,
        mock_get_policy_resource_filename,
        mock_process_policy_resource_file,
        mock_remove_policy_success_file,
        mock_clean_policyd_dir_for,
    ):
        mock_isfile.return_value = False
        mock__policy_success_file.return_value = "s-return"
        # test success condition
        mock_config.return_value = {policyd.POLICYD_CONFIG_NAME: True}
        mock_is_policyd_override_valid_on_this_release.return_value = True
        mock_get_policy_resource_filename.return_value = "resource.zip"
        mock_process_policy_resource_file.return_value = True
        mod_fn = mock.Mock()
        restart_handler = mock.Mock()
        policyd.maybe_do_policyd_overrides(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler)
        mock_is_policyd_override_valid_on_this_release.assert_called_once_with(
            "arelease")
        mock_get_policy_resource_filename.assert_called_once_with()
        mock_process_policy_resource_file.assert_called_once_with(
            "resource.zip", "aservice", ["a"], ["b"], mod_fn)
        restart_handler.assert_called_once_with()
        # test process_policy_resource_file is not called if not valid on the
        # release.
        mock_process_policy_resource_file.reset_mock()
        restart_handler.reset_mock()
        mock_is_policyd_override_valid_on_this_release.return_value = False
        policyd.maybe_do_policyd_overrides(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler)
        mock_process_policy_resource_file.assert_not_called()
        restart_handler.assert_not_called()
        # test restart_handler is not called if not needed.
        mock_is_policyd_override_valid_on_this_release.return_value = True
        mock_process_policy_resource_file.return_value = False
        policyd.maybe_do_policyd_overrides(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler)
        mock_process_policy_resource_file.assert_called_once_with(
            "resource.zip", "aservice", ["a"], ["b"], mod_fn)
        restart_handler.assert_not_called()
        # test that directory gets cleaned if the config is not set
        mock_config.return_value = {policyd.POLICYD_CONFIG_NAME: False}
        mock_process_policy_resource_file.reset_mock()
        policyd.maybe_do_policyd_overrides(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler)
        mock_process_policy_resource_file.assert_not_called()
        mock_remove_policy_success_file.assert_called_once_with()
        mock_clean_policyd_dir_for.assert_called_once_with(
            "aservice", ["a"], user='aservice', group='aservice')

    @mock.patch.object(policyd, "maybe_do_policyd_overrides")
    def test_maybe_do_policyd_overrides_with_config_changed(
        self,
        mock_maybe_do_policyd_overrides,
    ):
        mod_fn = mock.Mock()
        restart_handler = mock.Mock()
        policyd.maybe_do_policyd_overrides_on_config_changed(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler)
        mock_maybe_do_policyd_overrides.assert_called_once_with(
            "arelease", "aservice", ["a"], ["b"], mod_fn, restart_handler,
            config_changed=True)

    @mock.patch("charmhelpers.core.hookenv.resource_get")
    def test_get_policy_resource_filename(self, mock_resource_get):
        mock_resource_get.return_value = "test-file"
        self.assertEqual(policyd.get_policy_resource_filename(),
                         "test-file")
        mock_resource_get.assert_called_once_with(
            policyd.POLICYD_RESOURCE_NAME)

        # check that if an error is raised, that None is returned.
        def go_bang(*args):
            raise Exception("bang")

        mock_resource_get.side_effect = go_bang
        self.assertEqual(policyd.get_policy_resource_filename(), None)

    @mock.patch.object(policyd, "_yamlfiles")
    @mock.patch.object(policyd.zipfile, "ZipFile")
    def test_open_and_filter_yaml_files(self, mock_ZipFile, mock__yamlfiles):
        mock__yamlfiles.return_value = [
            ("file1", ".yaml", "file1.yaml", None),
            ("file2", ".yml", "file2.YML", None)]
        mock_ZipFile.return_value.__enter__.return_value = "zfp"
        # test a valid zip file
        with policyd.open_and_filter_yaml_files("some-file") as (zfp, files):
            self.assertEqual(zfp, "zfp")
            mock_ZipFile.assert_called_once_with("some-file", "r")
            self.assertEqual(files, [
                ("file1", ".yaml", "file1.yaml", None),
                ("file2", ".yml", "file2.YML", None)])
        # ensure that there must be at least one file.
        mock__yamlfiles.return_value = []
        with self.assertRaises(policyd.BadPolicyZipFile):
            with policyd.open_and_filter_yaml_files("some-file"):
                pass
        # ensure that it picks up duplicates
        mock__yamlfiles.return_value = [
            ("file1", ".yaml", "file1.yaml", None),
            ("file2", ".yml", "file2.yml", None),
            ("file1", ".yml", "file1.yml", None)]
        with self.assertRaises(policyd.BadPolicyZipFile):
            with policyd.open_and_filter_yaml_files("some-file"):
                pass

    def test__yamlfiles(self):
        class MockZipFile(object):
            def __init__(self, infolist):
                self._infolist = infolist

            def infolist(self):
                return self._infolist

        class MockInfoListItem(object):
            def __init__(self, is_dir, filename):
                self.filename = filename
                self._is_dir = is_dir

            def is_dir(self):
                return self._is_dir

            def __repr__(self):
                return "MockInfoListItem({}, {})".format(self._is_dir,
                                                         self.filename)

        zipfile = MockZipFile([
            MockInfoListItem(False, "file1.yaml"),
            MockInfoListItem(False, "file2.md"),
            MockInfoListItem(False, "file3.YML"),
            MockInfoListItem(False, "file4.Yaml"),
            MockInfoListItem(True, "file5"),
            MockInfoListItem(True, "file6.yaml"),
            MockInfoListItem(False, "file7"),
            MockInfoListItem(False, "file8.j2")])

        self.assertEqual(list(policyd._yamlfiles(zipfile)),
                         [("file1", ".yaml", "file1.yaml", mock.ANY),
                          ("file3", ".yml", "file3.YML", mock.ANY),
                          ("file4", ".yaml", "file4.Yaml", mock.ANY),
                          ("file8", ".j2", "file8.j2", mock.ANY)])

    @mock.patch.object(policyd.yaml, "safe_load")
    def test_read_and_validate_yaml(self, mock_safe_load):
        # test a valid document
        good_doc = {
            "key1": "rule1",
            "key2": "rule2",
        }
        mock_safe_load.return_value = copy.deepcopy(good_doc)
        doc = policyd.read_and_validate_yaml("test-stream")
        self.assertEqual(doc, good_doc)
        mock_safe_load.assert_called_once_with("test-stream")
        # test an invalid document - return a string
        mock_safe_load.return_value = "wrong"
        with self.assertRaises(policyd.BadPolicyYamlFile):
            policyd.read_and_validate_yaml("test-stream")
        # test for black-listed keys
        with self.assertRaises(policyd.BadPolicyYamlFile):
            mock_safe_load.return_value = copy.deepcopy(good_doc)
            policyd.read_and_validate_yaml("test-stream", ["key1"])
        # test for non string keys
        bad_key_doc = {
            (1,): "rule1",
            "key2": "rule2",
        }
        with self.assertRaises(policyd.BadPolicyYamlFile):
            mock_safe_load.return_value = copy.deepcopy(bad_key_doc)
            policyd.read_and_validate_yaml("test-stream", ["key1"])
        # test for non string values (i.e. no nested keys)
        bad_key_doc2 = {
            "key1": "rule1",
            "key2": {"sub_key": "rule2"},
        }
        with self.assertRaises(policyd.BadPolicyYamlFile):
            mock_safe_load.return_value = copy.deepcopy(bad_key_doc2)
            policyd.read_and_validate_yaml("test-stream", ["key1"])

    def test_policyd_dir_for(self):
        self.assertEqual(policyd.policyd_dir_for('thing'),
                         "/etc/thing/policy.d")

    @mock.patch.object(policyd.hookenv, 'log')
    @mock.patch("os.remove")
    @mock.patch("shutil.rmtree")
    @mock.patch("charmhelpers.core.host.mkdir")
    @mock.patch("os.path.exists")
    @mock.patch.object(policyd, "policyd_dir_for")
    def test_clean_policyd_dir_for(self,
                                   mock_policyd_dir_for,
                                   mock_os_path_exists,
                                   mock_mkdir,
                                   mock_shutil_rmtree,
                                   mock_os_remove,
                                   mock_log):
        if hasattr(os, 'scandir'):
            mock_scan_dir_parts = (mock.patch, ["os.scandir"])
        else:
            mock_scan_dir_parts = (mock.patch.object,
                                   [policyd, "_fallback_scandir"])

        class MockDirEntry(object):
            def __init__(self, path, is_dir):
                self.path = path
                self._is_dir = is_dir

            def is_dir(self):
                return self._is_dir

        # list of scanned objects
        directory_contents = [
            MockDirEntry("one", False),
            MockDirEntry("two", False),
            MockDirEntry("three", True),
            MockDirEntry("four", False)]

        mock_policyd_dir_for.return_value = "the-path"

        # Initial conditions
        mock_os_path_exists.return_value = False

        # call the function
        with mock_scan_dir_parts[0](*mock_scan_dir_parts[1]) as \
                mock_os_scandir:
            mock_os_scandir.return_value = directory_contents
            policyd.clean_policyd_dir_for("aservice")

        # check it did the right thing
        mock_policyd_dir_for.assert_called_once_with("aservice")
        mock_os_path_exists.assert_called_once_with("the-path")
        mock_mkdir.assert_called_once_with("the-path",
                                           owner="aservice",
                                           group="aservice",
                                           perms=0o775)
        mock_shutil_rmtree.assert_called_once_with("three")
        mock_os_remove.assert_has_calls([
            mock.call("one"), mock.call("two"), mock.call("four")])

        # check also that we can omit paths ... reset everything
        mock_os_remove.reset_mock()
        mock_shutil_rmtree.reset_mock()
        mock_os_path_exists.reset_mock()
        mock_os_path_exists.return_value = True
        mock_mkdir.reset_mock()

        with mock_scan_dir_parts[0](*mock_scan_dir_parts[1]) as \
                mock_os_scandir:
            mock_os_scandir.return_value = directory_contents
            policyd.clean_policyd_dir_for("aservice",
                                          keep_paths=["one", "three"])

        # verify all worked as we expected
        mock_mkdir.assert_not_called()
        mock_shutil_rmtree.assert_not_called()
        mock_os_remove.assert_has_calls([mock.call("two"), mock.call("four")])

    def test_path_for_policy_file(self):
        self.assertEqual(policyd.path_for_policy_file('this', 'that'),
                         "/etc/this/policy.d/that.yaml")

    @mock.patch("charmhelpers.core.hookenv.charm_dir")
    def test__policy_success_file(self, mock_charm_dir):
        mock_charm_dir.return_value = "/this"
        self.assertEqual(policyd._policy_success_file(),
                         "/this/{}".format(policyd.POLICYD_SUCCESS_FILENAME))

    @mock.patch("os.remove")
    @mock.patch.object(policyd, "_policy_success_file")
    def test_remove_policy_success_file(self, mock_file, mock_os_remove):
        mock_file.return_value = "the-path"
        policyd.remove_policy_success_file()
        mock_os_remove.assert_called_once_with("the-path")

        # now test that failure doesn't fail the function
        def go_bang(*args):
            raise Exception("bang")

        mock_os_remove.side_effect = go_bang
        policyd.remove_policy_success_file()

    @mock.patch("os.path.isfile")
    @mock.patch.object(policyd, "_policy_success_file")
    def test_policyd_status_message_prefix(self, mock_file, mock_is_file):
        mock_file.return_value = "the-path"
        mock_is_file.return_value = True
        self.assertEqual(policyd.policyd_status_message_prefix(), "PO:")
        mock_is_file.return_value = False
        self.assertEqual(
            policyd.policyd_status_message_prefix(), "PO (broken):")

    @mock.patch("yaml.dump")
    @mock.patch.object(policyd, "_policy_success_file")
    @mock.patch.object(policyd.hookenv, "log")
    @mock.patch.object(policyd, "read_and_validate_yaml")
    @mock.patch.object(policyd, "path_for_policy_file")
    @mock.patch.object(policyd, "clean_policyd_dir_for")
    @mock.patch.object(policyd, "remove_policy_success_file")
    @mock.patch.object(policyd, "open_and_filter_yaml_files")
    @mock.patch.object(policyd.ch_host, 'write_file')
    @mock.patch.object(policyd, "maybe_create_directory_for")
    def test_process_policy_resource_file(
        self,
        mock_maybe_create_directory_for,
        mock_write_file,
        mock_open_and_filter_yaml_files,
        mock_remove_policy_success_file,
        mock_clean_policyd_dir_for,
        mock_path_for_policy_file,
        mock_read_and_validate_yaml,
        mock_log,
        mock__policy_success_file,
        mock_yaml_dump,
    ):
        mock_zfp = mock.MagicMock()
        mod_fn = mock.Mock()
        mock_path_for_policy_file.side_effect = lambda s, n: s + "/" + n
        gen = [
            ("file1", ".yaml", "file1.yaml", "file1-zipinfo"),
            ("file2", ".yml", "file2.yml", "file2-zipinfo")]
        mock_open_and_filter_yaml_files.return_value.__enter__.return_value = \
            (mock_zfp, gen)
        # first verify that we can blacklist a file
        res = policyd.process_policy_resource_file(
            "resource.zip", "aservice", ["aservice/file1"], [], mod_fn)
        self.assertFalse(res)
        mock_remove_policy_success_file.assert_called_once_with()
        mock_clean_policyd_dir_for.assert_has_calls([
            mock.call("aservice",
                      ["aservice/file1"],
                      user='aservice',
                      group='aservice'),
            mock.call("aservice",
                      ["aservice/file1"],
                      user='aservice',
                      group='aservice')])
        mock_zfp.open.assert_not_called()
        mod_fn.assert_not_called()
        mock_log.assert_any_call("Processing resource.zip failed: policy.d"
                                 " name aservice/file1 is blacklisted",
                                 level=policyd.POLICYD_LOG_LEVEL_DEFAULT)

        # now test for success
        @contextlib.contextmanager
        def _patch_open():
            '''Patch open() to allow mocking both open() itself and the file that is
            yielded.

            Yields the mock for "open" and "file", respectively.'''
            mock_open = mock.MagicMock(spec=open)
            mock_file = mock.MagicMock(spec=io.FileIO)

            with mock.patch(builtin_open, mock_open):
                yield mock_open, mock_file

        mock_clean_policyd_dir_for.reset_mock()
        mock_zfp.reset_mock()
        mock_fp = mock.MagicMock()
        mock_fp.read.return_value = '{"rule1": "value1"}'
        mock_zfp.open.return_value.__enter__.return_value = mock_fp
        gen = [("file1", ".j2", "file1.j2", "file1-zipinfo")]
        mock_open_and_filter_yaml_files.return_value.__enter__.return_value = \
            (mock_zfp, gen)
        mock_read_and_validate_yaml.return_value = {"rule1": "modded_value1"}
        mod_fn.return_value = '{"rule1": "modded_value1"}'
        mock__policy_success_file.return_value = "policy-success-file"
        mock_yaml_dump.return_value = "dumped-file"
        with _patch_open() as (mock_open, mock_file):
            res = policyd.process_policy_resource_file(
                "resource.zip", "aservice", [], ["key"], mod_fn)
            self.assertTrue(res)
            # mock_open.assert_any_call("aservice/file1", "wt")
            mock_write_file.assert_called_once_with(
                "aservice/file1",
                b'dumped-file',
                "aservice",
                "aservice")
            mock_open.assert_any_call("policy-success-file", "w")
            mock_yaml_dump.assert_called_once_with({"rule1": "modded_value1"})
        mock_zfp.open.assert_called_once_with("file1-zipinfo")
        mock_read_and_validate_yaml.assert_called_once_with(
            '{"rule1": "modded_value1"}', ["key"])
        mod_fn.assert_called_once_with('{"rule1": "value1"}')

        # raise a BadPolicyZipFile if we have a template, but there is no
        # template function
        mock_log.reset_mock()
        with _patch_open() as (mock_open, mock_file):
            res = policyd.process_policy_resource_file(
                "resource.zip", "aservice", [], ["key"],
                template_function=None)
            self.assertFalse(res)
        mock_log.assert_any_call(
            "Processing resource.zip failed: Template file1.j2 "
            "but no template_function is available",
            level=policyd.POLICYD_LOG_LEVEL_DEFAULT)

        # raise the IOError to validate that code path
        def raise_ioerror(*args):
            raise IOError("bang")

        mock_open_and_filter_yaml_files.side_effect = raise_ioerror
        mock_log.reset_mock()
        res = policyd.process_policy_resource_file(
            "resource.zip", "aservice", [], ["key"], mod_fn)
        self.assertFalse(res, False)
        mock_log.assert_any_call(
            "File resource.zip failed with IOError.  "
            "This really shouldn't happen -- error: bang",
            level=policyd.POLICYD_LOG_LEVEL_DEFAULT)
        # raise a general exception, so that is caught and logged too.

        def raise_exception(*args):
            raise Exception("bang2")

        mock_open_and_filter_yaml_files.reset_mock()
        mock_open_and_filter_yaml_files.side_effect = raise_exception
        mock_log.reset_mock()
        res = policyd.process_policy_resource_file(
            "resource.zip", "aservice", [], ["key"], mod_fn)
        self.assertFalse(res, False)
        mock_log.assert_any_call(
            "General Exception(bang2) during policyd processing",
            level=policyd.POLICYD_LOG_LEVEL_DEFAULT)
