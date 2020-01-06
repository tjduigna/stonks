#!/usr/bin/env python
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0
"""
"""
import os
import sys
from functools import partial

from traitlets.config.application import Application
from traitlets import Unicode, default, validate

from stonks import _root
from stonks.mailbox import Mailbox
from stonks.parser import EmailParser, StatementParser
from stonks.processor import Processor


_here = partial(os.path.join, _root, 'conf')


class App(Application):
    cfg_file = Unicode(_here('cfg.py')).tag(config=True)
    sec_file = Unicode().tag(config=True)
    mode = Unicode('email').tag(config=True)

    @default('sec_file')
    def _default_sec_file(self):
        return os.environ.get('STONKS_SECRETS', _here('pwd.py'))

    @validate('mode')
    def _is_valid_mode(self, change):
        if change.value not in ['email', 'dumps']:
            raise Exception(f"validation error {change.value}")
        return change.value

    def initialize(self, argv=None):
        self.parse_command_line(argv)
        if self.cfg_file:
            self.load_config_file(self.cfg_file)
        if self.sec_file:
            self.load_config_file(self.sec_file)
        if self.mode == 'email':
            self.parser = EmailParser(config=self.config,
                                      mailbox=Mailbox(config=self.config))
        else:
            self.parser = StatementParser(config=self.config)
        self.processor = Processor(config=self.config)

    def run(self):
        records, not_parsed = self.parser.parse_orders()
        if self.mode == 'email':
            df = self.processor.records_to_df(records)
            self.processor.analyze(df)
        else:
            print(records, not_parsed)
            #records, not_parsed = self.parser.parse_orders()


if __name__ == '__main__':
    app = App()
    app.initialize(sys.argv)
    app.run()
