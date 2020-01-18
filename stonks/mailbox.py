# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0

from collections import defaultdict

from traitlets.config.configurable import Configurable
from traitlets import Unicode, List

from imapclient import IMAPClient


class Mailbox(Configurable):
    """Configurable IMAP client wrapper.
    The idea is to first fetch envelopes and search
    through subject lines containing key words found
    in the config based filters. Then a second round
    of fetches is made to get the plain text body of
    the email.

    The main entry point is the fetch_orders method
    and returns a dictionary of the following structure:
        {subject: [(idx, body), ...]}
    """
    user = Unicode().tag(config=True)
    pwd = Unicode().tag(config=True)
    hostname = Unicode().tag(config=True)
    folder = Unicode().tag(config=True)
    broker = Unicode().tag(config=True)
    filters = List().tag(config=True)

    def fetch_envelopes(self, c):
        """Get all email ids coming from the broker
        email address and filter them by key words
        in the subject of the email."""
        print('fetching envelopes')
        msgs = c.search(['FROM', self.broker])
        envs = c.fetch(msgs, ['ENVELOPE'])
        emails_by_name = defaultdict(list)
        for idx, data in envs.items():
            env = data[b'ENVELOPE']
            subject = env.subject.decode('utf-8')
            # deprecate self.filters config
            emails_by_name[subject].append(idx)
        stop = ['login', 'account', 'statement', 'expiring']
        orders = {
            key: val for key, val in
            emails_by_name.items()
            if len(val) > 1 and
            not any((s in key.lower().split() for s in stop))
        }
        print(f'fetched {len(emails_by_name)} subjects')
        return orders

    def fetch_bodies(self, c, emails_by_name):
        """Get the plain text bodies of the previously
        filtered emails. Chunks the fetch by unique
        subject lines.

        Returns:
            {subject: [(idx, body), ...]}
        """
        print('fetching bodies in chunks')
        orders = defaultdict(list)
        for subject, idxs in emails_by_name.items():
            # TODO : get body structure to
            #        assert text/plain is BODY[1]
            bodies = c.fetch(idxs, ['BODY[1]'])
            for idx, data in bodies.items():
                body = data[b'BODY[1]'].decode('utf-8')
                orders[subject].append((idx, body))
        return orders

    def fetch_orders(self):
        """Gets all broker emails from the email address
        according to the configurations set in the cfg.py
        file."""
        print("fetching orders:", self.hostname)
        # TODO : make mailbox optionally accept a watermark
        #        so that cached data need not be re-pulled
        with IMAPClient(host=self.hostname) as c:
            c.login(self.user, self.pwd)
            c.select_folder(self.folder, readonly=True)
            emails_by_name = self.fetch_envelopes(c)
            orders = self.fetch_bodies(c, emails_by_name)
        return orders

