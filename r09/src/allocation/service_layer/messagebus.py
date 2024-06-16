from __future__ import annotations
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from allocation.domain import events
from . import handlers
if TYPE_CHECKING:
    from . import unit_of_work

HANDLERS = {
    events.BatchCreated: [handlers.add_batch],
    events.BatchQuantityChanged: [handlers.change_batch_quantity],
    events.AllocationRequired: [handlers.allocate],
    events.OutOfStock: [handlers.send_out_of_stock_notification],

}  # type: Dict[Type[events.Event], List[Callable]]


class AbstractMessageBus:
    HANDLERS: Dict[Type[events.Event], List[Callable]]

    def handle(self, event: events.Event):
        for handler in self.HANDLERS[type(event)]:
            handler(event)


class MessageBus(AbstractMessageBus):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.uow = uow
        self.HANDLERS = HANDLERS

    def handle(self, event: events.Event):
        results = []
        queue = [event]
        while queue:
            event = queue.pop(0)
            for handler in HANDLERS[type(event)]:
                results.append(handler(event, uow=self.uow))
                queue.extend(self.uow.collect_new_events())
        return results


class FakeMessageBus(AbstractMessageBus):

    def __init__(self, uow: unit_of_work.AbstractUnitOfWork):
        self.HANDLERS = {
            events.BatchCreated: [handlers.add_batch],
            events.BatchQuantityChanged: [handlers.change_batch_quantity],
            events.AllocationRequired: [handlers.allocate],
            events.OutOfStock: [lambda event: self.events_published.append(event)],
        }
        self.events_published = []
        self.uow = uow

    def handle(self, event: events.Event):
        for handler in self.HANDLERS[type(event)]:
            handler(event, uow=self.uow)
            self.events_published.extend(self.uow.collect_new_events())



def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow=uow))
            queue.extend(uow.collect_new_events())
    return results



