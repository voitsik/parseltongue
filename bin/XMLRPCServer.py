#!/usr/bin/env python3

# Copyright (C) 2005, 2006 Joint Institute for VLBI in Europe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
This module provides a simple XML-RPC server that can run classic AIPS
tasks and provide verb-like access to AIPS data on a machine.
"""

import sys
from xmlrpc.server import SimpleXMLRPCServer

# Import AIPS modules.
from parseltongue.Proxy import AIPSData, AIPSTask


class XMLRPCServer(SimpleXMLRPCServer):
    allow_reuse_address = True


class ServerFuncs:
    def __init__(self):
        self.AIPSTask = AIPSTask.AIPSTask()
        self.AIPSUVData = AIPSData.AIPSUVData()
        self.AIPSImage = AIPSData.AIPSImage()
        self.AIPSCat = AIPSData.AIPSCat()

    def _dispatch(self, name, args):
        # For security reasons, SimpleXMLRPCServer in Python
        # 2.3.5/2.4.1, no longer resolves names with a dot in it. So
        # here we explicitly accept names starting with 'AIPS' and
        # containing a single dot; that should be safe enough.
        if name.startswith("AIPS") and name.count(".") == 1:
            name = name.split(".")
            inst = getattr(self, name[0])
            method = getattr(inst, name[1])
            return method(*args)
        msg = "object has no attribute '%s'" % name
        raise AttributeError(msg)


def main():
    with XMLRPCServer(("localhost", 8000), allow_none=True) as server:
        server.register_instance(ServerFuncs())

        # Run the server's main loop
        server.serve_forever()


if __name__ == "__main__":
    main()
