c = get_config()

c.Mailbox.user = ''
c.Mailbox.pwd = ''
c.Mailbox.hostname = 'imap.gmail.com'
c.Mailbox.folder = 'inbox'
c.Mailbox.broker = 'robinhood.com'
# key words to filter by in email subject
c.Mailbox.filters = ['Executed',] # 'Placed', 'Canceled']

c.Parser.debug = 1
# delete these strings from email body
c.Parser.stop_chars = ['=0D', '=']
# chop email body after each of these phrases
c.Parser.stop_phrases = [
    '[', 'If you have any',
    'Your trade confirmation',
]

c.Processor.debug = 0
