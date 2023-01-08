import re

import pytest

from parseltongue.AIPSData import AIPSCat, AIPSImage
from parseltongue.AIPSTask import AIPSTask


@pytest.fixture
def image(userno):
    image = AIPSImage("MANDELBROT", "MANDL", 1, 1)
    if image.exists():
        image.zap()

    yield image

    if image.exists():
        image.zap()


def test_cat(image):
    """Test AIPSCat class."""
    AIPSCat(1).zap()
    mandl = AIPSTask("mandl")
    mandl.outdata = image
    mandl.imsize[1:] = [512, 512]
    mandl.go()

    mandl.outclass = "TEMP"
    mandl.go()

    cat = AIPSCat(1)
    assert len(cat) == 2

    # disk -> num -> param
    assert cat[1][0]["name"] == "MANDELBROT"
    assert cat[1][0]["klass"] == "MANDL"
    assert cat[1][0]["seq"] == 1
    assert cat[1][1]["name"] == "MANDELBROT"
    assert cat[1][1]["klass"] == "TEMP"
    assert cat[1][1]["seq"] == 1

    with pytest.raises(
        TypeError,
        match=re.escape("zap() got an unexpected keyword argument(s): 'klaas'"),
    ):
        AIPSCat(1).zap(klaas="TEMP")

    AIPSCat(1).zap(klass="TEMP")

    assert len(AIPSCat(1)) == 1

    AIPSCat(1).zap()

    assert len(AIPSCat(1)) == 0
