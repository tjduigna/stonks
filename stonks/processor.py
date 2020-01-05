# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0
import datetime as dt

import pandas as pd
from traitlets.config.configurable import Configurable
from traitlets import Int, Float, TraitType


class Processor(Configurable):
    """Collect data-processing algorithms on dataframes
    conforming to the Record spec.
    """
    debug = Int().tag(config=True)
    total_deposit = Float().tag(config=True)

    def records_to_df(self, records):
        """Convert a list of Configurable data
        structures to a dataframe."""
        rec = records[0].__class__
        attrs = [
            key for key, val in vars(rec).items()
            if isinstance(val, TraitType)
        ]
        df = pd.DataFrame.from_records((
            {key: getattr(rec, key, None) for key in attrs}
            for rec in records
        ))
        print(f'dataframe has shape {df.shape}')
        return df

    def add_date_and_fix_expir_year(self, df):
        # the expiry date is given with no year if
        # it's unambiguous with the execution date
        update = df[df['expiration'].str.len() == 5].index
        df.loc[update, 'expiration'] = df.loc[update, 'expiration'].str.cat(
            df.loc[update, 'year'].astype(str).str[2:], sep='/')
        # compute total_amount from avg_price and count
        update = df[df['total_amount'] == 0].index
        # try to compute partial orders
        # TODO : partial_amount is apparently poorly named
        #        should be partial_count?
        upd = df[df['partial_amount'] > 0].index
        df.loc[upd, 'count'] = df.loc[upd, 'partial_amount']
        df.loc[update, 'total_amount'] = df.loc[update, 'count'] * df.loc[update, 'avg_price']
        #df['execution_date'] = pd.to_datetime(
        #    df['year'].apply('{:04d}'.format).str.cat(
        #        df['month'].apply('{:02d}'.format).str.cat(
        #            df['day'].apply('{:02d}'.format)
        #        )
        #    )
        #)
        return df

    def compute_positions(self, df):
        inputs = ['ticker', 'strike', 'order', 'expiration']
        outputs = ['sells', 'buys', 'count', 'amount']
        grps = df.groupby(inputs)
        pos = []
        print("computing PNL per position")
        if self.debug:
            print(('tick', 'strk', 'ord', 'exp', 'sell', 'buy', 'cnt', 'amt'))
        for tup, grp in grps:
            sub = grp.groupby('direction')
            buy, sell = None, None
            buy_cnt, sel_cnt, buy_amt, sel_amt = 0, 0, 0, 0
            try:
                # the only way buy doesn't exist is if its mislabeled
                # smh multi option orders. not sure fix is in parser
                buy = sub.get_group('buy')
                buy_cnt = buy['count'].sum()
                buy_amt = buy['total_amount'].sum()
            except KeyError:
                pass
            try:
                # sell might not exist if still holding
                sel = sub.get_group('sell')
                sel_cnt = sel['count'].sum()
                sel_amt = sel['total_amount'].sum()
            except KeyError:
                pass
            count = sel_cnt - buy_cnt
            amount = sel_amt - buy_amt
            # try to handle expired positions..
            # this func getting out of hand
            if count < 0 and tup[-1]:
                expir = pd.Timestamp(tup[-1])
                today = dt.datetime.today()
                if expir < today:
                    count = 0
            pos.append((*tup, *(sel_cnt, buy_cnt, count, amount)))
            if self.debug:
                print(pos[-1])
        return pd.DataFrame(pos, columns=inputs + outputs)

    def analyze(self, df):
        df = self.add_date_and_fix_expir_year(df)
        s = df.groupby('direction')['total_amount'].sum()
        dum = s['sell'] - s['buy'] - self.total_deposit
        print(f"Naive: sells - buys - total deposit = {dum}")
        print("not handling partial orders in computing positions")
        pos = self.compute_positions(df)
        print("closed positions")
        print(pos[pos['count'] == 0])
        print("negative of holdings")
        print(pos[pos['count'] < 0])
        print("wat")
        print(pos[pos['count'] > 0])
