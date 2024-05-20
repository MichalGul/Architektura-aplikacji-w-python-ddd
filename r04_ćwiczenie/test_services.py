import pytest
import model
import repository
import services


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


def test_returns_allocation():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENTSKU", 10)
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine('o1', 'OMINOUS-MIRROR', 10)
    batch = model.Batch('b1', 'OMINOUS-MIRROR', 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed is True


def test_deallocate_decrements_available_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, session)
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)
    services.allocate(line, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90
    services.deallocate(batch, line)
    assert batch.available_quantity == 100

def test_deallocate_decrements_correct_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b2", "Some-shiet", 100, None, repo, session)
    services.add_batch("b3", "Some-other-shiet", 88, None, repo, session)
    line_shiet = model.OrderLine("o2", "Some-shiet", 5)
    line_shiet_other = model.OrderLine("o3", "Some-other-shiet", 5)
    services.allocate(line_shiet, repo, session)
    services.allocate(line_shiet_other, repo, session)

    b2 = repo.get(reference="b2")
    b3 = repo.get(reference="b3")
    assert b2.available_quantity == 95
    assert b3.available_quantity == 83

    b3.deallocate(line_shiet_other)
    assert b3.available_quantity == 88
    assert b2.available_quantity == 95


def test_trying_to_deallocate_unallocated_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b2", "Some-shiet", 100, None, repo, session)
    line_shiet = model.OrderLine("o2", "Some-shiet", 5)
    b2 = repo.get(reference="b2")
    with pytest.raises(services.ResourceUnallocated,  match=f"Line o2 was not allocated in batch b2"):
        services.deallocate(b2, line_shiet)
