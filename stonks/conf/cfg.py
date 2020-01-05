c = get_config()

c.App.mode = 'email'

c.Mailbox.user = ''
c.Mailbox.pwd = ''
c.Mailbox.hostname = 'imap.gmail.com'
c.Mailbox.folder = 'inbox'
c.Mailbox.broker = 'robinhood.com'
# key words to filter by in email subject
c.Mailbox.filters = ['Executed',] # 'Placed', 'Canceled']

c.EmailParser.debug = 1
# delete these strings from email body
c.EmailParser.stop_chars = ['=0D', '=']
# chop email body after each of these phrases
c.EmailParser.stop_phrases = [
    '[', 'If you have any',
    'Your trade confirmation',
]

c.StatementParser.debug = 1
c.StatementParser.tokens = [
    'PORTFOLIO SUMMARY',
    'ACCOUNT ACTIVITY',
]
c.StatementParser.statements = [
    '2019_09.txt',
    '2019_10.txt',
    '2019_11.txt',
    '2019_12.txt',
]

c.Processor.debug = 1

