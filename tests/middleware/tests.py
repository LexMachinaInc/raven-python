
import logging
import sys
from unittest2 import TestCase
from raven.base import Client
from raven.middleware import Sentry
# XXX: webob does not work under Python < 2.6
if (sys.version_info < (2, 6, 0)):
    from nose.plugins.skip import SkipTest
    raise SkipTest
import webob


class TempStoreClient(Client):
    def __init__(self, servers=None, **kwargs):
        self.events = []
        super(TempStoreClient, self).__init__(servers=servers, **kwargs)

    def is_enabled(self):
        return True

    def send(self, **kwargs):
        self.events.append(kwargs)


def example_app(environ, start_response):
    raise ValueError('hello world')


class MiddlewareTest(TestCase):
    def setUp(self):
        self.app = example_app

    def test_error_handler(self):
        client = TempStoreClient()
        middleware = Sentry(self.app, client=client)

        request = webob.Request.blank('/an-error?foo=bar')
        response = middleware(request.environ, lambda *args: None)

        with self.assertRaises(ValueError):
            response = list(response)

        self.assertEquals(len(client.events), 1)
        event = client.events.pop(0)

        self.assertTrue('sentry.interfaces.Exception' in event)
        exc = event['sentry.interfaces.Exception']
        self.assertEquals(exc['type'], 'ValueError')
        self.assertEquals(exc['value'], 'hello world')
        self.assertEquals(event['level'], logging.ERROR)
        self.assertEquals(event['message'], 'ValueError: hello world')

        self.assertTrue('sentry.interfaces.Http' in event)
        http = event['sentry.interfaces.Http']
        self.assertEquals(http['url'], 'http://localhost/an-error')
        self.assertEquals(http['query_string'], 'foo=bar')
        self.assertEquals(http['method'], 'GET')
        # self.assertEquals(http['data'], {'foo': 'bar'})
        headers = http['headers']
        self.assertTrue('Host' in headers, list(headers.keys()))
        self.assertEquals(headers['Host'], 'localhost:80')
        env = http['env']
        self.assertTrue('SERVER_NAME' in env, list(env.keys()))
        self.assertEquals(env['SERVER_NAME'], 'localhost')
        self.assertTrue('SERVER_PORT' in env, list(env.keys()))
        self.assertEquals(env['SERVER_PORT'], '80')
