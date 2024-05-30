# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from typing import ContextManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from allocation import config
from allocation.adapters import repository
from contextlib import contextmanager


class AbstractUnitOfWork(abc.ABC):
    # Czy ta klasa powinna zawierać __enter__ i __exit__?
    # Czy menedżer kontekstu i UoW powinny być rozdzielone?
    # Wybór należy do Ciebie!

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError



DEFAULT_SESSION_FACTORY = sessionmaker(bind=create_engine(
    config.get_postgres_uri(),
))



# Jedną z możliwości jest zdefiniowanie funkcji start_uow
# lub UnitOfWorkStarter albo UnitOfWorkManager pełniącego rolę
# menedżera kontekstu. UoW zostaje osobną klasę
# zwracaną przez funkcję __enter__ menedżera kontekstu.
#
# Taki typ by działał?
AbstractUnitOfWorkStarter = ContextManager[AbstractUnitOfWork]


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory
        self.session = self.session_factory()
        self.batches = repository.SqlAlchemyRepository(self.session)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
        self.session.close()


class UnitOfWorkManager(AbstractUnitOfWorkStarter):
    def __init__(self, session_factory=None):
        self.uow: AbstractUnitOfWork = None
        self.session_factory = session_factory or DEFAULT_SESSION_FACTORY

    def __enter__(self) -> AbstractUnitOfWork:
        self.uow = SqlAlchemyUnitOfWork(self.session_factory)
        return self.uow

    def __exit__(self, *args):
        self.uow.rollback()


# @contextmanager
# def start_uow() -> AbstractUnitOfWorkStarter:
#     uow = SqlAlchemyUnitOfWork()
#
#     yield uow
#
#     uow.rollback()

