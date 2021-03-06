"""Tornado web handlers for webhook POST requests.
"""

from __future__ import absolute_import

from six import u
from tornado.web import RequestHandler
from tornado.escape import json_decode


class WebhookHandler(RequestHandler):
    """Handle webhook post backs from celery tasks and route to websockets
    via registered callbacks.
    """

    def post(self):
        payload = json_decode(u(self.request.body))
        data = payload['data']
        keys = payload['keys']

        self.application.webhook_container.logger.info(
            'Received webhook postback for {}'.format(keys))

        notified = self.application.webhook_container.notify(keys, data)

        # Celery compatible "hook" response, good enough for our purposes
        self.write({"status": "ok",
                    "notified": notified})
