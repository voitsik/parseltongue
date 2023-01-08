# import signal
# import time

import pytest
from obit import OErr
from parseltongue.AIPSData import AIPSUVData
from parseltongue.AIPSTask import AIPSMessageLog


def test_zap_nonexistent_data(userno):
    test_data = AIPSUVData("TEST", "UVDATA", 1, 1, userno)

    assert not test_data.exists()

    with pytest.raises(OErr.ObitError, match="Error finding AIPS catalog entry"):
        assert test_data.zap()


def test_zap_nonexistent_table(uvdata):
    # Zapping non-existent table is OK
    assert [1, "AIPS QQ"] not in uvdata.tables
    assert uvdata.zap_table("QQ", 1)


def test_zap_table_nonexistent_data(userno):
    test_data = AIPSUVData("TEST", "UVDATA", 1, 1, userno)

    with pytest.raises(OErr.ObitError, match="Error finding AIPS catalog entry"):
        assert [1, "AIPS QQ"] not in test_data.tables

    with pytest.raises(OErr.ObitError, match="Error finding AIPS catalog entry"):
        assert test_data.zap_table("QQ", 1)


### Code from zap3.py
# def test_zap(uvdata, tv):
#     uvplt = AIPSTask("uvplt")
#     uvplt.indata = uvdata
#     uvplt.dotv = 1
#     job = uvplt.spawn()
#     time.sleep(5)

#     uvplt.abort(job[0], job[1], sig=signal.SIGKILL)

#     uvdata.zap()

#     assert uvdata.exists()


def test_zap(uvdata):
    assert uvdata.exists()
    uvdata.zap()
    assert not uvdata.exists()


@pytest.mark.usefixtures("userno")
def test_zap_msglog():
    msglog = AIPSMessageLog()
    assert msglog.zap()
