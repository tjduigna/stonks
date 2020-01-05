# stonks

Parse order execution emails from a brokerage account.

Intended to be configurable by use of `cfg.py`, `pwd.py`, command-line, etc.
Add your gmail username and app password to `pwd.py` or via command line like:
```python
python app.py --Mailbox.user='mygmailname' --Mailbox.pwd='gmailapp.password'
```

For more flexible configurations you can specify the path to the configuration
files directly by:
```python
python app.py --App.cfg_file='/path/to/file' --App.sec_file='/path/to/other'
```
`sec_file` is loaded second and overrides `cfg_file` and is meant for sensitive
data, e.g.

```python
c.Mailbox.user = ''
c.Mailbox.pwd = ''
c.Processor.total_deposit = float
```

Rather than having to provide the command line argument to the secrets file,
its path can be set with the environment variable, `STONKS_SECRETS`.
