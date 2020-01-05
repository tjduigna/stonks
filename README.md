# stonks

Parse order execution emails from a brokerage account. Get hacking with:
```bash
conda create -n myenv
conda activate myenv
conda install -c conda-forge `cat requirements.txt`
pip install -e .
```

Intended to be configurable by use of `cfg.py`, `pwd.py`, command-line, etc.
Add your gmail username and app password to `pwd.py` or via command line like:
```bash
python app.py --Mailbox.user='mygmailname' --Mailbox.pwd='gmailapp.password'
```

For more flexible configurations you can specify the path to the configuration
files directly by:
```bash
python app.py --App.cfg_file='/path/to/file' --App.sec_file='/path/to/secrets'
```
`sec_file` is loaded second and overrides `cfg_file` and is meant for sensitive
data, e.g.

```python
c.Mailbox.user = ''
c.Mailbox.pwd = ''
c.Processor.total_deposit = float
```

Rather than having to provide the command line argument to the secrets file,
its path can be set with the environment variable:
```bash
export STONKS_SECRETS=/path/to/secrets
python stonks/app.py
```

Emails can't guarantee an accurate ledger. Download your robinhood statements
and convert them to text using pdfminer:
```bash
pip install pdfminer
pdf2txt.py monthly_statement.pdf > text_dump.txt
python statement_parser.py text_dump.txt > transactions.csv
```

Then add csv loading to Processor..
