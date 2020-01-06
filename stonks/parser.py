# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0
import os
from io import StringIO
from collections import defaultdict

from traitlets.config.configurable import Configurable
from traitlets import List, Int, Instance, Unicode

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

from .record import Record
from .mailbox import Mailbox


class EmailParser(Configurable):
    """A robinhood specific plain/text email parser.
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
    """A robinhood specific plain text pdf statement parser.
    Attempts a page-by-page determination of the content
    in hopes to be less brittle.
    """
    debug = Int().tag(config=True)
    portfolio_token = Unicode().tag(config=True)
    portfolio_tokens = List().tag(config=True)
    activity_token = Unicode().tag(config=True)
    activity_tokens = List().tag(config=True)
    statements = List().tag(config=True)

    def parse_txt_fmt(self, path):
        with open(path, 'r') as f:
            return f.read()

    def parse_pdf_fmt(self, path):
        resource = PDFResourceManager()
        ret = StringIO()
        dev = TextConverter(resource, ret, laparams=LAParams())
        with open(path, 'rb') as f:
            interp = PDFPageInterpreter(resource, dev)
            pagenos = set()
            for page in PDFPage.get_pages(
                    f, pagenos, maxpages=0, password='',
                    caching=True, check_extractable=True):
                interp.process_page(page)
            text = ret.getvalue()
        dev.close()
        ret.close()
        return text

    def parse_orders(self):
        dumps = defaultdict(dict)
        for path in self.statements:
            print(f"reading {path}, exists {os.path.isfile(path)}")
            ext = path.split('.')[-1]
            raw = {'pdf': self.parse_pdf_fmt,
                   'txt': self.parse_txt_fmt}[ext](path)
            dumps[path]['raw'] = raw
            self.parse_pages(path, dumps, raw)
        return None, None

    def parse_pages(self, path, dumps, text):
        """This is not sufficient to parse the pdf"""
        begin, *pages = text.split('Page ')
        print(f"statement has {len(pages)} pages")
        ports, acts = [], []
        for i, page in enumerate(pages):
            pageno, period, name_acct, addr, *norm = [
                ln.strip() for ln in page.splitlines() if ln.strip()
            ]
            page = ' '.join((
                ' '.join(ln.split()) for ln in page.splitlines()
            ))
            print(f"parsing page {pageno} {period} user * addr *")
            print(page[:100])
            headers = (pageno, period, name_acct, addr)
            act = self.parse_activity(page)
            if act is not None:
                acts.append((*headers, act))

    def parse_portfolio(self, page):
        split = page.split(self.portfolio_tokens[0])
        if len(split) == 1: return
        split = ' '.join([self.portfolio_tokens[0], split[1]])
        split = split.split(self.activity_token)[0]
        split = split.split(self.portfolio_tokens[-1])[1].split()
        #print("portfolio", len(split), split)

    def parse_activity(self, page):
        split = page.split(self.activity_tokens[0])
        if len(split) == 1: return
        split = ' '.join([self.activity_tokens[0], split[1]]).split()
        good = []
        # smh
        while True:
            try:
                cnt = 0
                while cnt < len(split) and split[cnt] in self.activity_tokens:
                    cnt += 1
                split = split[cnt:]
                if '/' in split[1] and split[3].startswith('$'):
                    good.append(('contract', *split[:4]))
                    split = split[4:]
                else:
                    cnt = 0
                    while 'CUSIP' not in split[cnt]:
                        cnt += 1
                    wordy = ' '.join(split[:cnt + 2])
                    good.append(('share', wordy))
                    split = split[cnt + 2:]
            except IndexError:
                break
        print("activity", "split", len(split),
              "line items", len(good),
              good[0] if len(good) else None,
              good[-1] if len(good) else None)
