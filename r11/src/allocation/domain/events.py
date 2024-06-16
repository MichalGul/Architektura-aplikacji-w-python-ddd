# pylint: disable=too-few-public-methods
from dataclasses import dataclass
from typing import Optional
from datetime import date

class Event:
    pass

@dataclass
class Allocated(Event):
    orderid: str
    sku: str
    qty: int
    batchref: str


@dataclass
class BatchCreated(Event):
    ref: str
    sku: str
    qty: int


@dataclass
class OutOfStock(Event):
    sku: str
