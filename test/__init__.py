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

        stack.enter_context(chtmpdir())

        self.mock_get_versions = stack.enter_context(mock.patch("autoenv.get_installed_versions", automock=True))

        self.mock_get_definitions = stack.enter_context(mock.patch("autoenv.get_definitions", automock=True))
        self.mock_get_definitions.return_value = [
            "3.11-dev",
            "3.9.4",
            "3.8.5",
            "3.8.9",
            "3.10.2",
            "3.11.0a4",
            "3.9",
            "pypy-3.9",
        ]

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

    def test_latest_version(self):
        res = autoenv.get_versions("test-env")
        self.assertEqual(res.desired, "3.10.2")
        self.assertEqual(res.current, None)



class TestVersionDetectionWithCurrent(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)

        stack.enter_context(chtmpdir())
        Path("pyproject.toml").write_text('requires-python = "3.10.0"\n')

        patch = lambda target: stack.enter_context(mock.patch(target, automock=True))

        self.mock_get_versions = patch("autoenv.get_installed_versions")
        self.mock_get_versions.return_value = ["test-env"]

        self.mock_get_definitions = patch("autoenv.get_definitions")
        self.mock_get_definitions.return_value = ["3.10.0"]

        self.mock_current = patch("autoenv.get_venv_python_version")

    def test_desired_version_is_specified_when_lower(self):
        self.mock_current.return_value = "3.9"

        res = autoenv.get_versions("test-env")
        self.assertEqual(res.current, "3.9")
        self.assertEqual(res.desired, "3.10.0")
        self.assertTrue(res.current_is_lower)

    def test_desired_version_is_specified_when_equal(self):
        self.mock_current.return_value = "3.10"

        res = autoenv.get_versions("test-env")
        self.assertEqual(res.current, "3.10")
        self.assertEqual(res.desired, "3.10.0")

    def test_desired_version_is_current_when_higher(self):
        self.mock_current.return_value = "3.11"

        res = autoenv.get_versions("test-env")
        self.assertEqual(res.current, "3.11")
        self.assertEqual(res.desired, "3.11")


@contextmanager
def chtmpdir():
    with tempfile.TemporaryDirectory() as tmpdir:
        with chdir(tmpdir):
            yield Path(tmpdir)


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
