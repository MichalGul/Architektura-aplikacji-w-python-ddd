import inspect
from typing import Callable
from allocation.adapters import orm
from allocation.adapters.redis_eventpublisher import AbstractPublisher, RedisPublisher
from allocation.adapters.notifications import (
    AbstractNotifications, EmailNotifications
)
from allocation.service_layer import handlers, messagebus, unit_of_work


def bootstrap(
    start_orm: bool = True,
    uow: unit_of_work.AbstractUnitOfWork = unit_of_work.SqlAlchemyUnitOfWork(),
    notifications: AbstractNotifications = None,
    publish: AbstractPublisher = RedisPublisher,
) -> messagebus.MessageBus:

    if notifications is None:
        notifications = EmailNotifications(destination_email="stock@made.com")

    if start_orm:
        orm.start_mappers()

    dependencies = {'uow': uow, 'notifications': notifications, 'publish': publish}


    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies)
            for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }


    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    injected_event_class_handlers = {
        event_type: [inject_class_dependencies(handler, dependencies) for handler in event_handlers]
        for event_type, event_handlers in handlers.EVENT_HANDLERS_CLASS.items()

    }

    injected_command_class_handlers = {
        command_type: inject_class_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS_CLASS.items()}


    # return messagebus.MessageBus(
    #     uow=uow,
    #     event_handlers=injected_event_handlers,
    #     command_handlers=injected_command_handlers,
    # )

    return messagebus.MessageBus(
        uow=uow,
        event_handlers=injected_event_class_handlers,
        command_handlers=injected_command_class_handlers,
    )


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda message: handler(message, **deps)


def inject_class_dependencies(cls, dependencies):
    params = inspect.signature(cls).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return cls(**deps)