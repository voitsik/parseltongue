from parseltongue.AIPSTask import AIPSTask
from parseltongue.Wizardry.AIPSData import AIPSUVData as WizAIPSUVData


def test_indxr_uvdata(uvdata):
    num_tables = len(uvdata.tables)
    uvdata.zap_table('NX', 1)
    assert len(uvdata.tables) == num_tables - 1

    indxr = AIPSTask('indxr')
    indxr.indata = uvdata
    indxr()

    assert len(uvdata.tables) == num_tables


def test_indxr_wiz(uvdata):
    num_tables = len(uvdata.tables)

    wuvdata = WizAIPSUVData(uvdata)
    wuvdata.zap_table('NX', 1)
    assert len(wuvdata.tables) == num_tables - 1

    indxr = AIPSTask('indxr')
    indxr.indata = wuvdata
    indxr()

    assert len(wuvdata.tables) == num_tables
