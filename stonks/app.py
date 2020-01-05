#!/usr/bin/env python
"""
"""
import os
import sys
from functools import partial

from traitlets.config.application import Application
from traitlets import Unicode, default
import pandas as pd

from stonks import _root
from stonks.mailbox import Mailbox
from stonks.parser import Parser
from stonks.processor import Processor

_here = partial(os.path.join, _root, 'conf')

class App(Application):
    cfg_file = Unicode(_here('cfg.py')).tag(config=True)
    sec_file = Unicode().tag(config=True)

    @default('sec_file')
    def _default_sec_file(self):
        return os.environ.get('STONKS_SECRETS', _here('pwd.py'))

    def initialize(self, argv=None):
        self.parse_command_line(argv)
        if self.cfg_file:
            self.load_config_file(self.cfg_file)
        if self.sec_file:
            self.load_config_file(self.sec_file)
        self.mailbox = Mailbox(config=self.config)
        self.parser = Parser(config=self.config)
        self.processor = Processor(config=self.config)

    def run(self):
        orders = self.mailbox.fetch_orders()
        records, not_parsed = self.parser.parse_orders(orders)
        df = self.processor.records_to_df(records)
        self.processor.analyze(df)


if __name__ == '__main__':
    app = App()
    app.initialize(sys.argv)
    app.run()
