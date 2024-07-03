#pylint: disable=too-few-public-methods
import abc
import smtplib
from allocation import config
from twilio.rest import Client

class AbstractNotifications(abc.ABC):
    destination: str = ""

    @abc.abstractmethod
    def send(self, destination, message):
        raise NotImplementedError


DEFAULT_HOST = config.get_email_host_and_port()['host']
DEFAULT_PORT = config.get_email_host_and_port()['port']

TWILIO_ACCOUNT_SID = config.get_sms_sid_and_token()['sid']
TWILIO_AUTH_TOKEN = config.get_sms_sid_and_token()['token']

class EmailNotifications(AbstractNotifications):

    def __init__(self, smtp_host=DEFAULT_HOST, port=DEFAULT_PORT, destination_email='default@example.com'):
        self.server = smtplib.SMTP(smtp_host, port=port)
        self.server.noop()
        self.destination = destination_email

    def send(self, destination, message):
        msg = f'Subject: allocation service notification\n{message}'
        self.server.sendmail(
            from_addr='allocations@example.com',
            to_addrs=[destination],
            msg=msg
        )


class SMSNotifications(AbstractNotifications):
    def __init__(self, account_sid=TWILIO_ACCOUNT_SID, auth_token=TWILIO_AUTH_TOKEN, destination_number='0000000000'):
        self.client = Client(account_sid, auth_token)
        self.destination = destination_number

    def send(self, destination, message):
        message_send = self.client.messages.create(
            body=message,
            from_="+17178373511", # Twilio test magic number
            to=destination
        )
        print(message_send.body)
        return message_send.body