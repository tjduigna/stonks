# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0

from traitlets import HasTraits, Unicode, Int, Float, Bool


class Record(HasTraits):
    """A structure for the most relevant attributes
    that are present in the plain/text body portion
    of a brokerage transaction email confirmation.
    """
    subject = Unicode('', help='subject title of email')
    email_id = Int(help='id from imap client')
    order_type = Unicode('', allow_none=True, help='"market", "limit", ..')
    direction = Unicode('', help='"buy" or "sell"')
    count = Float(allow_none=True, help='number of items')
    kind = Unicode('', allow_none=True,
                   help='units of count, "shares", "contracts", ..')
    strike = Unicode('', allow_none=True, help='option strike price')
    order = Unicode('', allow_none=True, help='call or put')
    expiration = Unicode('', allow_none=True, help='expiration date')
    ticker = Unicode('', allow_none=True, help='ticker symbol')
    total_amount = Float(allow_none=True, help='total money')
    month = Int(help='month')
    day = Int(help='day')
    year = Int(help='year')
    hour = Int(help='hour')
    minute = Int(help='minute')
    meridiem = Unicode('', help='AM or PM')
    partial = Bool(allow_none=True, help='if True, only partial fill')
    partial_amount = Float(allow_none=True, help='partial amount')
    unfilled_amount = Float(allow_none=True, help='unfilled amount')
    partial_unit = Unicode('', allow_none=True, help='partial amount unit')
    partial_price = Float(allow_none=True, help='partial_price')
    avg_price = Float(allow_none=True, help='average price per unit')

