import time

from parseltongue.AIPSTask import AIPSTask


def test_kntr(image, tv):
    assert tv.running()

    kntr = AIPSTask('kntr')
    kntr.indata = image
    kntr.docont = 0
    kntr.dovect = 0
    kntr.dotv = 1
    kntr.go()

    time.sleep(2)
