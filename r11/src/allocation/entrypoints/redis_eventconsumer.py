import json
import logging
from datetime import datetime

import redis

from allocation import config
from allocation.domain import commands
from allocation.adapters import orm
from allocation.service_layer import messagebus, unit_of_work

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def main():
    orm.start_mappers()
    pubsub = r.pubsub(ignore_subscribe_messages=True)

    for channel in CHANNEL_HANDLERS:
        pubsub.subscribe(channel)
    # pubsub.subscribe('change_batch_quantity')
    # pubsub.subscribe('allocate')
    # pubsub.subscribe('add_batch')

    logger.info('Start listening for messages')
    for m in pubsub.listen():
        channel = m['channel']
        if channel in CHANNEL_HANDLERS:
            handler = CHANNEL_HANDLERS[channel]
            handler(m)
        else:
            logger.warning(f'No handler for channel {channel}')


def handle_change_batch_quantity(msg):
    logging.debug('handling %s', msg)
    data = json.loads(msg['data'])
    cmd = commands.ChangeBatchQuantity(ref=data['batchref'], qty=data['qty'])
    messagebus.handle(cmd, uow=unit_of_work.SqlAlchemyUnitOfWork())


def handle_allocation(msg):
    logging.debug(f"handling {msg}")
    data = json.loads(msg['data'])
    cmd = commands.Allocate(orderid=data['orderid'], sku=data['sku'], qty=data['qty'])
    result = messagebus.handle(cmd, uow=unit_of_work.SqlAlchemyUnitOfWork())

    batchref = result.pop(0)
    print(batchref)


def handle_add_batch(msg):
    logging.debug(f"handling {msg}")
    data = json.loads(msg['data'])
    eta = data['eta']
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(
        ref=data['ref'], sku=data['sku'], qty=data['qty'], eta=eta,
    )
    messagebus.handle(cmd, uow=unit_of_work.SqlAlchemyUnitOfWork())



CHANNEL_HANDLERS = {
    b'change_batch_quantity': handle_change_batch_quantity,
    b'allocate': handle_allocation,
    b'add_batch': handle_add_batch,
}


if __name__ == '__main__':
    main()
