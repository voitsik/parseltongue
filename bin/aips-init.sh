#!/bin/sh

# Init AIPS
if [ -z "$AIPS_ROOT" ]; then
    . /home/aips/LOGIN.SH
fi

# If AIPS is available, make its data disks and printers available.
if [ -n "$AIPS_ROOT" ]; then
    if [ -z "$DADEVS_QUIET" ]; then
        DADEVS_QUIET=YES
        export DADEVS_QUIET
    fi
    . "$AIPS_VERSION/SYSTEM/UNIX/DADEVS.SH"
    . "$AIPS_VERSION/SYSTEM/UNIX/PRDEVS.SH"
fi
