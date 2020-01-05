# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0

from traitlets.config.configurable import Configurable
from traitlets import List, Int, Instance

from .record import Record
from .mailbox import Mailbox


class EmailParser(Configurable):
    """A robinhood specific plain/text parser.
    The purpose is to find the minimal string in
    the text body containing the relevant transaction
    and then attempt to structure that data into
    proper records.

    The main entry point is the parse_orders method
    which expects a dictionary of the structure produced
    by the Mailbox's fetch_orders method.

    The keep variable that gets passed around would
    be better suited as a deque based on copious
    use of what amounts to popleft.
    """
    stop_phrases = List().tag(config=True)
    stop_chars = List().tag(config=True)
    debug = Int().tag(config=True)
    mailbox = Instance(Mailbox)
    months = {
        'January': 1, 'February': 2,
        'March': 3, 'April': 4, 'May': 5,
        'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10,
        'November': 11, 'December': 12
    }

    def dollar_to_float(self, dollar):
        return float(dollar.strip('$').replace(',', ''))

    def banner(self, tup, width=10, just='<', extra=None):
        """Print a tuple"""
        fmtr = f'{{:{just}{width}}}' * len(tup)
        fmt = (t if t is not None else '' for t in tup)
        print(fmtr.format(*fmt), end=' ')
        print(extra or '')

    def parse_orders(self):
        """Iterate over the emails, do some simple
        configurable text normalization and then
        attempt to parse the email into a record.
        Returns a list of dictionaries attempting
        to conform to the spec for the Record
        class, as well as a list of all email bodies
        that were not parsed.
        """
        bodies = self.mailbox.fetch_orders()
        nrec = sum((len(bods) for bods in bodies.values()))
        print(f'parsing {nrec} orders')
        records, not_parsed = [], []
        for subject, bods in bodies.items():
            print(f'{len(bods)} with subject: {subject}')
            if self.debug:
                self.banner(('order', 'dir', 'count', 'amount',
                             'kind', 'ticker', 'strike', 'order',
                             'expir', 'avg_price', 'month', 'day',
                             'year', 'hour', 'minute', 'merid',
                             'prt', 'prt_amt', 'prt_unit',
                             'unfill', 'prt_prc'))
            for (idx, bod) in bods:
                for stop in self.stop_chars:
                    bod = bod.replace(stop, '')
                for stop_phrase in self.stop_phrases:
                    bod = bod.split(stop_phrase)[0]
                bod = ' '.join((
                    ' '.join(ln.split()) for ln in bod.splitlines()
                ))
                try:
                    records.append(
                        self.parse_order_to_record(subject, idx, bod)
                    )
                except Exception as e:
                    not_parsed.append((subject, idx, bod))
                    if self.debug > 1:
                        print(str(e), bod)
        print(f'parsed {len(records)} records')
        print(f'missed {len(not_parsed)} emails')
        if len(not_parsed):
            print('make c.EmailParser.debug > 1 to see bodies not parsed')
        return records, not_parsed

    def determine_order_type(self, r, keep):
        """Crypto is slightly different than equities, set
        some conditional values in the determination. Hope
        to reduce most customization to this function and
        streamline all other methods.
        """
        if r['direction'] == 'open':
            r['direction'] = 'buy'
            r['kind'] = 'contract'
            count, r['ticker'], multi, _, *keep = keep
            degen, r['strike'] = multi.split('-')
            r['count'] = int(count) * int(degen)
        else:
            if r['order_type'] == 'Your':
                r['kind'] = 'crypto'
                amt, _, *keep = keep
                r['total_amount'] = self.dollar_to_float(amt)
                r.pop('order_type')
            else:
                cnt, r['kind'], _, *keep = keep
                r['count'] = int(cnt)
            r['ticker'], *keep = keep
            r['kind'] = r['kind'].rstrip('s')
        # handle options details
        if keep[0].startswith('$'):
            r['strike'], r['order'], r['expiration'], *keep = keep
        return r, keep

    def consume_datetime(self, r, keep):
        """Isolate each component of the execution datetime
        and let transformation occur elsewhere.
        """
        cnt = self.keep_on(keep, kind='month')
        month, day, r['year'], *keep = keep[cnt:]
        r['month'] = self.months[month]
        r['day'] = int(''.join((c for c in day if c.isnumeric())))
        # found a broken year so..
        if len(r['year']) != 4 and keep[0].isnumeric():
            r['year'] = r['year'] + keep[0]
            keep = keep[1:]
        r['year'] = int(r['year'])
        if keep[0] == 'at':
            keep = keep[1:]
        # if time is broken, find the M and combine
        cnt = self.keep_on(keep, kind='meridiem')
        time = ''.join(keep[:cnt]).strip('at')
        r['hour'], r['minute'] = (int(t) for t in time.split(':'))
        m, *keep = keep[cnt:]
        r['meridiem'] = m.strip('.')
        return r, keep

    def keep_on(self, keep, kind='dollar'):
        """Find the next occurrence of a thing of kind
        or return the length of keep"""
        cnt = 0
        if kind == 'dollar':
            while cnt < len(keep) and not keep[cnt].startswith('$'):
                cnt += 1
        elif kind == 'number':
            while cnt < len(keep) and not keep[cnt].isnumeric():
                cnt += 1
        elif kind == 'month':
            while cnt < len(keep) and not keep[cnt] in self.months.keys():
                cnt += 1
        elif kind == 'meridiem':
            while (cnt < len(keep) and not
                   any((m in keep[cnt] for m in ('AM', 'PM')))):
                cnt += 1
        return cnt

    def consume_partial_order(self, r, keep):
        """Parse the partial execution data"""
        # partial fill crypto
        if keep[0].startswith('$'):
            partial, _, unit, *keep = keep
            cnt = self.keep_on(keep)
            unfill, *keep = keep[cnt:]
            r['unfilled_amount'] = self.dollar_to_float(unfill)
        else:
            cnt = self.keep_on(keep, kind='number')
            partial, unit, *keep = keep[cnt:]
            if unit == 'of':
                unit, *keep = keep[1:]
            cnt = self.keep_on(keep)
            amount, *keep = keep[cnt:]
            r['partial_price'] = self.dollar_to_float(amount)
            if keep[0] == 'and':
                r['unfilled_amount'] = self.dollar_to_float(keep[1])
                keep = keep[2:]
        r['partial_amount'] = self.dollar_to_float(partial)
        r['partial_unit'] = unit.rstrip('s')
        return r, keep

    def parse_prices(self, r, keep):
        """Attempts to find all the prices in the
        body (except the first price in crypto is
        already consumed at this point).
        Assumes first price is an average
        price and second price is a total amount.
        Does not process more than 2 prices.
        """
        # get [average, [total]] prices
        prices = []
        while True:
            try:
                cnt = self.keep_on(keep)
                if cnt == len(keep):
                    break
                price, *keep = keep[cnt:]
                prices.append(price)
            except IndexError:
                break
        for price, attr in zip(prices, ['avg_price', 'total_amount']):
            r[attr] = self.dollar_to_float(price)
        return r

    def parse_order_to_record(self, subject, idx, bod):
        """Assumes a slowly changing format for parsing
        the data concerning an order execution email."""
        before_order, after_order = bod.split('order to')
        r = {'order_type': before_order.split()[-1],
             'subject': subject, 'email_id': idx}
        keep = after_order.split()
        r['direction'] = keep[0]
        r, keep = self.determine_order_type(r, keep[1:])
        r = self.parse_prices(r, keep.copy())
        r, keep = self.consume_datetime(r, keep)
        try:
            r, keep = self.consume_partial_order(r, keep)
            r['partial'] = True
        except (ValueError, IndexError):
            r['partial'] = False
        if self.debug:
            self.banner((r.get('order_type'),
                         r.get('direction'),
                         r.get('count'),
                         r.get('total_amount'),
                         r.get('kind'),
                         r.get('ticker'),
                         r.get('strike'),
                         r.get('order'),
                         r.get('expiration'),
                         r.get('avg_price'),
                         r.get('month'),
                         r.get('day'),
                         r.get('year'),
                         r.get('hour'),
                         r.get('minute'),
                         r.get('meridiem'),
                         r.get('partial'),
                         r.get('partial_amount'),
                         r.get('partial_unit'),
                         r.get('unfilled_amount'),
                         r.get('partial_price')))
        return Record(**r)


class StatementParser(Configurable):
    debug = Int().tag(config=True)

    def parse_orders(self):
        dumps = {}
        for path in self.statements[:1]:
            with open(path, 'r') as f:
                dumps[path] = f.read()
            print("len split on portfolio", len(dumps[path].split(self.tokens[0])))
            print("len split on activity", len(dumps[path].split(self.tokens[1])))

