# csvpeek

Instant CSV inspection in the terminal. Point it at a file and get the
shape, the inferred type of every column, null counts, real stats, the top
values, and the first few rows, without opening a spreadsheet or writing a
pandas one-liner.

Zero dependencies. Pure standard library. Python 3.8+.

```
$ csvpeek sales.csv
12488 rows x 6 columns

order_id  int     0 null... 
```

## Install

```
pip install git+https://github.com/TheRealAlexxx/csvpeek.git
```

or run it straight from a clone, nothing to build:

```
python -m csvpeek yourfile.csv
```

## Use it

```
csvpeek data.csv              # the full report
csvpeek data.csv --rows 10    # show ten sample rows instead of five
csvpeek data.csv --rows 0     # stats only, no sample
cat data.csv | csvpeek -      # read from stdin
csvpeek data.csv --delimiter ';'     # force a delimiter (sniffing is good, not perfect)
csvpeek data.csv --encoding latin-1  # older files
```

## What you get

For every column: the inferred type (int, float, bool, date, string), how
many nulls (it knows NA, n/a, null, -, --, ?, and friends), how many
unique values, and type-appropriate stats: min/max/mean for numbers,
earliest/latest for dates, true/false counts for booleans, and the most
common values for text.

Delimiter sniffing handles comma, semicolon, tab and pipe files, including
the European kind with semicolons and comma decimals. Ragged rows are
padded, BOMs are eaten, quoted commas are parsed correctly.

## Why not pandas

pandas is right when you are going to transform the data. csvpeek is for
the thirty seconds before that, when you just want to know what you are
looking at.

## License

MIT. Do whatever you like.
