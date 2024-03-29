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

import numpy as np

# Obit stuff.
from obit import History, InfoList, Obit, OErr, OSystem, Table, TableList


def _array(sequence, shape):
    arr = np.frombuffer(sequence, dtype=np.float32)

    return arr.reshape(shape)


def _scalarize(value):
    """Scalarize a value.

    If `value` is a list that consists of a single element, return that
    element.  Otherwise return `value`.
    """
    if isinstance(value, list) and len(value) == 1:
        return value[0]

    return value


def _vectorize(value):
    """Vectorize a value.

    If `value` is a scalar, return a list consisting of that scalar.
    Otherwise return `value`.
    """
    if not isinstance(value, list):
        return [value]

    return value


def _rstrip(value):
    """Strip trailing whitespace."""
    if isinstance(value, list):
        return [str.rstrip() for str in value]

    return value.rstrip()


class _AIPSTableRow:
    """This class is used to access rows in an extension table."""

    def __init__(self, table, fields, rownum, err):
        self._err = err
        self._table = table
        self._fields = fields
        self._rownum = rownum
        if self._rownum >= 0:
            assert not self._err.isErr
            self._row = self._table.ReadRow(self._rownum + 1, self._err)
            if not self._row:
                raise IndexError("list index out of range")
            if self._err.isErr:
                raise OErr.ObitError("Reading row")

    def __str__(self):
        return str(self._generate_dict())

    def _generate_dict(self):
        dict = {}
        for name in self._fields:
            if name.startswith("_"):
                continue
            dict[name] = getattr(self, name)

        return dict

    def _findattr(self, name):
        """Return the field name corresponding to attribute NAME."""
        if name in self._fields:
            return self._fields[name]
        msg = f"{self.__class__.__name__} instance has no attribute '{name}'"
        raise AttributeError(msg)

    def __getattr__(self, name):
        key = self._findattr(name)
        return _scalarize(self._row[key])

    def __setattr__(self, name, value):
        if name.startswith("_"):
            self.__dict__[name] = value
            return
        key = self._findattr(name)
        self._row[key] = _vectorize(value)
        pass

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setitem__(self, name, value):
        self.__setattr__(name, value)

    def update(self):
        """Update this row."""
        assert not self._err.isErr
        self._table.WriteRow(self._rownum + 1, self._row, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Updating row")


# class _AIPSTableRow


class AIPSTableRow(_AIPSTableRow):
    """This class is used as a template row for an extension table."""

    def __init__(self, table):
        _AIPSTableRow.__init__(self, table._table, table._columns, -1, table._err)
        header = table._table.Desc.Dict
        self._row = {}
        self._row["Table name"] = header["Table name"]
        self._row["NumFields"] = len(header["FieldName"])
        desc = zip(header["FieldName"], header["type"], header["repeat"])

        for field, type_, repeat in desc:
            if type_ in (1, 2, 3, 4):
                # Integer.
                self._row[field] = repeat * [0]
            elif type_ in (10, 11):
                # Floating-point number.
                self._row[field] = repeat * [0.0]
            elif type_ == 14:
                # String.
                self._row[field] = ""
            elif type_ == 15:
                # Boolean.
                self._row[field] = repeat * [False]
            else:
                msg = f"Unimplemented type {type_} for field {field}"
                raise NotImplementedError(msg)

    def update(self):
        # A row instantiated by the AIPSTableRow class cannot be updated.
        msg = "%s instance has no attribute 'update'" % self.__class__.__name__
        raise AttributeError(msg)


# AIPSTableRow


class _AIPSTableIter(_AIPSTableRow):
    """This class is used as an iterator over rows in an extension table."""

    def __init__(self, table, fields, err):
        _AIPSTableRow.__init__(self, table, fields, -1, err)

    def __next__(self):
        """Return the next row."""
        self._rownum += 1
        assert not self._err.isErr
        self._row = self._table.ReadRow(self._rownum + 1, self._err)
        if not self._row:
            self._err.Clear()
            raise StopIteration
        assert not self._err.isErr

        return self


# class _AIPSTableIter


class _AIPSTableKeywords:
    def __init__(self, table, err):
        self._err = err
        self._table = table

    def __getitem__(self, key):
        key = key.upper().ljust(8)
        value = InfoList.PGet(self._table.IODesc.List, key)
        return _scalarize(value[4])

    def __setitem__(self, key, value):
        key = key.upper().ljust(8)

        try:
            _type = InfoList.PGet(self._table.IODesc.List, key)[2]
        except KeyError as exc:
            # New keys are either strings or floats.
            if isinstance(value, str):
                _type = 14  # OBIT_string == 14
            else:
                _type = 10  # OBIT_float == 10

        if _type in (2, 3, 4):
            value = int(value)
            InfoList.PAlwaysPutInt(
                self._table.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
            InfoList.PAlwaysPutInt(
                self._table.IODesc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 10:
            value = float(value)
            InfoList.PAlwaysPutFloat(
                self._table.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
            InfoList.PAlwaysPutFloat(
                self._table.IODesc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 11:
            value = float(value)
            InfoList.PAlwaysPutDouble(
                self._table.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
            InfoList.PAlwaysPutDouble(
                self._table.IODesc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 14:
            value = str(value).ljust(8)
            InfoList.PAlwaysPutString(
                self._table.Desc.List, key, [8, 1, 1, 1, 1], _vectorize(value)
            )
            InfoList.PAlwaysPutString(
                self._table.IODesc.List, key, [8, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 15:
            value = bool(value)
            InfoList.PAlwaysPutBoolean(
                self._table.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
            InfoList.PAlwaysPutBoolean(
                self._table.IODesc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        else:
            raise NotImplementedError("not implemented")
        Table.PDirty(self._table)

    def _generate_dict(self):
        dict_ = {}
        for key in self._table.IODesc.List.Dict:
            if self._table.IODesc.List.Dict[key][0] == 14:
                dict_[key] = self._table.IODesc.List.Dict[key][2][0]
            else:
                dict_[key] = _scalarize(self._table.IODesc.List.Dict[key][2])

        return dict_

    def __str__(self):
        return str(self._generate_dict())


# class _AIPSTableKeywords


class _AIPSTable:
    """This class is used to access extension tables to an AIPS UV data set."""

    def __init__(self, data, name, version):
        if not name.startswith("AIPS "):
            name = f"AIPS {name}"

        self._err = OErr.OErr()

        if version == 0:
            version = TableList.PGetHigh(data.TableList, name)

        tables = TableList.PGetList(data.TableList, self._err)
        if [version, name] not in tables:
            msg = name + " table"
            if version:
                msg += f" version {version}"

            msg += " does not exist"
            raise FileNotFoundError(msg)

        self._table = data.NewTable(3, name, version, self._err)
        self._table.Open(3, self._err)

        if self._err.isErr:
            raise OErr.ObitError("Opening table")

        header = self._table.Desc.Dict
        self._columns = {}
        self._keys = []
        for column in header["FieldName"]:
            # Convert the AIPS column names into acceptable Python
            # identifiers.
            key = column.lower()
            key = key.replace(" ", "_")
            key = key.rstrip(".")
            key = key.replace(".", "_")
            self._columns[key] = column
            self._keys.append(key)

        self.name = name
        self.version = header["version"]

    def close(self):
        """Close this extension table.

        Closing an extension table flushes any changes to the table to
        disk and updates the information in the header of the data
        set.
        """
        assert not self._err.isErr
        # Reopen the file to make sure the keywords are updated.
        self._table.Open(3, self._err)
        self._table.Close(self._err)
        if self._err.isErr:
            raise OErr.ObitError("Closing table")

    # The following functions make an extension table behave as a list
    # of rows.

    def __getitem__(self, key):
        if key < 0:
            key = len(self) - key
        return _AIPSTableRow(self._table, self._columns, key, self._err)

    def __iter__(self):
        return _AIPSTableIter(self._table, self._columns, self._err)

    def __len__(self):
        return self._table.Desc.Dict["nrow"]

    def __setitem__(self, key, row):
        if key < 0:
            key = len(self) - key
        assert not self._err.isErr
        self._table.WriteRow(key + 1, row._row, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Writing row")

    def append(self, row):
        """Append a row to this extension table."""
        assert not self._err.isErr
        self._table.WriteRow(len(self) + 1, row._row, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Appending table row")

    @property
    def keywords(self):
        """Keywords for this table."""
        return _AIPSTableKeywords(self._table, self._err)

# class _AIPSTable


class _AIPSHistory:
    """This class is used to access AIPS history tables."""

    def __init__(self, data):
        self._err = OErr.OErr()
        self._table = History.History("AIPS HI", data.List, self._err)
        self._table.Open(3, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Opening history")

    def close(self):
        """Close this history table.

        Closing a history table flushes any changes to the table to
        disk and updates the information in the header of the data
        set."""
        self._table.Close(self._err)
        if self._err.isErr:
            raise OErr.ObitError("Closing history")

    # The following functions make an extension table behave as a list
    # of records.

    def __getitem__(self, key):
        assert not self._err.isErr
        record = self._table.ReadRec(key + 1, self._err)
        if not record:
            raise IndexError("list index out of range")
        if self._err.isErr:
            raise OErr.ObitError("Reading history")
        return record

    def __setitem__(self, key, record):
        msg = "You are not allowed to rewrite history!"
        raise NotImplementedError(msg)

    def append(self, record):
        """Append a record to this history table."""

        assert not self._err.isErr
        self._table.WriteRec(0, record, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Appending history")

# class _AIPSHistory


class _AIPSVisibility:
    """This class is used as an iterator over visibilities."""

    def __init__(self, data, err, index):
        self._err = err
        self._data = data
        self._index = -1
        self._desc = self._data.Desc.Dict
        self._ant1 = None
        self._ant2 = None
        self._subarray = None
        if self._desc["ilocb"] == -1:
            try:
                self._ant1 = self._desc["ptype"].index("ANTENNA1")
                self._ant2 = self._desc["ptype"].index("ANTENNA2")
                self._subarray = self._desc["ptype"].index("SUBARRAY")
            except BaseException:
                pass

        self._first = 0
        self._count = 0
        self._flush = False
        if index > -1:
            shape = len(self._data.VisBuf) // 4
            self._buffer = _array(self._data.VisBuf, shape)
            self._first = self._data.Desc.Dict["firstVis"] - 1
            self._count = self._data.Desc.Dict["numVisBuff"]
            count = InfoList.PGet(self._data.List, "nVisPIO")[4][0]
            self._buffer.shape = (count, -1)

            if (
                self._first < 0
                or index < self._first
                or index >= self._first + self._count
            ):
                self._fill(index)

            self._index = index - self._first

    def _fill(self, index=None):
        if self._flush:
            assert self._first == self._data.Desc.Dict["firstVis"] - 1
            Obit.UVRewrite(self._data.me, self._err.me)
            if self._err.isErr:
                raise OErr.ObitError("Obit.UVRewrite")
            self._flush = False

        if index:
            d = self._data.IODesc.Dict
            count = InfoList.PGet(self._data.List, "nVisPIO")[4][0]
            d["firstVis"] = max(0, index - count + 1)
            self._data.IODesc.Dict = d

        Obit.UVRead(self._data.me, self._err.me)
        if self._err.isErr:
            raise OErr.ObitError("Reading UV")
        shape = len(self._data.VisBuf) // 4
        self._buffer = _array(self._data.VisBuf, shape)
        self._first = self._data.Desc.Dict["firstVis"] - 1
        self._count = self._data.Desc.Dict["numVisBuff"]
        count = InfoList.PGet(self._data.List, "nVisPIO")[4][0]
        self._buffer.shape = (count, -1)
        self._index = 0

    def update(self):
        self._flush = True

    def _get_uvw(self):
        u = self._buffer[self._index][self._desc["ilocu"]]
        v = self._buffer[self._index][self._desc["ilocv"]]
        w = self._buffer[self._index][self._desc["ilocw"]]
        return [u, v, w]

    def _set_uvw(self, value):
        self._buffer[self._index][self._desc["ilocu"]] = value[0]
        self._buffer[self._index][self._desc["ilocv"]] = value[1]
        self._buffer[self._index][self._desc["ilocw"]] = value[2]

    uvw = property(_get_uvw, _set_uvw)

    def _get_time(self):
        return self._buffer[self._index][self._desc["iloct"]]

    def _set_time(self, value):
        self._buffer[self._index][self._desc["iloct"]] = value

    time = property(_get_time, _set_time)

    def _get_baseline(self):
        if self._ant1 and self._ant2:
            ant1 = int(self._buffer[self._index][self._ant1])
            ant2 = int(self._buffer[self._index][self._ant2])
            return [ant1, ant2]
        baseline = int(self._buffer[self._index][self._desc["ilocb"]])
        return [baseline / 256, baseline % 256]

    def _set_baseline(self, value):
        if self._ant1 and self._ant2:
            self._buffer[self._index][self._ant1] = value[0]
            self._buffer[self._index][self._ant2] = value[1]
            return
        baseline = value[0] * 256 + value[1] + (self.subarray - 1) * 0.01
        self._buffer[self._index][self._desc["ilocb"]] = baseline

    baseline = property(_get_baseline, _set_baseline)

    def _get_subarray(self):
        if self._subarray:
            return int(self._buffer[self._index][self._subarray])
        ilocb = self._buffer[self._index][self._desc["ilocb"]]
        return int((ilocb - int(ilocb)) * 100 + 0.5) + 1

    def _set_subarray(self, value):
        if self._subarray:
            self._buffer[self._index][self._subarray] = value
            return
        baseline = int(self._buffer[self._index][self._desc["ilocb"]])
        ilocb = baseline + (value - 1) * 0.01
        self._buffer[self._index][self._desc["ilocb"]] = ilocb

    subarray = property(_get_subarray, _set_subarray)

    def _get_source(self):
        rnd_indx = self._desc["ilocsu"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        return self._buffer[self._index][rnd_indx]

    def _set_source(self, value):
        rnd_indx = self._desc["ilocsu"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        self._buffer[self._index][rnd_indx] = value

    source = property(_get_source, _set_source)

    def _get_freqsel(self):
        rnd_indx = self._desc["ilocfq"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        return self._buffer[self._index][rnd_indx]

    def _set_freqsel(self, value):
        rnd_indx = self._desc["ilocfq"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        self._buffer[self._index][rnd_indx] = value
        return

    freqsel = property(_get_freqsel, _set_freqsel)

    def _get_inttim(self):
        return self._buffer[self._index][self._desc["ilocit"]]

    def _set_inttim(self, value):
        self._buffer[self._index][self._desc["ilocit"]] = value
        return

    inttim = property(_get_inttim, _set_inttim)

    def _get_corrid(self):
        rnd_indx = self._desc["ilocid"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        return self._buffer[self._index][rnd_indx]

    def _set_corrid(self, value):
        rnd_indx = self._desc["ilocid"]
        if rnd_indx == -1:
            raise KeyError("Random Parameter not present")
        self._buffer[self._index][rnd_indx] = value
        return

    corrid = property(_get_corrid, _set_corrid)

    def _get_visibility(self):
        visibility = self._buffer[self._index][self._desc["nrparm"] :]
        inaxes = self._desc["inaxes"]
        shape = (inaxes[3], inaxes[2], inaxes[1], inaxes[0])
        visibility.shape = shape
        return visibility

    def _set_visibility(self, value):
        value = value.ravel()
        self._buffer[self._index][self._desc["nrparm"] :] = value

    visibility = property(_get_visibility, _set_visibility)

    pass  # class _AIPSVisibility


class _AIPSVisibilityIter(_AIPSVisibility):
    def __init__(self, data, err, ranges=None):
        if data.Desc.Dict["firstVis"] > 0:
            data.Open(3, err)

        _AIPSVisibility.__init__(self, data, err, -1)
        self._len = self._desc["nvis"]
        if not ranges:
            ranges = [(0, self._len)]

        self._ranges = ranges
        self._range = self._ranges.pop(0)

    def __next__(self):
        self._index += 1
        if self._index + self._first > self._range[1]:
            try:
                self._range = self._ranges.pop(0)
            except Exception:
                pass

        while self._first + self._count < self._range[0]:
            self._fill()

        if self._index + self._first < self._range[0]:
            self._index = self._range[0] - self._first

        if self._index + self._first >= self._range[1]:
            if self._flush:
                Obit.UVWrite(self._data.me, self._err.me)
                if self._err.isErr:
                    raise OErr.ObitError("Writing UV data")
                self._flush = False
            raise StopIteration
        if self._index >= self._count:
            self._fill()
        return self


# class _AIPSVisibilityIter


class _AIPSVisibilitySel:
    def __init__(self, data, source):
        self._data = data

        self._ranges = []
        for row in data.table("SU", 0):
            if source == row.source.strip():
                source_id = row.id__no
                break

        for row in data.table("NX", 0):
            if source_id == row.source_id:
                self._ranges.append((row.start_vis - 1, row.end_vis - 1))

    def __iter__(self):
        return _AIPSVisibilityIter(self._data._data, self._data._err, self._ranges)


class _AIPSVisibilitySlice:
    def __init__(self, data, slice):
        self._data = data

        start = 0
        stop = len(data)
        if slice.start:
            if slice.start < 0:
                start = len(data) + slice.start
            else:
                start = slice.start

        if slice.stop:
            if slice.stop < 0:
                stop = len(data) + slice.stop
            else:
                stop = slice.stop

        if slice.step and not slice.step == 1:
            msg = "Stride %d is not supported" % slice.step
            raise NotImplementedError(msg)
        self._ranges = [(start, stop)]

    def __iter__(self):
        return _AIPSVisibilityIter(self._data._data, self._data._err, self._ranges)


class _AIPSDataKeywords:
    def __init__(self, data, obit, err):
        self._err = err
        self._data = data
        self._obit = obit

    def __getitem__(self, key):
        key = key.upper().ljust(8)
        value = InfoList.PGet(self._data.Desc.List, key)
        return _scalarize(value[4])

    def __setitem__(self, key, value):
        key = key.upper().ljust(8)
        try:
            _type = InfoList.PGet(self._data.Desc.List, key)[2]
        except KeyError:
            # New keys are either strings or floats.
            if isinstance(value, str):
                _type = 14  # OBIT_string == 14
            else:
                _type = 10  # OBIT_float == 10

        if _type in (2, 3, 4):
            value = int(value)
            InfoList.PAlwaysPutInt(
                self._data.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 10:
            value = float(value)
            InfoList.PAlwaysPutFloat(
                self._data.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 11:
            value = float(value)
            InfoList.PAlwaysPutDouble(
                self._data.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 14:
            value = str(value).ljust(8)
            InfoList.PAlwaysPutString(
                self._data.Desc.List, key, [8, 1, 1, 1, 1], _vectorize(value)
            )
        elif _type == 15:
            value = bool(value)
            InfoList.PAlwaysPutBoolean(
                self._data.Desc.List, key, [1, 1, 1, 1, 1], _vectorize(value)
            )
        else:
            raise NotImplementedError("not implemented")
        self._obit.PDirty(self._data)

    def _generate_dict(self):
        dict_ = {}
        for key in self._data.Desc.List.Dict:
            if self._data.Desc.List.Dict[key][0] == 14:
                dict_[key] = self._data.Desc.List.Dict[key][2][0]
            else:
                dict_[key] = _scalarize(self._data.Desc.List.Dict[key][2])

        return dict_

    def __str__(self):
        return str(self._generate_dict())

    def update(self):
        self._obit.PUpdateDesc(self._data, self._err)


# class _AIPSDataKeywords


class _AIPSDataHeader:
    def __init__(self, data, obit, err):
        self._err = err
        self._data = data
        self._obit = obit
        self._dict = data.Desc.Dict
        for key in self._strip:
            if self._keys[key] in self._dict:
                value = _rstrip(self._dict[self._keys[key]])
                self._dict[self._keys[key]] = value

    _keys = {
        "object": "object",
        "telescop": "teles",
        "instrume": "instrume",
        "observer": "observer",
        "date_obs": "obsdat",
        "date_map": "date",
        "bunit": "bunit",
        "ndim": "naxis",
        "naxis": "inaxes",
        "epoch": "equinox",
        "ctype": "ctype",
        "crval": "crval",
        "cdelt": "cdelt",
        "crpix": "crpix",
        "crota": "crota",
        "bmaj": "beamMaj",
        "bmin": "beamMin",
        "bpa": "beamPA",
        "altrval": "altRef",
        "altrpix": "altCrpix",
        "obsra": "obsra",
        "obsdec": "obsdec",
        "restfreq": "restFreq",
        "xshift": "xshift",
        "yshift": "yshift",
        # Images
        "niter": "niter",
        "datamin": "minval",
        "datamax": "maxval",
        # UV Data sets
        "sortord": "isort",
        "nrparm": "nrparm",
        "ptype": "ptype",
        "ncorr": "ncorr",
    }
    _strip = ("object", "telescop", "instrume", "observer", "bunit", "ptype", "ctype")

    def __getitem__(self, key):
        if key == "velref":
            return self._dict["VelReference"] + self._dict["VelDef"] * 256
        if key not in self._keys:
            raise KeyError(key)
        return self._dict[self._keys[key]]

    def __setitem__(self, key, value):
        if key == "velref":
            self._dict["VelDef"] = value / 256
            self._dict["VelReference"] = value % 256
            return
        if key not in self._keys:
            raise KeyError(key)
        self._dict[self._keys[key]] = value
        return

    def __getattr__(self, name):
        if name.startswith("_"):
            return self.__dict__[name]
        try:
            value = self.__getitem__(name)
        except KeyError:
            msg = f"{self.__class__.__name__} instance has no attribute '{name}'"
            raise AttributeError(msg)
        return value

    def __setattr__(self, name, value):
        if name.startswith("_"):
            self.__dict__[name] = value
            return
        try:
            self.__setitem__(name, value)
        except KeyError:
            msg = f"{self.__class__.__name__} instance has no attribute '{name}'"
            raise AttributeError(msg)

    def _generate_dict(self):
        dict_ = {}
        for key in self._keys:
            if self._keys[key] in self._dict:
                dict_[key] = self._dict[self._keys[key]]

        return dict_

    def __str__(self):
        return str(self._generate_dict())

    def update(self):
        self._data.Desc.Dict = self._dict
        self._obit.PUpdateDesc(self._data, self._err)


# class _AIPSDataHeader


class _AIPSData:
    """This class is used to access generic AIPS data."""

    def __init__(self, *args):
        # Instances can be created by specifying name, class, disk,
        # sequency number and (optionally) user number explicitly, or
        # by passing an object that has the appropriate attributes.
        # This allows the creation of a Wizardry object from its
        # non-Wizardry counterpart.

        if len(args) not in [1, 4, 5]:
            msg = "__init__() takes 2, 5 or 6 arguments (%d given)" % (len(args) + 1)
            raise TypeError(msg)

        if len(args) == 1:
            self._init(
                args[0].name, args[0].klass, args[0].disk, args[0].seq, args[0].userno
            )
        else:
            userno = -1
            if len(args) == 5:
                userno = args[4]

            self._init(args[0], args[1], args[2], args[3], userno)

    _header = None

    def _generate_header(self):
        if not self._header:
            self._header = _AIPSDataHeader(self._data, self._obit, self._err)

        return self._header

    header = property(_generate_header, doc="Header for this data set.")

    _keywords = None

    def _generate_keywords(self):
        if not self._keywords:
            self._keywords = _AIPSDataKeywords(self._data, self._obit, self._err)

        return self._keywords

    keywords = property(_generate_keywords, doc="Keywords for this data set.")

    def _generate_tables(self):
        # Reopen the file to make sure the list of tables is updated.
        self._data.Open(3, self._err)
        return TableList.PGetList(self._data.TableList, self._err)

    tables = property(_generate_tables, doc="Tables attached to this data set.")

    def _generate_stokes(self):
        """Generate the 'stokes' attribute."""

        stokes_dict = {
            1: "I",
            2: "Q",
            3: "U",
            4: "V",
            -1: "RR",
            -2: "LL",
            -3: "RL",
            -4: "LR",
            -5: "XX",
            -6: "YY",
            -7: "XY",
            -8: "YX",
        }

        stokes = []
        header = self._data.Desc.Dict
        jlocs = header["jlocs"]
        cval = header["crval"][jlocs]
        for i in range(header["inaxes"][jlocs]):
            stokes.append(stokes_dict[int(cval)])
            cval += header["cdelt"][jlocs]

        return stokes

    stokes = property(_generate_stokes, doc="Stokes parameters for this data set.")

    def _generate_name(self):
        return self._data.Aname

    name = property(_generate_name)

    def _generate_klass(self):
        return self._data.Aclass

    klass = property(_generate_klass)

    def _generate_disk(self):
        return self._data.Disk

    disk = property(_generate_disk)

    def _generate_seq(self):
        return self._data.Aseq

    seq = property(_generate_seq)

    def _generate_userno(self):
        return self._userno

    userno = property(_generate_userno)

    def rename(self, name=None, klass=None, seq=None):
        """Rename this image or data set.

        NAME is the new name, KLASS is the new class and SEQ is the
        new sequence number for the data set.  Note that you can't
        change the disk number, since that would require copying the
        data.
        """

        if name is None:
            name = self._data.Aname
        if klass is None:
            klass = self._data.Aclass
        if seq is None:
            seq = self._data.Aseq

        self._obit.PRename(
            self._data,
            self._err,
            newAIPSName=name.ljust(12),
            newAIPSClass=klass.ljust(6),
            newAIPSSeq=seq,
        )

        # If SEQ was zero, we need to check out the assigned sequence
        # number.  We do this based on the catalog number, so there is
        # a chance it'll fail if somebody does a RECAT.
        if seq == 0:
            from obit import AIPSDir

            cno = self._data.Acno
            entry = AIPSDir.PInfo(self.disk, self.userno, cno, self._err)
            if name == entry[0:12].strip() and klass == entry[13:19].strip():
                seq = int(entry[20:25])

        return (name, klass, seq)

    def table_highver(self, name):
        """Return the latest version of the extension table `name`."""
        if not name.startswith("AIPS "):
            name = f"AIPS {name}"

        return TableList.PGetHigh(self._data.TableList, name)

    def table(self, name, version):
        """Access an extension table attached to this UV data set.

        Parameters
        ----------
        name : str
            Name of the extension table ("CL", "SN", "PL", etc).
        version : int
            Version of the extension table. If `version` is 0, return the highest
            available version of the requested extension table.

        Returns
        -------
            AIPSTable object.
        """
        return _AIPSTable(self._data, name, version)

    def zap_table(self, name, version):
        """Remove an extension table from this UV data set."""

        if not name.startswith("AIPS "):
            name = f"AIPS {name}"

        assert not self._err.isErr
        try:
            self._data.ZapTable(name, version, self._err)

            # OData.ZapTable calls OData.UpdateTables
            # self._data.UpdateTables(self._err)
        except OErr.ObitError as err:
            # print(err)
            msg = f"Cannot zap {name} table version {version}: {err}"
            raise RuntimeError(msg)

    def zap(self, force=False):
        """Removes the data object from the AIPS catalogue.

        Parameters
        ----------
        force : bool, optional
            If True reset file status before removing.

        """
        if force:
            self.clrstat()

        self._data.Zap(self._err)

    def clrstat(self):
        """Reset file 'busy' status in the AIPS catalogue."""
        cno = Obit.AIPSDirFindCNO(
            self._data.Disk,
            self._userno,
            self._data.Aname,
            self._data.Aclass,
            self._type,
            self._data.Aseq,
            self._err.me,
        )
        Obit.AIPSDirStatus(self._data.Disk, self._userno, cno, 4, self._err.me)

    def update(self):
        """Synchronise the data object with the AIPS catalogue entry."""
        self._obit.PUpdateDesc(self._data, self._err)

# class _AIPSData


class AIPSImage(_AIPSData):
    """This class is used to access an AIPS image."""

    def _init(self, name, klass, disk, seq, userno):
        from obit import Image

        from .. import AIPS

        self._obit = Image
        self._type = "MA"
        if userno == -1:
            userno = AIPS.userno

        self._userno = userno
        self._err = OErr.OErr()
        self._squeezed = False
        OSystem.PSetAIPSuser(userno)
        self._data = Image.newPAImage(name, name, klass, disk, seq, True, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Opening Image data")

    def _pixels(self):
        Obit.ImageRead(self._data.me, self._err.me)
        if self._err.isErr:
            raise OErr.ObitError("Reading image pixels")
        shape = []
        for len in self.header["naxis"]:
            if self._squeezed and len == 1:
                continue
            shape.insert(0, len)
            continue
        shape = tuple(shape)
        pixels = _array(self._data.PixBuf, shape)
        return pixels

    pixels = property(_pixels)

    def squeeze(self):
        """Remove degenerate dimensions from image."""

        self._squeezed = True

    def attach_table(self, name, version, **kwds):
        """Attach an extension table to this image.

        A new extension table is created if the extension table NAME
        with version VERSION doesn't exist.  If VERSION is 0, a new
        extension table is created with a version that is one higher
        than the highest available version."""

        if not name.startswith("AIPS "):
            name = "AIPS " + name

        if version == 0:
            version = Obit.ImageGetHighVer(self._data.me, name) + 1

        no_parms = 0
        if "no_parms" in kwds:
            no_parms = kwds["no_parms"]
        data = Obit.ImageCastData(self._data.me)
        if name == "AIPS CC":
            Obit.TableCC(data, [version], 3, name, no_parms, self._err.me)
        elif name == "AIPS FG":
            Obit.TableFG(data, [version], 3, name, self._err.me)
        elif name == "AIPS PS":
            Obit.TablePS(data, [version], 3, name, self._err.me)
        elif name == "AIPS SN":
            Obit.TableSN(
                data, [version], 3, name, kwds["no_pol"], kwds["no_if"], self._err.me
            )
        else:
            msg = f"Attaching {name} tables is not implemented yet"
            raise NotImplementedError(msg)

        if self._err.isErr:
            raise OErr.ObitError(f"Attaching table {name}")

        return _AIPSTable(self._data, name, version)

    history = property(lambda self: _AIPSHistory(self._data))

    def update(self):
        Obit.ImageWrite(self._data.me, self._err.me)
        if self._err.isErr:
            raise OErr.ObitError("Writing image pixels")

        _AIPSData.update(self)

# class AIPSImage


class AIPSUVData(_AIPSData):
    """This class is used to access an AIPS UV data set."""

    def _init(self, name, klass, disk, seq, userno):
        from obit import UV

        from .. import AIPS

        self._obit = UV
        self._type = "UV"
        if userno == -1:
            userno = AIPS.userno
        self._userno = userno
        self._err = OErr.OErr()
        OSystem.PSetAIPSuser(userno)
        self._data = UV.newPAUV(name, name, klass, disk, seq, True, self._err)
        if self._err.isErr:
            raise OErr.ObitError("Opening UV data")
        self._antennas = []
        self._polarizations = []
        self._sources = []
        self._open = False

    def __len__(self):
        return self._data.Desc.Dict["nvis"]

    def __getitem__(self, name):
        if not self._open:
            self._data.Open(3, self._err)
            self._open = True

        if isinstance(name, str):
            return _AIPSVisibilitySel(self, name)
        elif isinstance(name, slice):
            return _AIPSVisibilitySlice(self, name)
        return _AIPSVisibility(self._data, self._err, name)

    def __iter__(self):
        if not self._open:
            self._data.Open(3, self._err)
            self._open = True

        return _AIPSVisibilityIter(self._data, self._err)

    def _generate_antennas(self):
        """Generate the 'antennas' attribute."""

        if not self._antennas:
            antable = self.table("AN", 0)
            for antenna in antable:
                self._antennas.append(antenna.anname.rstrip())

        return self._antennas

    antennas = property(_generate_antennas, doc="Antennas in this data set.")

    def _generate_polarizations(self):
        """Generate the 'polarizations' attribute.

        Returns a list of the polarizations for this data set."""

        if not self._polarizations:
            for stokes in self.stokes:
                if len(stokes) == 2:
                    for polarization in stokes:
                        if polarization not in self._polarizations:
                            self._polarizations.append(polarization)
        return self._polarizations

    polarizations = property(
        _generate_polarizations, doc="Polarizations in this data set."
    )

    def _generate_sources(self):
        """Generate the 'sources' attribute."""

        if not self._sources:
            sutable = self.table("SU", 0)
            for source in sutable:
                self._sources.append(source.source.rstrip())

        return self._sources

    sources = property(_generate_sources, doc="Sources in this data set.")

    def attach_table(self, name, version, **kwds):
        """Attach an extension table to this UV data set.

        A new extension table is created if the extension table NAME
        with version VERSION doesn't exist.  If VERSION is 0, a new
        extension table is created with a version that is one higher
        than the highest available version."""

        if not name.startswith("AIPS "):
            name = "AIPS " + name

        if version == 0:
            version = Obit.UVGetHighVer(self._data.me, name) + 1

        header = self._data.Desc.Dict
        jlocif = header["jlocif"]
        no_if = header["inaxes"][jlocif]
        if "no_if" in kwds:
            no_if = kwds["no_if"]

        no_pol = len(self.polarizations)
        if "no_pol" in kwds:
            no_pol = kwds["no_pol"]

        data = Obit.UVCastData(self._data.me)
        if name == "AIPS AI":
            # Obit.TableAI(data, [version], 3, name, kwds["no_term"], self._err.me)
            raise NotImplementedError("AIPS AI")
        elif name == "AIPS CL":
            Obit.TableCL(
                data, [version], 3, name, no_pol, no_if, kwds["no_term"], self._err.me
            )
        elif name == "AIPS FQ":
            Obit.TableFQ(data, [version], 3, name, no_if, self._err.me)
        elif name == "AIPS NI":
            Obit.TableNI(data, [version], 3, name, kwds["num_coef"], self._err.me)
        elif name == "AIPS PS":
            Obit.TablePS(data, [version], 3, name, self._err.me)
        elif name == "AIPS SN":
            Obit.TableSN(data, [version], 3, name, no_pol, no_if, self._err.me)
        elif name == "AIPS SU":
            Obit.TableSU(data, [version], 3, name, no_if, self._err.me)
        else:
            msg = "Attaching %s tables is not implemented yet" % name
            raise NotImplementedError(msg)

        if self._err.isErr:
            raise OErr.ObitError(f"Opening table {name}")

        return _AIPSTable(self._data, name, version)

    # history = property(lambda self: _AIPSHistory(self._data))
    @property
    def history(self):
        return _AIPSHistory(self._data)


# class AIPSUVData


err = OErr.OErr()
OSystem.OSystem("", 1, 0, -1, [], -1, [], True, False, err)
