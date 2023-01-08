import os

import pytest

from parseltongue.AIPSData import AIPSUVData
from parseltongue.AIPSTask import AIPSTask


@pytest.fixture(scope="module")
def input_file():
    return os.path.join(os.path.dirname(__file__), "data", "VLBA1.UVCON")


@pytest.fixture(scope="module")
def uvdata(userno):
    name = 'UVCON'
    uvdata = AIPSUVData(name, 'UVDATA', 1, 1)

    if uvdata.exists():
        uvdata.zap()

    yield uvdata

    if uvdata.exists():
        uvdata.zap()


def test_uvcon(uvdata, input_file):
    assert not uvdata.exists()

    uvcon = AIPSTask('uvcon')
    uvcon.outdata = uvdata
    uvcon.infile = input_file
    uvcon.smodel = [None, 1.0, 0.0, 0.0, 0]
    uvcon.aparm = [None, 1.4, 0, 30, -12, 12, 0, 120, 1, 1]
    uvcon.bparm = [None, -1, 0, 0, 0, 0]
    uvcon()

    assert uvdata.exists()
    assert len(uvdata.tables) == 2
