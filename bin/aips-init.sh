#!/bin/sh

# Init AIPS
if [ -z "$AIPS_ROOT" ]; then
    aips_login="/home/aips/LOGIN.SH"
    if [ -f "$aips_login" ]; then
        . "${aips_login}"
    else
        echo "Could not find LOGIN.SH. Please init AIPS environment manually."
    fi
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
