import json
import logging
from dataclasses import asdict
import redis

from allocation import config
from allocation.domain import events

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())

class AbstractPublisher:
    def __call__(self, channel, event: events.Event):
        raise NotImplementedError()


class RedisPublisher(AbstractPublisher):
    def __call__(self, channel, event: events.Event):
        logging.info('publishing: channel=%s, event=%s', channel, event)
        r.publish(channel, json.dumps(asdict(event)))


# def publish(channel, event: events.Event):
#     logging.info('publishing: channel=%s, event=%s', channel, event)
#     r.publish(channel, json.dumps(asdict(event)))
