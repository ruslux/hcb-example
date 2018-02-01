import os
import multiprocessing
import time
import json
from random import choice
from unittest import TestCase

import aiohttp
import asyncio

from aiohttp import WSMsgType

from src.server.entrypoint import worker


LIMIT = 100


async def make_requests(port, answers, index):
    _session = aiohttp.ClientSession()
    _response = await _session.post(f'http://0.0.0.0:{port}/session', data={})
    _token = _response.headers['x-token']
    assert _response.status == 201

    _session = aiohttp.ClientSession()
    _response = await _session.post(
        f'http://0.0.0.0:{port}/vote', data=json.dumps({'number': 1}), headers={'x-token': _token}
    )
    assert _response.status == 201

    ws = await _session.ws_connect(f'http://0.0.0.0:{port}/online', headers={'x-token': _token})

    _keep_connection = True

    while _keep_connection:
        await ws.send_str('get_votes')
        msg = await ws.receive()
        if msg.type == WSMsgType.TEXT:
            _sum = int(msg.data)
            answers[index] = _sum
            _keep_connection = _sum < LIMIT
        else:
            _keep_connection = False

    await ws.close()


def run(port, answers, index):
    _loop = asyncio.get_event_loop()
    _result = _loop.run_until_complete(make_requests(port, answers, index))


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

        for _answer in range(LIMIT):
            _answers.append(0)

        _ports = [7999 + i for i in range(self.cpu_count)]
        _processes = [
            multiprocessing.Process(target=run, args=(choice(_ports), _answers, i,)) for i in range(LIMIT)
        ]

        for _process in _processes:
            _process.daemon = True
            _process.start()

        _sum = sum(_answers)

        while _sum < LIMIT * LIMIT:
            _sum = sum(_answers)

        self.assertEqual(_sum, LIMIT * LIMIT)
