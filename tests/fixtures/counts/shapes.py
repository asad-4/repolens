import asyncio


def sync_func():
    square = lambda n: n * n
    return square(2)


async def async_func():
    await asyncio.sleep(0)


class Outer:
    def method(self):
        def inner():
            return 1
        return inner()

    async def async_method(self):
        return 2

    class Inner:
        pass
