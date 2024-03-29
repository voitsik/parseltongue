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

"""
This module provides the Task class.  It extends the MinimalMatch
class from the MinimalMatch module with type and range checking on its
attributes:

>>> class MyTask(Task):
...     indisk = 0
...     inseq  = 0
...     infile = ''
...     pixavg = 1.0
...     aparms = 10*[0.0]
...     def __init__(self):
...         Task.__init__(self)
...         self._min_dict = {'inseq': 0, 'aparms': 0}
...         self._max_dict = {'inseq': 4, 'aparms': 10}
...         self._strlen_dict = {'infile': 14}
...         self.__dict__['bparms'] = List(self, 'bparms', [None, 1, 2, 3])
...
>>> my_task = MyTask()

It still has the property that attribute names can be abbreviated:

>>> print(my_task.ind)
0
>>> my_task.ind = 1
>>> print(my_task.ind)
1

But an exception will be thrown if you try to assign a value that is
out of range:

>>> my_task.ins = 5
Traceback (most recent call last):
  ...
ValueError: value '5' is out of range for attribute 'inseq'

Or if you try to assign a value that has the wrong type, such
assigning a string to an integer attribute:

>>> my_task.ind = 'now'
Traceback (most recent call last):
  ...
TypeError: value 'now' has invalid type for attribute 'indisk'

Assigning strings to string attributes works fine of course:

>>> my_task.infile = 'short'

As long as there is no limit on the length of a string:

>>> my_task.infile = 'tremendouslylong'
Traceback (most recent call last):
  ...
ValueError: string 'tremendouslylong' is too long for attribute 'infile'

Assigning an integer value to a floating point attribute is perfectly
fine of course:

>>> my_task.pixavg = 2
>>> print(my_task.pixavg)
2.0

The same should happen for lists:

>>> my_task.aparms = 10*[1]
>>> print(my_task.aparms)
[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

For subscripting:

>>> my_task.aparms[0] = 0
>>> print(my_task.aparms)
[0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

And slice assignment:

>>> my_task.aparms[1:3] = [1, 2]
>>> print(my_task.aparms)
[0.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

You're not allowed to change the length of the list through slice
assignment though:

>>> my_task.aparms[3:6] = [3, 4, 5, 6]
Traceback (most recent call last):
  ...
TypeError: array '[3, 4, 5, 6]' is too big for attribute 'aparms'

To provide 1-based indexing used by several packages, you can set the
element at index zero of an array to 'None'.  This prevents setting that
element to anything other than 'None'

>>> my_task.bparms[0] = 0
Traceback (most recent call last):
  ...
ValueError: setting element '0' is prohibited

"""

# Generic Python stuff
import copy
import pydoc

from .MinimalMatch import MinimalMatch


class List(list):
    def __init__(self, task, attr, value):
        self._task = task
        self._attr = attr
        _value = []
        for item in value:
            if isinstance(item, list):
                _value.append(List(task, attr, item))
            else:
                _value.append(item)

        list.extend(self, _value)

    def __setitem__(self, key, item):
        if item is not None and self[key] is None:
            msg = "setting element '%d' is prohibited" % key
            raise ValueError(msg)
        item = self._task._validateattr(self._attr, item, self[key])
        list.__setitem__(self, key, item)

    def __setslice__(self, low, high, seq):
        high = min(high, len(self))
        if len(seq) > high - low or (len(seq) < high - low and high < len(self)):
            msg = "slice '%d:%d' changes the array size of attribute '%s'" % (
                low,
                high,
                self._attr,
            )
            raise TypeError(msg)
        for key in range(low, high):
            if key - low < len(seq):
                self[key] = seq[key - low]
            else:
                default = self._task._default_dict[self._attr][key]
                self[key] = copy.copy(default)


class Task(MinimalMatch):
    def __init__(self):
        self._default_dict = {}
        self._min_dict = {}
        self._max_dict = {}
        self._strlen_dict = {}
        self._help_string = ""

    def help(self):
        """Display help for this task."""
        if self._help_string:
            pydoc.pager(self._help_string)

    def _validateattr(self, attr, value, default):
        """Check whether VALUE is a valid valid for attribute ATTR."""

        # Do not check private attributes.
        if attr.startswith("_"):
            return value

        # Short circuit.
        if value is None and default is None:
            return value

        # Handle lists recursively.
        if isinstance(value, list) and isinstance(default, list):
            if len(value) > len(default):
                msg = f"array '{value}' is too big for attribute '{attr}'"
                raise TypeError(msg)
            validated_value = List(self, attr, default)
            for key in range(len(value)):
                validated_value[key] = value[key]
            return validated_value

        # Convert integers into floating point numbers if necessary.
        if isinstance(value, int) and isinstance(default, float):
            value = float(value)

        # Check attribute type.
        if not isinstance(value, type(default)):
            msg = f"value '{value}' has invalid type for attribute '{attr}'"
            raise TypeError(msg)

        # Check range.
        if attr in self._min_dict:
            min_val = self._min_dict[attr]
            if not min_val <= value:
                msg = f"value '{value}' is out of range for attribute '{attr}'"
                raise ValueError(msg)

        if attr in self._max_dict:
            max_val = self._max_dict[attr]
            if not value <= max_val:
                msg = f"value '{value}' is out of range for attribute '{attr}'"
                raise ValueError(msg)

        # Check string length.
        if attr in self._strlen_dict:
            if len(value) > self._strlen_dict[attr]:
                msg = f"string '{value}' is too long for attribute '{attr}'"
                raise ValueError(msg)

        return value

    def __setattr__(self, name, value):
        attr = self._findattr(name)

        # Validate based on the value already present.
        if hasattr(self, attr):
            value = self._validateattr(attr, value, getattr(self, attr))
        self.__dict__[attr] = value
