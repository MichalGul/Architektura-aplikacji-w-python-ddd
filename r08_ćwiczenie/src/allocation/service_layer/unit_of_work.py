# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from typing import Protocol
from allocation import config
from allocation.adapters import repository
from . import messagebus


class AbstractUnitOfWork(Protocol):
    products: repository.AbstractRepository

    def __enter__(self) -> AbstractUnitOfWork:
        return self

    def __exit__(self, *args):
        self.rollback()

    # def commit(self):
    #     self._commit()
    #     self.publish_events()

    def publish_events(self):
        for product in self.products.seen:
            while product.events:
                event = product.events.pop(0)
                messagebus.handle(event)

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError



DEFAULT_SESSION_FACTORY = sessionmaker(bind=create_engine(
    config.get_postgres_uri(),
    isolation_level="REPEATABLE READ",
))


class TrackingUnitOfWork:

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def __enter__(self):
        return self.uow.__enter__()

    def __exit__(self, *args):
        self.uow.__exit__(*args)

    def commit(self):
        self.uow.commit()
        self.uow.publish_events()

    def rollback(self):
        self.uow.rollback()

    @property
    def products(self):
        return self.uow.products



class SqlAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()  # typ: Session
        self.products = repository.TrackingRepository(
            repository.SqlAlchemyRepository(self.session)
        )
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()


