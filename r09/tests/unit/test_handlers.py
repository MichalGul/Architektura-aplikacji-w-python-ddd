# pylint: disable=no-self-use
from datetime import date
from unittest import mock
import pytest

from allocation.adapters import repository
from allocation.domain import events
from allocation.service_layer import handlers, messagebus, unit_of_work
from allocation.service_layer.messagebus import FakeMessageBus, MessageBus


class FakeRepository(repository.AbstractRepository):

    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref):
        return next((
            p for p in self._products for b in p.batches
            if b.reference == batchref
        ), None)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeUnitOfWorkWithFakeMessageBus(FakeUnitOfWork):

    def __init__(self):
        super().__init__()
        self.events_published = []

    def publish_events(self):
        for product in self.products.seen:
            while product.events:
                event = product.events.pop(0)
                self.events_published.append(event)

    def commit(self):
        self._commit()
        self.publish_events()





class TestAddBatch:

    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        messagebus = MessageBus(uow=uow)

        messagebus.handle(
            events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None)
        )
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed


    def test_for_existing_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "GARISH-RUG", 100, None), uow)
        messagebus.handle(events.BatchCreated("b2", "GARISH-RUG", 99, None), uow)
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


class TestAllocate:

    def test_returns_allocation(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("batch1", "COMPLICATED-LAMP", 100, None), uow
        )
        results = messagebus.handle(
            events.AllocationRequired("o1", "COMPLICATED-LAMP", 10), uow
        )
        assert results.pop(0) == "batch1"


    def test_errors_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "AREALSKU", 100, None), uow)

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            messagebus.handle(
                events.AllocationRequired("o1", "NONEXISTENTSKU", 10), uow
            )

    def test_commits(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("b1", "OMINOUS-MIRROR", 100, None), uow
        )
        messagebus.handle(
            events.AllocationRequired("o1", "OMINOUS-MIRROR", 10), uow
        )
        assert uow.committed


    def test_sends_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("b1", "POPULAR-CURTAINS", 9, None), uow
        )

        with mock.patch("allocation.adapters.email.send") as mock_send_mail:
            messagebus.handle(
                events.AllocationRequired("o1", "POPULAR-CURTAINS", 10), uow
            )
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com", f"Brak na stanie POPULAR-CURTAINS"
            )


class TestChangeBatchQuantity:

    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("batch1", "ADORABLE-SETTEE", 100, None), uow
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        messagebus.handle(events.BatchQuantityChanged("batch1", 50), uow)

        assert batch.available_quantity == 50


    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        # this executes chain of events in test below we implement isolated version with fake message bus
        messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)

        # order1 lub order2 zostanie dezalokowane, więc będziemy mieć 25 - 20
        assert batch1.available_quantity == 5
        # i 20 zostanie alokowane do następnej partii
        assert batch2.available_quantity == 30


    def test_reallocates_if_necessary_isolated(self):
        uow = FakeUnitOfWorkWithFakeMessageBus()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]

        for e in event_history:
            messagebus.handle(e, uow)



        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)

        [reallocation_event] = uow.events_published

        assert isinstance(reallocation_event, events.AllocationRequired)
        assert reallocation_event.orderid in {"order1", "order2"}
        assert reallocation_event.sku == "INDIFFERENT-TABLE"

    def test_reallocates_if_necessary_isolated_v2(self):
        uow = FakeUnitOfWork()
        messagebus = FakeMessageBus(uow=uow)

        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]

        for e in event_history:
            messagebus.handle(e)

        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("batch1", 25))

        [reallocation_event] = messagebus.events_published

        assert isinstance(reallocation_event, events.AllocationRequired)
        assert reallocation_event.orderid in {"order1", "order2"}
        assert reallocation_event.sku == "INDIFFERENT-TABLE"