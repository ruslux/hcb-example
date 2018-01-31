from aiounittest import AsyncTestCase
from src.server.entrypoint import session, vote


class Request(object):
    def __init__(self, headers, data):
        self.headers = headers
        self.data = data

    async def json(self):
        return self.data


class UnitTestCase(AsyncTestCase):
    async def test_session(self):
        _votes = {}
        _response = await session(_votes)(None)
        self.assertEqual(_response.status, 201)
        self.assertIn('x-token', _response.headers)
        self.assertEqual(_votes.get(_response.headers['x-token']), 0)

    async def test_unauthorized_vote(self):
        _votes = {'ololo': 0}
        _cache = {}

        _response = await vote(_votes, _cache)(Request({'x-token': 'ahtung'}, {'number': 0}))
        self.assertEqual(_response.status, 401)

    async def test_wrong_vote(self):
        _votes = {'ololo': 0}
        _cache = {}

        _response = await vote(_votes, _cache)(Request({'x-token': 'ololo'}, {}))
        self.assertEqual(_response.status, 400)

        _response = await vote(_votes, _cache)(Request({'x-token': 'ololo'}, {'number': 0}))
        self.assertEqual(_response.status, 400)

        _response = await vote(_votes, _cache)(Request({'x-token': 'ololo'}, {'number': 'ahtung'}))
        self.assertEqual(_response.status, 400)

    async def test_right_vote_offline(self):
        _votes = {'ololo': 0}
        _cache = {}

        _response = await vote(_votes, _cache)(Request({'x-token': 'ololo'}, {'number': '1'}))
        self.assertEqual(_response.status, 201)
        self.assertEqual(_votes.get('ololo', 0), 1)
        self.assertEqual(_cache.get('ololo', None), None)

    async def test_right_vote_online(self):
        _votes = {'ololo': 0}
        _cache = {'ololo': 0}

        _response = await vote(_votes, _cache)(Request({'x-token': 'ololo'}, {'number': '1'}))
        self.assertEqual(_response.status, 201)
        self.assertEqual(_votes.get('ololo', 0), 1)
        self.assertEqual(_cache.get('ololo', 0), 1)

