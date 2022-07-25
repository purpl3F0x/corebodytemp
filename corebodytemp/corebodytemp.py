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

from .datatypes import CoreMeasurement

import asyncio
import logging
from typing import Union, Callable

from bleak import BleakClient

from bleak.backends.device import BLEDevice

_logger = logging.getLogger(__name__)


class Core(BleakClient):
    BODY_TEMP_SERVICE = "00002100-5B1E-4347-B07C-97B514DAE121"
    BODY_TEMP_CHARACTERISTIC_ID = "00002101-5B1E-4347-B07C-97B514DAE121"
    BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805F9B34FB"

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super().__init__(address_or_ble_device, **kwargs)

        # Callbacks
        self.body_temp_callback = None

    async def start_listening_core_temp_broadcasts(self) -> None:
        """
        Start listening to Core Temperature Notifications
        :return:
        """
        await self.start_notify(Core.BODY_TEMP_CHARACTERISTIC_ID, self.__core_temp_notification_handler)

    async def stop_listening_core_temp_broadcasts(self):
        """
        Stop listening to Core Temperature Notifications
        :return:
        """
        await self.stop_notify(Core.BODY_TEMP_CHARACTERISTIC_ID)

    def set_core_temp_callback(self, callback: Callable[[CoreMeasurement], None]) -> None:
        """
        Register Callback function for Core Temperature Broadcasts
        :param callback:
        :return:
        """
        self.body_temp_callback = callback

    async def get_battery_level(self) -> int:
        """
        Reads sensor's battery level
        :return: Battery Percentage  from 0 to 100
        """
        return int.from_bytes(await self.read_gatt_char(Core.BATTERY_LEVEL_UUID), 'little')

    def __core_temp_notification_handler(self, _sender: int, data: bytearray) -> None:
        """
        Internal handler& parsser for core temperature notifications
        :param _sender:
        :param data: Senders raw data
        :return:
        """
        _logger.debug(f"{_sender} {data}")

        # Parse payload
        # See: https://github.com/CoreBodyTemp/CoreBodyTemp/raw/main/CORE%20BLE%20Implementation%20Notes.pdf
        #      https://github.com/CoreBodyTemp/CoreBodyTemp/raw/main/CoreTemp%20BLE%20Service%20Specification.pdf
        #
        # byte 0   Flag
        # byte 1-2 Core Body Temperature (int16)
        # byte 2-3 Skin Body Temperature (int16)
        # byte 4-5 Core Reserved         (int16)
        # byte 6   Quality & State

        response = CoreMeasurement(
            core_temp=(0.01 * int.from_bytes(data[1:3], 'little')) if data[0] & 0b1 else None,
            skin_temp=(0.01 * int.from_bytes(data[3:5], 'little')) if data[0] & 0b01 else None,
            core_reserved=int.from_bytes(data[5:7], 'little'),
            quality=CoreMeasurement.Quality(data[7] & 0b1111) if data[0] & 0b100 else CoreMeasurement.Quality.NOT_AVAILABLE,
            state=CoreMeasurement.State((data[7] & 0b111000) >> 4) if data[0] & 0b100 else CoreMeasurement.State.NOT_AVAILABLE,
            unit=CoreMeasurement.TempUnit(data[0] & 0b1000)
        )

        _logger.debug(f'{response!r}')

        try:
            self.body_temp_callback(data)
        except Exception as e:
            _logger.error(f"Error calling callback: {e}")
