import os

_root = os.path.dirname(os.path.abspath(__file__))

from stonks.record import Record
from stonks.mailbox import Mailbox
from stonks.parser import EmailParser, StatementParser
from stonks.processor import Processor

