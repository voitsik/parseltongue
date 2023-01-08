import pytest

from parseltongue import AIPS
from parseltongue.AIPSData import AIPSImage
from parseltongue.AIPSTask import AIPSTask


@pytest.fixture(scope="function")
def image(userno):
    image = AIPSImage("MANDELBROT", "MANDL", 1, 1)
    if image.exists():
        image.zap()

    yield image

    if image.exists():
        image.zap()


@pytest.fixture(scope="function")
def image2(userno):
    image2 = AIPSImage("MANDELBROT", "MANDL", 1, 1, 2)
    if image2.exists():
        image2.zap()

    yield image2

    if image2.exists():
        image2.zap()


@pytest.fixture(scope="function")
def image_mandl512(image):
    mandl = AIPSTask("mandl")
    mandl.outdata = image
    mandl.imsize[1:] = [512, 512]
    mandl.go()

    yield image

    if image.exists():
        image.zap()


@pytest.fixture(scope="function")
def image_mandl64(image):
    mandl = AIPSTask("mandl")
    mandl.outdata = image
    mandl.imsize[1:] = [64, 64]
    mandl.go()

    yield image

    if image.exists():
        image.zap()


def test_mandl(image_mandl512):
    """Test MANDL task."""
    assert image_mandl512.tables[0] == [1, "AIPS HI"]

    header = image_mandl512.header
    assert header.naxis[0] == 512
    assert header.naxis[1] == 512


def test_userno(image, image2):
    """Test setting userno globally and as parameter."""
    mandl = AIPSTask("mandl")
    mandl.userno = 2
    mandl.outdata = image
    mandl.imsize[1:] = [512, 512]
    mandl.go()

    assert not image.exists()
    assert image2.exists()

    AIPS.userno = 2
    image3 = AIPSImage("MANDELBROT", "MANDL", 1, 1)
    assert image3.exists()


def test_imean(image_mandl512):
    """Test IMEAN task."""
    imean = AIPSTask("imean")
    imean.indata = image_mandl512
    imean.blc[1:] = [128, 128]
    imean.trc[1:] = [256, 256]
    imean.go()

    assert imean.pixavg == pytest.approx(2229.293457)
    assert imean.pixstd == pytest.approx(708.026855)


def test_jmfit(image_mandl64):
    """Test JMFIT task."""
    jmfit = AIPSTask("jmfit")
    jmfit.indata = image_mandl64
    jmfit.ngauss = 4
    jmfit.domax[1:] = [1, 0, 0, 0]
    jmfit.go()

    assert jmfit.fmax[1] == pytest.approx(-121.07095)
    assert jmfit.fmax[2] == pytest.approx(25.4)
    assert jmfit.fmax[3] == pytest.approx(25.4)
    assert jmfit.fmax[4] == pytest.approx(25.4)


def test_table_zap(image_mandl512):
    """Test zapping nonexistent table?"""
    assert image_mandl512.header.datamax == 254.0
    image_mandl512.zap_table("PL", -1)
    assert image_mandl512.header.datamax == 254.0
