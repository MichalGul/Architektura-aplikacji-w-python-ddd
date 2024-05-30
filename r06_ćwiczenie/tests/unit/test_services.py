import pytest
from allocation.adapters import repository
from allocation.service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):

    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeUnitOfWorkManager(unit_of_work.AbstractUnitOfWorkStarter):
    def __init__(self, uow):
        self.uow = uow

    def __enter__(self):
        return self.uow

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.uow.rollback()


def test_add_batch():
    uow = FakeUnitOfWork()
    fake_uow_manager = FakeUnitOfWorkManager(uow)

    services.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, fake_uow_manager)
    assert uow.batches.get("b1") is not None
    assert uow.committed


# @pytest.mark.skip('unskip and fix when ready')
def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    fake_uow_manager = FakeUnitOfWorkManager(uow)

    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, fake_uow_manager)
    result = services.allocate("o1", "COMPLICATED-LAMP", 10, fake_uow_manager)
    assert result == "batch1"


# @pytest.mark.skip('unskip and fix when ready')
def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    fake_uow_manager = FakeUnitOfWorkManager(uow)

    services.add_batch("b1", "AREALSKU", 100, None, fake_uow_manager)

    with pytest.raises(services.InvalidSku, match="Nieprawidłowa sku NONEXISTENTSKU"):
        services.allocate("o1", "NONEXISTENTSKU", 10, fake_uow_manager)


# @pytest.mark.skip('unskip and fix when ready')
def test_allocate_commits():
    uow = FakeUnitOfWork()
    fake_uow_manager = FakeUnitOfWorkManager(uow)

    services.add_batch("b1", "OMINOUS-MIRROR", 100, None, fake_uow_manager)
    services.allocate("o1", "OMINOUS-MIRROR", 10, fake_uow_manager)
    assert uow.committed
