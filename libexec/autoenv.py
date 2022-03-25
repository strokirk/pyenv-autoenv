#!/usr/bin/env python3
from typing import NamedTuple
import argparse
import os
import re
import subprocess
from pathlib import Path

PYENV_AUTOENV_VERSION = "2.2.0"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name")
    parser.add_argument("--python")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--clear-if-lower", action="store_true")
    parser.add_argument("--no-local", action="store_true")
    parser.add_argument("-q", "--quiet", action="count")
    args = parser.parse_args()

    if args.version:
        print(PYENV_AUTOENV_VERSION)
        return

    run = subprocess.run
    name = args.name
    output = Output(args.quiet)

    if not name:
        name = Path().cwd().name

    versions = get_versions(name, args.python)

    if name in versions.installed:
        if args.clear_if_lower and versions.current_is_lower:
            args.clear = True

        if not args.clear:
            if versions.current_is_lower:
                output.yell("Virtualenv '{}' ({}) already exists.".format(name, versions.current))
                output.yell("Desired Python ({}) is later, use '--clear-if-lower' to upgrade.".format(versions.desired))
            else:
                output.say("Virtualenv '{}' ({}) already exists. Use '--clear' to recreate it.".format(name, versions.current))
            return

        output.say("Clearing previous virtualenv '{}'...".format(name))

        run(["pyenv", "virtualenv-delete", "-f", name])

    if versions.desired not in versions.installed:
        output.shout("Using Python version {}".format(versions.desired))
        run(["pyenv", "install", "--skip-existing", versions.desired])

    fmt = "Creating new virtualenv '{}' with Python {}..."
    output.yell(fmt.format(name, versions.desired))

    run(["pyenv", "virtualenv", versions.desired, name], capture_output=output.level > 0)

    if args.no_local:
        return
    output.say("Setting local virtualenv '{}'...".format(name))
    run(["pyenv", "local", name])


class Output:
    def __init__(self, level: int = 0):
        self.level = level or 0

    def say(self, s: str):
        if self.level < 1:
            print(s)

    def yell(self, s: str):
        if self.level < 2:
            print(s)

    def shout(self, s: str):
        print(s)


class VersionDetector:
    def __init__(self, definitions):
        self.definitions: "list[str]" = definitions

    def get_desired_version_spec(self, version=None) -> "None | VersionSpec":
        if version:
            return version
        finders = [
            ("pyproject.toml", "requires-python"),
            ("setup.py", "python_requires"),
            ("setup.cfg", "python_requires"),
        ]
        for filename, prefix in finders:
            version_line = _find_line_with_prefix(filename, prefix)
            if version_line:
                return VersionSpec(version_line)
        line = self.get_runtime_txt_version()
        if line:
            return VersionSpec(line)
        return None

    def get_concrete_version(self, desired: "VersionSpec") -> "None | str":
        if desired.optimal in self.definitions:
            return desired.optimal
        for definition in sorted(self.definitions, reverse=True):
            if re.match(desired.optimal, definition):
                return definition
        return None

    def get_latest_version(self) -> "str":
        for version in reversed(self.definitions):
            if re.match(r"\d+\.\d+\.\d+$", version):  # type: ignore
                return version  # type: ignore
        aise SystemExit("Couldn't find any usable Python versions")

    def get_runtime_txt_version(self) -> "None | str":
        prefix = "python-"
        line = _find_line_with_prefix("runtime.txt", prefix)
        if line:
            return _removeprefix(line, prefix)
        return None


class VersionSpec:
    def __init__(self, spec: str) -> None:
        self.spec = spec
        self.greater = False
        self.equal = False
        self.lower = False

        spec = spec.split("=", maxsplit=1)[1].strip("\t \"',")

        if re.match(r"[0-9.]+$", spec):
            self.equal = True
            self.optimal = spec
            return

        elif re.match(r">", spec):
            # For > / >= we can simply fall back to using the latest version possible
            self.greater = True
            self.optimal = _removeprefix(_removeprefix(spec, ">"), "=")
            return

        elif re.match(r"[0-9.]+$", _removeprefix(spec, "<=")):
            # For <= we can treat it as "==", since we want to use the latest version possible
            self.equal = True
            self.optimal = _removeprefix(spec, "<=")
            return

        elif re.match(r"<[0-9.]+$", spec):
            # For < we need to guess what the previous available version could be
            self.lower = True
            version = list(map(int, _removeprefix(spec, "<").split(".")))
            if version[-1] == 0:
                version.pop()
            version[-1] -= 1
            self.optimal = ".".join(map(str, version))

        else:
            raise SystemExit("Unimplemented version specifier: %s" % spec)

    def is_lower(self, version):
        return version.split(".") < self.optimal.split(".")

    def __repr__(self):
        return "<VersionSpec({})>".format(self.spec)

    def __str__(self):
        return self.spec


class Versions(NamedTuple):
    current: "str | None"
    desired: str
    current_is_lower: bool
    installed: "list[str]"


def get_versions(name: str, desired_python: "str | None" = None) -> Versions:
    installed_versions = get_installed_versions()
    available_versions = get_definitions()

    current = None
    if name in installed_versions:
        current = get_venv_python_version(name)

    detector = VersionDetector(available_versions)
    desired = None
    if desired_python:
        desired = detector.get_concrete_version(VersionSpec(f'python_requires="{desired_python}"'))
        if not desired:
            raise SystemExit("Python '%s' not available" % desired_python)

    spec = None
    current_is_lower = False
    if not desired:
        spec = detector.get_desired_version_spec()
        if spec:
            if current and not spec.is_lower(current):
                desired = current
            else:
                current_is_lower = True
                desired = detector.get_concrete_version(spec)

    if desired is None:
        desired = detector.get_latest_version()

    return Versions(
        current,
        desired,
        current_is_lower,
        installed_versions,
    )


def get_installed_versions() -> "list[str]":
    natsort = lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split('(\d+)', s)]
    sorted_list = sorted(_get_command_output(["pyenv", "versions", "--bare", "--skip-aliases"]).splitlines(), key=natsort)
    return sorted_list


def get_definitions() -> "list[str]":
    result = _get_command_output(["python-build", "--definitions"])
    return [line.strip() for line in result.splitlines()]


def get_venv_python_version(name: str) -> str:
    prefix = _get_command_output(["pyenv", "prefix", name])
    python_bin = str(Path(prefix) / "bin" / "python")
    current = _get_command_output([python_bin, "--version"])
    return _removeprefix(current, "Python ")


###########
#  UTILS  #
###########


def _get_command_output(cmd: list) -> str:
    return subprocess.check_output(cmd).decode().strip()


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
