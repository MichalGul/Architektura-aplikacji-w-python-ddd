#pylint: disable=redefined-outer-name
import pytest
from sqlalchemy.orm import clear_mappers
from allocation import bootstrap, config
from allocation.domain import commands
from allocation.adapters import notifications
from allocation.service_layer import unit_of_work
from ..random_refs import random_sku
from twilio.rest import Client

@pytest.fixture
def bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.SMSNotifications(destination_number="+48606912603"),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()


def get_last_sms_from_twilio(sku):
    sid, token = map(config.get_sms_sid_and_token().get, ['sid', 'token'])
    client = Client(sid, token)
    messages = client.messages.list(limit=20)
    return next(m for m in messages if sku in str(m.body))

@pytest.mark.skip(reason="No pricing Twilio")
def test_out_of_stock_sms(bus):
    sku = random_sku()
    bus.handle(commands.CreateBatch('batch1', sku, 9, None))
    bus.handle(commands.Allocate('order1', sku, 10))

    sms_message = get_last_sms_from_twilio(sku)
    assert f'Out of stock for {sku}' in sms_message.body
    assert sms_message.to == "+48606912603"

