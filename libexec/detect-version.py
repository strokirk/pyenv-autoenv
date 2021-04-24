import re
import os
import subprocess
import sys


def main():
    definitions = get_definitions()

    detector = VersionDetector(definitions)
    desired = detector.get_desired_version()
    if desired:
        if desired in definitions:
            print(desired)
            return
        for definition in sorted(definitions, reverse=True):
            if re.match(desired, definition):
                print(definition)
                return
        raise SystemExit("Python '%s' not available" % desired)

    version = detector.get_latest_version()
    if version:
        print(version)
        return
    raise SystemExit("No versions found")


class VersionDetector:
    def __init__(self, definitions):
        self.definitions = definitions

    def get_desired_version(self):
        version = None if len(sys.argv) < 2 else sys.argv[1].strip()
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

    def get_latest_version(self):
        for version in sorted(self.definitions, reverse=True):
            if re.match(r"\d+\.\d+\.\d+$", version):
                return version
        return None

    def get_runtime_txt_version(self):
        prefix = "python-"
        line = _find_line_with_prefix("runtime.txt", prefix)
        if line:
            return _removeprefix(line, prefix)
        return None

    def get_pyproject_version(self):
        # Hacky version parser that works for the most common version specifiers
        line = _find_line_with_prefix("pyproject.toml", "requires-python")
        if line:
            return self._parse_version_specifier(line)
        return None

    def get_setup_py_version(self):
        line = _find_line_with_prefix("setup.py", "python_requires")
        if line:
            return self._parse_version_specifier(line)
        return None

    def get_setup_cfg_version(self):
        line = _find_line_with_prefix("setup.cfg", "python_requires")
        if line:
            return self._parse_version_specifier(line)
        return None

    def _parse_version_specifier(self, line):
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


def get_definitions():
    result = subprocess.run(["python-build", "--definitions"], capture_output=True)
    return [line.strip() for line in result.stdout.decode().splitlines()]


###########
#  UTILS  #
###########


def _removeprefix(s, prefix):
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


##########
#  MAIN  #
##########


main()
