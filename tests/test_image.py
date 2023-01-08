import math

import pytest

from parseltongue.AIPSData import AIPSImage
from parseltongue.Wizardry.AIPSData import AIPSImage as WizAIPSImage


def test_image_fitld(image):
    assert len(image.stokes) == 1
    assert image.header.date_obs == '2005-03-01'
    assert image.header.telescop.rstrip() == 'EVN'


def test_image_history(image):
    count = 0
    for record in image.history:
        if record[0:5] == 'FRING':
            count += 1

    assert count > 5

    wimage = WizAIPSImage(image)
    history = wimage.history
    history.append('Something new!')
    history.close()

    image = AIPSImage(image)
    seen = 0
    for record in image.history:
        if record[0:5] == 'Somet':
            seen = 1

    assert seen


def test_image_pixels(image):
    wimage = WizAIPSImage(image)
    wimage.squeeze()
    wimage.pixels[0][0] = 0
    wimage.update()

    wimage = WizAIPSImage(image)
    wimage.squeeze()
    assert wimage.pixels[0][0] == 0


def test_image_keywords(image):
    # Check AIPSImage.keywords is just as a python dict
    assert isinstance(image.keywords, dict)
    image.keywords['PI'] = math.pi
    image.keywords.update()

    # Values set in image.keywords do not propagate to real data
    image = AIPSImage(image)
    with pytest.raises(KeyError):
        image.keywords['PI'] == pytest.approx(math.pi)

    wimage = WizAIPSImage(image)

    parangle = wimage.keywords['PARANGLE']
    wimage.keywords['PARANGLE'] *= 2
    wimage.keywords['PI'] = math.pi
    wimage.keywords['ARRNAM'] = 'EVN'
    wimage.keywords.update()

    image = AIPSImage(image)
    assert image.keywords['PARANGLE'] == 2 * parangle
    assert image.keywords['PI'] == pytest.approx(math.pi)
    arrnam = image.keywords['ARRNAM']
    assert arrnam.strip() == 'EVN'
