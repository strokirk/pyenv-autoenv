# pyenv-autoenv

`pyenv-autoenv` is a [pyenv](https://github.com/pyenv/pyenv) plugin that
will automatically create and upgrade your project's virtualenv.

## Installation

Install using git:

```sh
$ git clone https://github.com/strokirk/pyenv-autoenv.git $(pyenv root)/plugins/pyenv-autoenv
```

Upgrade by removing and reinstalling, or with git:

```sh
$ git --git-dir $(pyenv root)/plugins/pyenv-autoenv/.git pull
```

## Usage

To create the virtualenv of a project, simply run `pyenv autoenv` and let
the magic happen.

It will create a virtualenv named after the current directory using the
latest available Python version.

To specify a specific Python version, use the `--python` flag.

```sh
$ pyenv autoenv --python 3.X.Y
```

To customize the name of the created virtualenv, use the `--name` flag.

```sh
$ pyenv autoenv --name venv-name
```

To recreate the virtualenv even if one already exists, use the `--clear` flag.

```sh
$ pyenv autoenv --clear
```
