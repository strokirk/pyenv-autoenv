## Version History

#### 2.2.1

* Fix autoenv not picking up `3.10+` as the "latest python version".

#### 2.2.0

* Add `--quiet` parameter.

* Add `--clear-if-lower` parameter.

#### 2.1.0

* Add autodetection of `setup.cfg` and `setup.py` Python version specifiers.

#### 2.0.0

* Add autodetection of `pyproject.toml` and `runtime.txt` Python version
    specifiers.

* Fixes for OSX `grep` incompatibility.

* The `--version` flag is now called `--python`, to make it possible
    to query the plugin version.

#### 1.0.0

* Initial public release.
