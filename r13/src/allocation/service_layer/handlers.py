#pylint: disable=unused-argument
from __future__ import annotations
from dataclasses import asdict
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from allocation.domain import commands, events, model
from allocation.domain.model import OrderLine
if TYPE_CHECKING:
    from allocation.adapters import notifications
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


# class version
class AddBatchHandler:
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow

    def __call__(self, cmd: commands.CreateBatch):
        with self.uow:
            product = self.uow.products.get(sku=cmd.sku)
            if product is None:
                product = model.Product(cmd.sku, batches=[])
                self.uow.products.add(product)
            product.batches.append(model.Batch(
                cmd.ref, cmd.sku, cmd.qty, cmd.eta
            ))
            self.uow.commit()


def allocate(
        cmd: commands.Allocate, uow: unit_of_work.AbstractUnitOfWork
):
    line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f'Invalid sku {line.sku}')
        product.allocate(line)
        uow.commit()


# class version
class AllocateHandler:
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow

    def __call__(self, cmd: commands.Allocate):
        line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
        with self.uow:
            product = self.uow.products.get(sku=line.sku)
            if product is None:
                raise InvalidSku(f'Invalid sku {line.sku}')
            product.allocate(line)
            self.uow.commit()


def reallocate(
        event: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork
):
    allocate(commands.Allocate(**asdict(event)), uow=uow)


#class version
class ReallocateHandler:
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow

    def __call__(self, event: events.Deallocated):
        allocate_func = AllocateHandler(uow=self.uow)
        allocate_func(commands.Allocate(**asdict(event)))



def change_batch_quantity(
        cmd: commands.ChangeBatchQuantity, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


#class version
class ChangeBatchQuantityHandler:
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow

    def __call__(self, cmd: commands.ChangeBatchQuantity):
        with self.uow:
            product = self.uow.products.get_by_batchref(batchref=cmd.ref)
            product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
            self.uow.commit()



#pylint: disable=unused-argument

def send_out_of_stock_notification(
        event: events.OutOfStock, notifications: notifications.AbstractNotifications,
):
    notifications.send(
        'stock@made.com',
        f'Out of stock for {event.sku}',
    )


# class version
class SendOutOfStockNotificationHandler:
    def __init__(self, notifications: notifications.AbstractNotifications):
        self.notifications = notifications

    def __call__(self, event: events.OutOfStock):
        self.notifications.send(
            self.notifications.destination,
            f'Out of stock for {event.sku}',
        )


def publish_allocated_event(
        event: events.Allocated, publish: Callable,
):
    publish('line_allocated', event)


# class version
class PublishAllocatedEventHandler:
    def __init__(self, publish: Callable):
        self.publish = publish

    def __call__(self, event: events.Allocated):
        self.publish('line_allocated', event)


def add_allocation_to_read_model(
        event: events.Allocated, uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            'INSERT INTO allocations_view (orderid, sku, batchref)'
            ' VALUES (:orderid, :sku, :batchref)',
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref)
        )
        uow.commit()


# class version
class AddAllocationToReadModelHandler:
    def __init__(self, uow: unit_of_work.SqlAlchemyUnitOfWork):
        self.uow = uow

    def __call__(self, event:events.Allocated):
        with self.uow:
            self.uow.session.execute(
                'INSERT INTO allocations_view (orderid, sku, batchref)'
                ' VALUES (:orderid, :sku, :batchref)',
                dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref)
            )
            self.uow.commit()


def remove_allocation_from_read_model(
        event: events.Deallocated, uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            'DELETE FROM allocations_view '
            ' WHERE orderid = :orderid AND sku = :sku',
            dict(orderid=event.orderid, sku=event.sku)
        )
        uow.commit()


# class version
class RemoveAllocationFromReadModelHandler:
    def __init__(self, uow: unit_of_work.SqlAlchemyUnitOfWork):
        self.uow = uow

    def __call__(self, event: events.Deallocated):
        with self.uow:
            self.uow.session.execute(
                'DELETE FROM allocations_view '
                ' WHERE orderid = :orderid AND sku = :sku',
                dict(orderid=event.orderid, sku=event.sku)
            )
            self.uow.commit()


EVENT_HANDLERS = {
    events.Allocated: [publish_allocated_event, add_allocation_to_read_model],
    events.Deallocated: [remove_allocation_from_read_model, reallocate],
    events.OutOfStock: [send_out_of_stock_notification],
}  # type: Dict[Type[events.Event], List[Callable]]

COMMAND_HANDLERS = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]



EVENT_HANDLERS_CLASS = {
    events.Allocated: [PublishAllocatedEventHandler, AddAllocationToReadModelHandler],
    events.Deallocated: [RemoveAllocationFromReadModelHandler, ReallocateHandler],
    events.OutOfStock: [SendOutOfStockNotificationHandler]
    }

COMMAND_HANDLERS_CLASS = {
    commands.Allocate: AllocateHandler,
    commands.CreateBatch: AddBatchHandler,
    commands.ChangeBatchQuantity: ChangeBatchQuantityHandler
}