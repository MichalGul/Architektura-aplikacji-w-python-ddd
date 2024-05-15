# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from typing import ContextManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from allocation import config
from allocation.adapters import repository



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


class SqlAlchemyUnitOfWork:
    ...

# Jedną z alternatyw może być definicja funkcji `start_uow`
# lub UnitOfWorkStarter lub UnitOfWorkManager pełniący rolę
# menedżera kontekstu. Wówczas UoW zostaje osobną klasą
# zwracaną przez funkcję __enter__ menedżera kontekstu.
#
# Taki typ by działał?
# AbstractUnitOfWorkStarter = ContextManager[AbstractUnitOfWork]
