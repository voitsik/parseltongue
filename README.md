# ParselTongue

ParselTongue is a Python interface to classic AIPS.
It allows you to run AIPS tasks, and access AIPS headers and extension tables from Python.

## Installing ParselTongue

ParselTongue could be installed via pip:

```bash
pip install --user git+https://github.com/voitsik/parseltongue.git
```

## Using ParselTongue

The Python interface needs the environment variables:

```
AIPS_VERSION
DA00
LOAD
VERSION
```

These variables are normally set by `$AIPS_ROOT/LOGIN.SH`.

To do anything useful with AIPS, one also needs to set:

```
DA01
DA02
DA03
DA04
```

These are set by `$AIPS_VERSION/SYSTEM/UNIX/DADEVS.SH`.
