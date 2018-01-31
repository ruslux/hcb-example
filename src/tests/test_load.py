import os
import multiprocessing
import time
from random import choice
from unittest import TestCase

import aiohttp
import asyncio

from src.server.entrypoint import worker


async def make_requests(port, answers):
    _session = aiohttp.ClientSession()
    _response = await _session.post(f'http://0.0.0.0:{port}/session', data={})
    _token = _response.headers['x-token']

    answers.append(1)

    # ws = await session.ws_connect(
    #     'http://webscoket-server.org/endpoint')
    #
    # while True:
    #     msg = await ws.receive()
    #
    #     if msg.tp == aiohttp.MsgType.text:
    #         if msg.data == 'close':
    #             await ws.close()
    #             break
    #         else:
    #             ws.send_str(msg.data + '/answer')
    #     elif msg.tp == aiohttp.MsgType.closed:
    #         break
    #     elif msg.tp == aiohttp.MsgType.error:
    #         break


def run(port, answers):
    _loop = asyncio.get_event_loop()
    _result = _loop.run_until_complete(make_requests(port, answers))


class LoadTestCase(TestCase):
    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.votes = self.manager.dict()
        self.cache = self.manager.dict()

        self.cpu_count = int(os.environ.get("PROCESSES_COUNT", multiprocessing.cpu_count()))

        _processes = [
            multiprocessing.Process(target=worker, args=(self.votes, self.cache, 7999 + i))
            for i in range(self.cpu_count)
        ]

        for _process in _processes:
            _process.daemon = True
            _process.start()

    def test_10k(self):
        _answers = self.manager.list()

        _ports = [7999 + i for i in range(self.cpu_count)]
        _processes = [
            multiprocessing.Process(target=run, args=(choice(_ports), _answers,)) for i in range(100)
        ]

        for _process in _processes:
            _process.daemon = True
            _process.start()
            _process.join()

        self.assertEqual(len(_answers), 100)
