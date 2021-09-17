import os
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

sys.path += [str(Path(__file__).parent.parent / "libexec")]
import autoenv  # noqa


class TestVersionDetection(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)

        self.tmpdir = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(chdir(self.tmpdir))

        self.mock_get_versions = stack.enter_context(mock.patch("autoenv.get_installed_versions"))

    def test_setup_cfg(self):
        Path("setup.cfg").write_text('python_requires="3.9.4"\n')
        res = autoenv.get_versions("test-env")
        self.assertEqual(res.desired, "3.9.4")
        self.assertEqual(res.current, None)

    def test_pyproject_toml(self):
        Path("pyproject.toml").write_text('requires-python = "3.8.5"\n')
        res = autoenv.get_versions("test-env")
        self.assertEqual(res.desired, "3.8.5")
        self.assertEqual(res.current, None)

    def test_manual_version(self):
        Path("pyproject.toml").write_text('requires-python = "3.7.0"\n')
        res = autoenv.get_versions("test-env", "3.8")
        self.assertEqual(res.desired, "3.8.9")
        self.assertEqual(res.current, None)

    def test_manual_version_non_existing(self):
        with self.assertRaises(SystemExit):
            autoenv.get_versions("test-env", "3.99")


class TestVersionDetectionWithCurrent(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)

        self.tmpdir = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(chdir(self.tmpdir))

        self.mock_get_versions = stack.enter_context(mock.patch("autoenv.get_installed_versions"))
        self.mock_get_versions.return_value = ["test-env"]
        Path("pyproject.toml").write_text('requires-python = "3.7.0"\n')

    def test_desired_version_is_specified_when_lower(self):
        with mock.patch("autoenv.get_venv_python_version", return_value="3.6"):
            res = autoenv.get_versions("test-env")
            self.assertEqual(res.current, "3.6")
            self.assertEqual(res.desired, "3.7.0")

    def test_desired_version_is_specified_when_equal(self):
        with mock.patch("autoenv.get_venv_python_version", return_value="3.7"):
            res = autoenv.get_versions("test-env")
            self.assertEqual(res.current, "3.7")
            self.assertEqual(res.desired, "3.7.0")

    def test_desired_version_is_current_when_higher(self):
        with mock.patch("autoenv.get_venv_python_version", return_value="3.8"):
            res = autoenv.get_versions("test-env")
            self.assertEqual(res.current, "3.8")
            self.assertEqual(res.desired, "3.8")


@contextmanager
def chdir(path: str):
    curdir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(curdir)


if __name__ == "__main__":
    unittest.main()
