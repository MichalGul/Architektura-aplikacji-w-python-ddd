from __future__ import annotations

from datetime import date
from typing import Optional

import model
from model import OrderLine, Batch
from repository import AbstractRepository

class InvalidSku(Exception):
    pass

class ResourceUnallocated(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}

def is_allocated(line: OrderLine, batch:Batch):
    return batch.has_allocated(line)


def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f'Invalid sku {line.sku}')
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref


def deallocate(batch: Batch, line: OrderLine, session):
    if not is_allocated(line, batch):
        raise ResourceUnallocated(f"Line {line.orderid} was not allocated in batch {batch.reference}")
    batch.deallocate(line)
    session.commit()
    return batch.reference


def add_batch(
        ref: str, sku: str, qty: int, eta: Optional[date],
        repo: AbstractRepository, session,
):
    repo.add(model.Batch(ref, sku, qty, eta))
    session.commit()
