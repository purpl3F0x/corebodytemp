"""
MIT License

Copyright (c) 2022 Stavros Avramidis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import NamedTuple
from enum import IntEnum, unique


class CoreMeasurement(NamedTuple):
    @unique
    class Quality(IntEnum):
        INVALID = 0
        POOR = 1
        FAIR = 2
        GOOD = 3
        EXCELLENT = 4
        NOT_AVAILABLE = 5

        def __repr__(self):
            return str(self.name)

    @unique
    class State(IntEnum):
        PAIRING_HR = 0
        HR_SUPPORTED_NOT_PAIRED = 1
        HR_SUPPORTED_PAIRED = 2
        NOT_AVAILABLE = 4

        def __repr__(self):
            return str(self.name)

    @unique
    class TempUnit(IntEnum):
        Celsius = 0
        Fahrenheit = 1

        def __repr__(self):
            return "°F" if self.value else "°C"

    core_temp: float or None
    skin_temp: float or None
    quality: Quality
    state: State
    core_reserved: int
    unit: TempUnit
