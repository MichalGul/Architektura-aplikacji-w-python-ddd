#pylint: disable=unused-argument
from __future__ import annotations
from dataclasses import asdict
from typing import TYPE_CHECKING
from allocation.adapters import email, redis_eventpublisher
from allocation.domain import commands, events, model
from allocation.domain.model import OrderLine
if TYPE_CHECKING:
    from . import unit_of_work


class InvalidSku(Exception):
    pass


def add_batch(
        cmd: commands.CreateBatch, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = model.Product(cmd.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(
            cmd.ref, cmd.sku, cmd.qty, cmd.eta
        ))
        uow.commit()


def allocate(
        cmd: commands.Allocate, uow: unit_of_work.AbstractUnitOfWork
):
    line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f'Nieprawidłowa sku {line.sku}')
        product.allocate(line)
        uow.commit()

def reallocate(
        event: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(sku=event.sku)
        product.events.append(commands.Allocate(**asdict(event)))
        uow.commit()

def change_batch_quantity(
        cmd: commands.ChangeBatchQuantity, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


#pylint: disable=unused-argument

def send_out_of_stock_notification(
        event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork,
):
    email.send(
        'stock@made.com',
        f'Out of stock for {event.sku}',
    )


def publish_allocated_event(
        event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork,
):
    redis_eventpublisher.publish('line_allocated', event)


# def add_allocation_to_read_model(
#         event: events.Allocated, uow: unit_of_work.SqlAlchemyUnitOfWork,
# ):
#     with uow:
#         uow.session.execute(
#             'INSERT INTO allocations_view (orderid, sku, batchref)'
#             ' VALUES (:orderid, :sku, :batchref)',
#             dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref)
#         )
#         uow.commit()
#
# def remove_allocation_from_read_model(
#         event: events.Deallocated, uow: unit_of_work.SqlAlchemyUnitOfWork,
# ):
#     with uow:
#         uow.session.execute(
#             'DELETE FROM allocations_view '
#             ' WHERE orderid = :orderid AND sku = :sku',
#             dict(orderid=event.orderid, sku=event.sku)
#         )
#         uow.commit()


# using view model stored in redis instead of read model. It will pass same tests ass using allocations_view

def add_allocation_to_read_model(event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork):
    redis_eventpublisher.update_readmodel(event.orderid, event.sku, event.batchref)


def remove_allocation_from_read_model(event: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork):
    redis_eventpublisher.update_readmodel(event.orderid, event.sku, None)


