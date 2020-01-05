# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0

import pandas as pd
from traitlets.config.configurable import Configurable
from traitlets import Int, Float, TraitType



class Processor(Configurable):
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

    def compute_positions(self, df):
        grps = df.groupby(('ticker', 'strike', 'order', 'expiration'))
        print(grps.size())

    def analyze(self, df):
        s = df.groupby('direction')['total_amount'].sum()
        print("sells - buys - total deposit", s['sell'] - s['buy'] - self.total_deposit)
        self.compute_positions(df)
