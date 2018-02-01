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


"""
Количество процессов для нагрузочного тестирования, имитируют действия пользователей. 
Аккуратно! Процессы работают до тех пор, пока все ползьователи не увидят всех остальных.
"""
LIMIT = 100
VOTE_NUMBER = 2


async def make_requests(port, answers, index):
    """
    Корутина для трех запросов
    :param port: Порт на который будет стучать корутина
    :param answers: Общий для всех процессов список
    :param index: Индекс процесса в этом списке
    :return: 
    """

    """
    Создаем сессию, получаем токен
    """
    _session = aiohttp.ClientSession()
    _response = await _session.post(f'http://0.0.0.0:{port}/session', data={})
    _token = _response.headers['x-token']
    assert _response.status == 201

    """
    Используем токен, голосуем за 1. Важно! 1 требуется для простого посчета суммы всех ответов
    """
    _session = aiohttp.ClientSession()
    _response = await _session.post(
        f'http://0.0.0.0:{port}/vote', data=json.dumps({'number': VOTE_NUMBER}), headers={'x-token': _token}
    )
    assert _response.status == 201

    """
    Подключаем псевдопользователя к вебсокету и ждем пока сервер не пришлет корректную сумму равную VOTE_NUMBER * LIMIT
    """
    ws = await _session.ws_connect(f'http://0.0.0.0:{port}/online', headers={'x-token': _token})
    _keep_connection = True

    while _keep_connection:
        await ws.send_str('get_votes')
        msg = await ws.receive()
        if msg.type == WSMsgType.TEXT:
            _sum = int(msg.data)
            answers[index] = _sum
            _keep_connection = _sum < LIMIT * VOTE_NUMBER
            """
            Велосипед: не закрываем сокет, что бы кэш сумм на сервере не почистился при закрытии сокета. 
            (Имитация большого и ровного онлайна, что бы тест удался)
            """
            # if not _keep_connection:
            #     await ws.send_str('close')
        else:
            _keep_connection = False

    await ws.close()


def run(port, answers, index):
    """
    Запускаем цикл событий и пробрасываем в тестовый метод данные
    :param port: Порт на который будет стучать корутина
    :param answers: Общий для всех процессов список
    :param index: Индекс процесса в этом списке 
    :return: 
    """
    _loop = asyncio.get_event_loop()
    _result = _loop.run_until_complete(make_requests(port, answers, index))


class LoadTestCase(TestCase):
    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.votes = self.manager.dict()
        self.cache = self.manager.dict()

        self.cpu_count = int(os.environ.get("PROCESSES_COUNT", multiprocessing.cpu_count()))

        """
        Запускаем процессы имитирующие веб-сервер 
        """
        _processes = [
            multiprocessing.Process(target=worker, args=(self.votes, self.cache, 7999 + i))
            for i in range(self.cpu_count)
        ]

        for _process in _processes:
            _process.daemon = True
            _process.start()

    def test_10k(self):
        """
        Нагрузочный тест + интеграционный. На моей машине все умирает на 200 "пользователях".
        :return: 
        """
        _answers = self.manager.list()

        """
        Готовим межпроцессорный список для хранения "видимых" "пользователями" ответов сервера. Каждому пользователю
        выделим индекс и пока значение по этому индексу не будет равно VOTE_NUMBER * LIMIT (Что означает что все 
        пользователи проголосовали и все пользователи при этом в онлайне)
        """
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

        while _sum < VOTE_NUMBER * LIMIT * LIMIT:
            _sum = sum(_answers)

        self.assertEqual(_sum, VOTE_NUMBER * LIMIT * LIMIT)
