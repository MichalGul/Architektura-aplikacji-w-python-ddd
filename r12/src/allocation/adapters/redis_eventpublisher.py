import json
import logging
from dataclasses import asdict
import redis

from allocation import config
from allocation.domain import events

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def publish(channel, event: events.Event):
    logging.debug('publishing: channel=%s, event=%s', channel, event)
    r.publish(channel, json.dumps(asdict(event)))


def update_readmodel(orderid, sku, batchref):
    logging.debug('updating readmodel redis: orderid=%s, sku=%s, batchref=%s', orderid, sku, batchref)
    r.hset(orderid, sku, batchref)

def get_readmodel(orderid):
    return r.hgetall(orderid)

def update_single_readmodel(orderid, sku, qty):
    logging.debug('updating single readmodel redis: orderid=%s, sku=%s, qty=%s', orderid, sku, qty)
    r.hset(orderid, sku, qty)

def get_single_readmodel(orderid, sku):
    return r.hget(orderid, sku)