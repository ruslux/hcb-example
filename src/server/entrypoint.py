import os
import random
import string

import aiohttp
from aiohttp import web


def session(votes):
    async def handler(request):
        _token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        try:
            votes[_token] = 0
        except Exception as exc:
            print(exc, votes, _token)

        return web.Response(status=201, headers={'x-token': _token})

    return handler


def vote(votes, cache):
    async def handler(request):
        _token = request.headers.get('x-token', 'unknown')

        if _token not in votes:
            return web.Response(status=401)

        _data = await request.json()

        try:
            _number = int(_data.get('number', 0))
        except ValueError:
            return web.Response(status=400)

        if 0 < _number <= 10:
            votes[_token] = _number

            if _token in cache:
                cache[_token] = _number

            return web.Response(status=201)
        else:
            return web.Response(status=400)

    return handler


def online(votes, cache):
    async def handler(request):
        _token = request.headers.get('x-token', None)

        if _token in votes:
            cache[_token] = votes[_token]

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws.send_str(msg.data + '/answer')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        print('websocket connection closed')
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
