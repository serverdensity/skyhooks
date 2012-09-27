"""Container object for registering hook callbacks, and maintaining hook
pointers in a persistence layer (e.g. MongoDB) with TTLs.
"""

import logging
import asyncmongo
from bson.objectid import ObjectId

from skyhooks import IOLoop


class WebhookContainer(object):
    callbacks = {}

    def __init__(self, config):
        if config['system_type'] == 'twisted':
            raise NotImplemented('Twisted Matrix support is planned for the'
                                 ' future.')

        self.config = config
        self.ioloop = IOLoop(config['system_type'])

    @property
    def db(self):
        if not hasattr(self, '_db'):
            self._db = asyncmongo.Client(pool_id='skyhooks',
                    host=self.config['MONGO_HOST'],
                    port=self.config['MONGO_PORT'],
                    dbname='skyhooks')
        return self._db

    def register(self, account_id, callback, url, user_id=None,
                 call_next=None):
        if account_id not in self.account_callbacks:
            self.account_callbacks[account_id] = []

        self.account_callbacks[account_id].append(callback)

        query = {
            'accountId': ObjectId(account_id),
            'url': url
        }

        if user_id:
            if user_id not in self.user_callbacks:
                self.user_callbacks[user_id] = []

            self.user_callbacks[user_id].append(callback)

            query['userId'] = ObjectId(user_id)

        callback_wrapper = lambda doc, error: self._mongo_callback(doc, error,
                                                                   call_next)
        logging.debug("Registering webhook for: %s", query)

        self.db.webhooks.update(query, query,
                callback=callback_wrapper,
                upsert=True)

    def unregister(self, account_id, callback, url, user_id=None,
                   call_next=None):

        if account_id in self.account_callbacks:
            self.account_callbacks[account_id].remove(callback)

            query = {
                'accountId': ObjectId(account_id),
                'url': url
            }

            if user_id in self.user_callbacks:
                self.user_callbacks[user_id].remove(callback)

                query['userId'] = ObjectId(user_id)

            callback_wrapper = lambda doc, error: self._mongo_callback(doc,
                                                           error, call_next)

            logging.debug("Unregistering webhook for: %s", query)
            self.db.webhooks.remove(query,
                    callback=callback_wrapper)

    def _mongo_callback(self, doc, error, call_next=None):
        if error:
            logging.error(error)
        if call_next:
            call_next()

    def notify(self, account_id, data, user_id=None):
        if account_id in self.account_callbacks:
            for callback in self.account_callbacks[account_id]:
                self.io_loop.add_callback(lambda cb=callback: cb(data))

            if user_id in self.user_callbacks:
                for callback in self.user_callbacks[user_id]:
                    self.io_loop.add_callback(lambda cb=callback: cb(data))

            return True

        return False