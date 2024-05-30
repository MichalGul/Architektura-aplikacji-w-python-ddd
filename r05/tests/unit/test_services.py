import pytest
from domain import model
from adapters import repository
from domain.model import OrderLine, allocate
from service_layer import services
import datetime


class FakeRepository(repository.AbstractRepository):

    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeSession():
    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, repo, session)
    assert repo.get("b1") is not None
    assert session.committed


def test_allocate_returns_allocation():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, repo, session)
    result = services.allocate("o1", "COMPLICATED-LAMP", 10, repo, session)
    assert result == "batch1"


def test_allocate_errors_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "AREALSKU", 100, None, repo, session)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, repo, FakeSession())


def test_commits():
    repo, session = FakeRepository([]), FakeSession()
    session = FakeSession()
    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, repo, session)
    services.allocate("o1", "OMINOUS-MIRROR", 10, repo, session)
    assert session.committed is True


# domain layer test
def test_prefers_current_stock_batches_to_shipments():
    now = datetime.datetime.now()
    in_stock_batch = model.Batch("batch1", "COMPLICATED-LAMP", 100, eta=now)
    shipment_batch = model.Batch("batch2", "COMPLICATED-LAMP", 100, eta= now + datetime.timedelta(days=1) )
    line = OrderLine("oref", "COMPLICATED-LAMP", 10)

    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


# service layer test bad because ther relte on domain layer
def teste_prefers_warehouse_batches_to_shipments():
    now = datetime.datetime.now()
    in_stock_batch = model.Batch("batch1", "COMPLICATED-LAMP", 100, eta=now)
    shipment_batch = model.Batch("batch2", "COMPLICATED-LAMP", 100, eta= now + datetime.timedelta(days=1) )
    repo = FakeRepository([in_stock_batch, shipment_batch])
    session = FakeSession()

    line = OrderLine("oref", "COMPLICATED-LAMP", 10)
    services.allocate(line, "COMPLICATED-LAMP", 10, repo, session)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100