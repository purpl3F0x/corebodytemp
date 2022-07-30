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
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Union, NamedTuple
from enum import IntEnum, unique

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.winrt.client import BleakClientWinRT

from .datatypes import CoreMeasurement

_logger = logging.getLogger(__name__)


class Core(BleakClient):
    """
    Corebodytemp BLE Client class
    """

    # Core Defined GATTs
    CORE_BODY_TEMP_SERVICE = "00002100-5B1E-4347-B07C-97B514DAE121"
    CORE_BODY_TEMP_CHARACTERISTIC_ID = "00002101-5B1E-4347-B07C-97B514DAE121"
    CORE_BODY_TEMP_CTRL_CHARACTERISTIC_ID = "00002102-5B1E-4347-B07C-97B514DAE121"
    # Common Defined GATTs
    BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805F9B34FB"

    class _TempCtrlPointResponse(NamedTuple):
        @unique
        class ResultCodes(IntEnum):
            SUCCESS = 0x01
            OPCODE_NOT_SUPPORTED = 0x02
            INVALID_PARAMETER = 0x03
            OPERATION_FAILED = 0x04

        opCode: int
        resultCode: ResultCodes
        parameter: bytearray

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super().__init__(address_or_ble_device, **kwargs)

        # Callbacks
        self.body_temp_callback = None

        # Stuff for handling Control Endpoint indications
        self._ctrl_endpoint_observer = asyncio.Condition()
        self._ctrl_endpoint_buffer = None

    async def connect(self, **kwargs) -> bool:
        is_connected = await super().connect(**kwargs)
        if is_connected:
            await self.start_notify(Core.CORE_BODY_TEMP_CTRL_CHARACTERISTIC_ID, self._ctrl_endpoint_indication_handler)

        return is_connected

    async def start_listening_core_temp_broadcasts(self) -> None:
        """
        Start listening to Core Temperature Notifications
        :return:
        """
        await self.start_notify(Core.CORE_BODY_TEMP_CHARACTERISTIC_ID, self.__core_temp_notification_handler)

    async def stop_listening_core_temp_broadcasts(self) -> None:
        """
        Stop listening to Core Temperature Notifications
        :return:
        """
        await self.stop_notify(Core.CORE_BODY_TEMP_CHARACTERISTIC_ID)

    def set_core_temp_callback(self, callback: Callable[[Core, CoreMeasurement], None]) -> None:
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

    async def get_number_of_ant_hrm(self) -> int or None:
        """

        :return:
        """

        async with self._ctrl_endpoint_observer:
            await self.write_gatt_char(Core.CORE_BODY_TEMP_CTRL_CHARACTERISTIC_ID, bytearray(b'\x04'), response=True)

            await self._ctrl_endpoint_observer.wait_for(lambda: self._ctrl_endpoint_buffer is not None)

            response = self._ctrl_endpoint_buffer
            self._ctrl_endpoint_buffer = None

            if response.resultCode == Core._TempCtrlPointResponse.ResultCodes.SUCCESS:
                n_of_monitors = int(response.parameter[0])
                _logger.info(f"Number of ANT+ HRM: {n_of_monitors}")
                return n_of_monitors

        return None

    async def get_ant_hrm_id_at(self, index: int) -> int:
        """

        :param index:
        :return:
        """

        async with self._ctrl_endpoint_observer:
            request = bytes([0x05]) + index.to_bytes(1, 'little')
            await self.write_gatt_char(Core.CORE_BODY_TEMP_CTRL_CHARACTERISTIC_ID, request, response=True)

            await self._ctrl_endpoint_observer.wait_for(lambda: self._ctrl_endpoint_buffer is not None)

            response = self._ctrl_endpoint_buffer
            self._ctrl_endpoint_buffer = None

            if response.resultCode == Core._TempCtrlPointResponse.ResultCodes.SUCCESS:
                hrm_id = response.parameter[0]
                ant_id = int.from_bytes(response.parameter[1:3], 'little') + ((response.parameter[3] & 0b1111) << 16)
                _logger.debug(f"Got ANT+ID of HRM[{hrm_id}]: {ant_id}")

                return ant_id

            else:
                _logger.error(f"Error Getting ANT+ID of HRM[{index}]: Result Code: {response.resultCode}")

        return 0

    def __core_temp_notification_handler(self, _sender: int, data: bytearray) -> None:
        """
        Internal handler & parser for core temperature notifications
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

        _logger.debug(f'{self.address} Notified: {response!r}')

        try:
            self.body_temp_callback(self, response)
        except Exception as e:
            _logger.error(f"Error calling callback: {e}")

    def _ctrl_endpoint_indication_handler(self, _sender: int, data: bytearray):

        self._ctrl_endpoint_buffer = Core._TempCtrlPointResponse(
            opCode=data[1],
            resultCode=Core._TempCtrlPointResponse.ResultCodes(data[2]),
            parameter=data[2:]
        )

        _logger.debug(f"CTRL Endpoint Indication {_sender} : {data}")
