import math

import pytest

from parseltongue.AIPSTask import AIPSTask
from parseltongue.Wizardry.AIPSData import AIPSUVData as WizAIPSUVData


class TestUV:
    def test_uvdata(self, uvdata):
        assert len(uvdata.antennas) == 4
        assert len(uvdata.polarizations) == 2
        assert len(uvdata.sources) == 2
        assert len(uvdata.stokes) == 4
        assert len(uvdata) == 36033

        assert uvdata.header.date_obs == "2003-02-25"

    def test_uvdata_tables(self, uvdata):
        sutable = uvdata.table("SU", 1)
        assert sutable.version == 1
        assert sutable[0].epoch == 2000.0

        antable = uvdata.table("AN", 0)
        assert antable.version == 1
        stabxyz = antable[3].stabxyz
        assert 3822846 < stabxyz[0] < 3822847

        cltable = uvdata.table("CL", 0)
        start = cltable[0].time

        nxtable = uvdata.table("NX", 0)
        for row in nxtable:
            assert row.time >= start
        for row in nxtable:
            assert sutable[row.source_id - 1].id__no == row.source_id

        start2 = cltable[0]["time"]
        assert start2 == start

    def test_uvdata_history(self, uvdata):
        count = 0

        for record in uvdata.history:
            # print(record)
            if record[0:5] == "FITLD":
                count += 1

        assert count > 5

    # def test_uvdata_indxr(self, uvdata):
    #     num_tables = len(uvdata.tables)

    #     uvdata.zap_table("NX", 1)

    #     assert len(uvdata.tables) == num_tables - 1

    #     indxr = AIPSTask("indxr")
    #     indxr.indata = uvdata
    #     indxr()

    #     assert len(uvdata.tables) == num_tables

    def test_uvdata_table_zap(self, uvdata):
        assert uvdata.table_highver("NX") == 1
        uvdata.table("NX", 0).zap()
        assert uvdata.table_highver("NX") == 0

    def test_uvdata_table_copy_zap(self, uvdata):
        tacop = AIPSTask("tacop")
        tacop.indata = uvdata
        tacop.outdata = uvdata
        tacop.inext = "CL"
        tacop.invers = 1
        tacop.outvers = 3
        tacop()

        assert [3, "AIPS CL"] in uvdata.tables

        uvdata.zap_table("CL", 1)

        assert [3, "AIPS CL"] in uvdata.tables
        assert [1, "AIPS CL"] not in uvdata.tables


class TestWiz:
    """Test Wizardry module."""

    def test_wiz_properties(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)

        assert wuvdata.antennas == ["MC", "WB", "NT", "JB"]
        assert wuvdata.polarizations == ["R", "L"]
        assert wuvdata.sources == ["3C84", "DA193"]

    def test_wiz_uvdata(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)
        count = 0
        inttim = 0
        for vis in wuvdata:
            inttim += vis.inttim
            count += 1

        assert len(wuvdata) == count
        assert inttim == 144132.0

    def test_wiz_uvdata2a(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)
        for vis in wuvdata:
            vis.visibility[0][0][0][2] = 1.234
            vis.update()

    def test_wiz_uvdata2b(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)
        for vis in wuvdata:
            assert vis.visibility[0][0][0][2] > 1.233
            assert vis.visibility[0][0][0][2] < 1.235

    def test_wiz_uvdata3(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)

        assert wuvdata[3].baseline == [1, 1]
        assert wuvdata[4].baseline == [1, 4]
        assert wuvdata[3].baseline == [1, 1]
        assert wuvdata[2167].baseline == [2, 4]
        assert wuvdata[3].baseline == [1, 1]

    def test_wiz_uvdata4(self, uvdata, userno):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1, userno)

        count = 0
        inttim = 0
        for vis in wuvdata[10:20]:
            inttim += vis.inttim
            count += 1

        assert count == 10
        assert inttim == 40.0

        count = 0
        inttim = 0
        for vis in wuvdata[30000:]:
            assert vis.time > 0.746901
            inttim += vis.inttim
            count += 1

        assert count == (len(uvdata) - 30000)
        assert inttim == 24132.0

        count = 0
        for vis in wuvdata[30000:-10]:
            count += 1

        assert count == (len(uvdata) - 30010)

    # def test_wiz_indxr(self, uvdata):
    #     wuvdata = WizAIPSUVData(uvdata)
    #     num_tables = len(wuvdata.tables)

    #     wuvdata.zap_table("NX", 1)

    #     assert len(wuvdata.tables) == num_tables - 1

    #     indxr = AIPSTask("indxr")
    #     indxr.indata = wuvdata
    #     indxr()

    #     assert len(wuvdata.tables) == num_tables

    def test_wiz_table_copy_zap(self, uvdata):
        tacop = AIPSTask("tacop")
        tacop.indata = uvdata
        tacop.outdata = uvdata
        tacop.inext = "CL"
        tacop.invers = 3
        tacop.outvers = 5
        tacop()

        uvdata2 = WizAIPSUVData(uvdata.name, uvdata.klass, uvdata.disk, uvdata.seq)

        assert [5, "AIPS CL"] in uvdata2.tables

        uvdata2.zap_table("CL", 0)

        assert [5, "AIPS CL"] not in uvdata2.tables
        assert [3, "AIPS CL"] in uvdata2.tables
        assert [1, "AIPS CL"] not in uvdata2.tables

        count = 0
        for cl in uvdata2.table("CL", 3):
            count += 1

        assert count > 0

    def test_wiz_history(self, uvdata):
        wuvdata = WizAIPSUVData(uvdata)
        history = wuvdata.history
        history.append("Something new!")
        history.close()

        # uvdata = AIPSUVData(uvdata)
        seen = False
        for record in uvdata.history:
            # print(record)
            if record[0:5] == "Somet":
                seen = True

        assert seen

    def test_wiz_keywords_read(self, uvdata):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1)

        antable = wuvdata.table("AN", 0)
        arrnam = antable.keywords["ARRNAM"]
        assert arrnam.strip() == "EVN"
        assert antable.keywords["FREQID"] == -1
        assert antable.keywords["FREQ"] == 1642490000.0
        assert antable.keywords["IATUTC"] != 33.0

    def test_wiz_keywords_write(self, uvdata):
        wuvdata = WizAIPSUVData(uvdata.name, "UVDATA", 1, 1)

        antable = wuvdata.table("AN", 0)

        antable.keywords["ARRNAM"] = "VLBA"
        antable.keywords["FREQID"] = 1
        antable.keywords["FREQ"] = 4974990000.0
        antable.keywords["IATUTC"] = 33.0

        # Create new keywords
        antable.keywords["E"] = math.e
        antable.keywords["OPERATOR"] = "NRAO"
        antable.close()

        antable = uvdata.table("AN", 0)
        arrnam = antable.keywords["ARRNAM"]
        assert arrnam.strip() == "VLBA"
        assert antable.keywords["FREQID"] == 1
        assert antable.keywords["FREQ"] == 4974990000.0
        assert antable.keywords["IATUTC"] == 33.0
        assert antable.keywords["E"] == pytest.approx(math.e)
        operator = antable.keywords["OPERATOR"]
        assert operator.strip() == "NRAO"
