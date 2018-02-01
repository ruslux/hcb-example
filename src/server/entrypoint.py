import os
import random
import string
import json

import aiohttp
from aiohttp import web, WSMsgType


def session(votes):
    """
    Обертка-воркер для мультипросессорного запуска
    :param votes: Общий для процессов словарь с голосами пользователей. 
        Если токен присутствует в нем, значит у пользователя верная сессия
    :return: 
    """
    async def handler(request):
        """
        Метод создает сессию и устанавливает токен как заголовок
        :param request: 
        :return: 
        """
        _token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        try:
            votes[_token] = 0
        except Exception as exc:
            print(exc, votes, _token)

        return web.Response(status=201, headers={'x-token': _token})

    return handler


def vote(votes, cache):
    """
    Обертка-воркер для мультипросессорного запуска
    :param votes: Общий для процессов словарь с голосами пользователей. 
        Если токен присутствует в нем, значит у пользователя верная сессия
    :param cache: Общий для процессов словарь с голосами пользователей, которые онлайн
    :return: 
    """
    async def handler(request):
        """
        Метод принимает голос от пользователя. 
        И обновляет кэш, если пользователь уже голосовал ранее и сейчас находится онлайн.
        :param request: 
        :return: 
        """
        _token = request.headers.get('x-token', 'unknown')

        if _token not in votes:
            return web.Response(status=401)

        try:
            _data = await request.json()
            _number = int(_data.get('number', 0))
        except (ValueError, json.decoder.JSONDecodeError):
            return web.Response(status=400)

        if 0 < _number <= 10:
            votes[_token] = _number

            if _token in cache:
                cache[_token] = _number

            return web.Response(status=201)
        else:
            return web.Response(status=400)

    return handler


def sum_votes(votes):
    return sum(votes.values())


def online(votes, cache):
    """
    Обертка-воркер для мультипросессорного запуска
    :param votes: Общий для процессов словарь с голосами пользователей.
        Если токен присутствует в нем, значит у пользователя верная сессия
    :param cache: Общий для процессов словарь с голосами пользователей, которые онлайн
    :return: 
    """
    async def handler(request):
        """
        Если пользователь с токеном, то считаем его как "онлайн" и засчитываем его голос при определении суммы.
        :param request: 
        :return: 
        """
        _token = request.headers.get('x-token', None)

        if _token in votes:
            """
            Кэшируются ТОЛЬКО онлайн пользователи, поэтому при подсчете суммы можнно просто использовать кэш
            """
            cache[_token] = votes[_token]

        ws = web.WebSocketResponse()

        await ws.prepare(request)
        async for msg in ws:
            try:
                if msg.type == WSMsgType.TEXT and msg.data == 'get_votes':
                    _sum = str(sum_votes(cache))
                    await ws.send_str(_sum)
                elif msg.data == 'close':
                    await ws.close()
                    """
                    Чистим кэш - пользователь больше не онлайн
                    """
                    del cache[_token]
                    print("Socket closed gracefully")
            except Exception as exc:
                await ws.close()
                del cache[_token]
                print("Socket closed with error:", exc)
        return ws

    return handler


def worker(votes, cache, port):
    app = web.Application()
    app.router.add_post('/session', session(votes))
    app.router.add_post('/vote', vote(votes, cache))
    app.router.add_get('/online', online(votes, cache))

    web.run_app(app, port=port)


if __name__ == "__main__":
    import multiprocessing

    _manager = multiprocessing.Manager()
    _votes = _manager.dict()
    _cache = _manager.dict()

    _processes_count = int(os.environ.get("PROCESSES_COUNT", multiprocessing.cpu_count()))

    _processes = [
        multiprocessing.Process(target=worker, args=(_votes, _cache, 8000 + i))
        for i in range(_processes_count)
    ]

    for _process in _processes:
        print("start process:", _process)
        _process.start()

    for _process in _processes:
        print("start process:", _process)
        _process.join()
