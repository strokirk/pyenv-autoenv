#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name")
    parser.add_argument("--python")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--no-local", action="store_true")
    parser.add_argument("-q", "--quiet", action="count")
    args = parser.parse_args()

    quiet = args.quiet or 0
    run = subprocess.run
    name = args.name

    if not name:
        name = Path().cwd().name

    result = run(["pyenv", "versions", "--bare"], capture_output=True)
    versions = result.stdout.decode().splitlines()
    if name in versions:
        if not args.clear:
            print("Virtualenv '{}' already exists. Use the flag '--clear' to recreate it.".format(name))
            return
        if quiet < 1:
            print("Clearing previous virtualenv '{}'...".format(name))
        run(["pyenv", "virtualenv-delete", "-f", name])

    python = detect_version(args.version)
    if python not in versions:
        print("Using Python version {}".format(python))
        run(["pyenv", "install", "--skip-existing", python])

    if quiet < 2:
        print("Creating new virtualenv '{}' with Python {}...".format(name, python))
    run(["pyenv", "virtualenv", python, name], capture_output=quiet > 0)

    if args.no_local:
        return
    if quiet < 1:
        print("Setting local virtualenv '{}'...".format(name))
    run(["pyenv", "local", name])


def detect_version(desired) -> str:
    definitions = get_definitions()

    detector = VersionDetector(definitions)
    desired = detector.get_desired_version(desired)
    if desired:
        if desired in definitions:
            return desired
        for definition in sorted(definitions, reverse=True):
            if re.match(desired, definition):
                return definition
        raise SystemExit("Python '%s' not available" % desired)

    version = detector.get_latest_version()
    if version:
        return version
    raise SystemExit("No versions found")


class VersionDetector:
    def __init__(self, definitions):
        self.definitions = definitions

    def get_desired_version(self, version=None):
        if version:
            return version
        finders = [
            self.get_pyproject_version,
            self.get_setup_cfg_version,
            self.get_setup_py_version,
            self.get_runtime_txt_version,
        ]
        for finder in finders:
            version = finder()
            if version:
                return version
        return None

    def get_latest_version(self) -> "None | str":
        for version in sorted(self.definitions, reverse=True):
            if re.match(r"\d+\.\d+\.\d+$", version):
                return version
        return None

    def get_runtime_txt_version(self) -> "None | str":
        prefix = "python-"
        line = _find_line_with_prefix("runtime.txt", prefix)
        if line:
            return _removeprefix(line, prefix)
        return None

    def get_pyproject_version(self) -> "None | str":
        # Hacky version parser that works for the most common version specifiers
        line = _find_line_with_prefix("pyproject.toml", "requires-python")
        if line:
            return self._parse_version_specifier(line)
        return None

    def get_setup_py_version(self) -> "None | str":
        line = _find_line_with_prefix("setup.py", "python_requires")
        if line:
            return self._parse_version_specifier(line)
        return None

    def get_setup_cfg_version(self) -> "None | str":
        line = _find_line_with_prefix("setup.cfg", "python_requires")
        if line:
            return self._parse_version_specifier(line)
        return None

    def _parse_version_specifier(self, line) -> "None | str":
        """
        Parsers a line like `python_requires = "<=3.8"` into a
        more concrete version
        """
        requires = line.split("=", maxsplit=1)[1].strip("\t \"',")
        if re.match(r">", requires):
            # For > / >= we can simply fall back to using the latest version possible
            return self.get_latest_version()
        if re.match(r"[0-9.]+$", _removeprefix(requires, "<=")):
            # For <= we can treat it as "==", since we want to use the latest version possible
            return _removeprefix(requires, "<=")
        if re.match(r"<[0-9.]+$", requires):
            # For < we need to guess what the previous available version could be
            version = list(map(int, _removeprefix(requires, "<").split(".")))
            version[-1] -= 1
            return ".".join(map(str, version))

        raise SystemExit("Unimplemented version specifier: %s" % requires)


def get_definitions() -> list:
    result = subprocess.run(["python-build", "--definitions"], capture_output=True)
    return [line.strip() for line in result.stdout.decode().splitlines()]


###########
#  UTILS  #
###########


def _removeprefix(s, prefix) -> str:
    if s.startswith(prefix):
        return s[len(prefix) :]
    return s[:]


def _find_line_with_prefix(filename, prefix):
    if not os.path.exists(filename):
        return None
    with open(filename) as f:
        for line in f.read().splitlines():
            if line.strip().startswith(prefix):
                return line
    return None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
