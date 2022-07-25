#  Copyright (c) - Stavros Avramidis 2022.
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#


import asyncio

from corebodytemp import Core


def callback(data):
    print(data)


async def main(address):
    async with Core(address, timeout=30.0) as client:
        print(f"Connected: {client.address}")
        print(f"Battery Level: {await client.get_battery_level()} %")

        client.set_core_temp_callback(callback)

        await client.start_listening_core_temp_broadcasts()
        await asyncio.sleep(100)

        await client.stop_listening_core_temp_broadcasts()
        await client.disconnect()


if __name__ == "__main__":
    ADDRESS = "C5:FA:48:7A:3A:64"

    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    asyncio.run(
        main(ADDRESS)
    )
