import os

import pytest

from parseltongue import AIPS
from parseltongue.AIPSData import AIPSUVData, AIPSImage
from parseltongue.AIPSTask import AIPSTask
from parseltongue.AIPSTV import AIPSTV


@pytest.fixture(scope="module")
def uv_file():
    return os.path.join(os.path.dirname(__file__), "data", "n03l1_1_1.IDI1")


@pytest.fixture(scope="module")
def image_file():
    return os.path.join(os.path.dirname(__file__), "data", "n05l1_4C39.25_ICLN.FITS")


@pytest.fixture(scope="module")
def userno():
    AIPS.userno = 1999

    return AIPS.userno


@pytest.fixture(scope="module")
def tv():
    tv = AIPSTV()
    tv.start()

    yield tv

    tv.kill()


@pytest.fixture(scope="module")
def uvdata(uv_file, userno):
    name = os.path.basename(uv_file).split("_")[0].upper()
    uvdata = AIPSUVData(name, "UVDATA", 1, 1, userno)
    if uvdata.exists():
        uvdata.zap()

    fitld = AIPSTask("fitld")
    fitld.datain = uv_file
    fitld.outdata = uvdata
    fitld.msgkill = 2
    fitld.go()

    yield uvdata

    if uvdata.exists():
        uvdata.zap(force=True)


@pytest.fixture(scope="module")
def image(image_file, userno):
    name = os.path.basename(image_file).split("_")[0].upper()
    image = AIPSImage(name, "ICLN", 1, 1, userno)
    if image.exists():
        image.zap()

    fitld = AIPSTask("fitld")
    fitld.datain = image_file
    fitld.outdata = image
    fitld.msgkill = 2
    fitld.go()

    yield image

    if image.exists():
        image.zap()
