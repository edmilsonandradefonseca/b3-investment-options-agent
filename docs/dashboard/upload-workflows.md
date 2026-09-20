# Dashboard Upload Workflows

## Portfolio Excel

1. User selects a BTG workbook.
2. React sends it to `POST /imports/portfolio`.
3. Backend validates it with `BtgRendaVariavelLoader`.
4. Validated workbook atomically replaces the active portfolio snapshot.
5. Runtime configuration is invalidated.
6. Portfolio is subsequently retrieved through `POST /orchestrate`.

## Options Excel

1. User selects an options workbook.
2. React sends it to `POST /imports/options`.
3. Backend validates it with `OptionsTransactionLoader`.
4. Validated workbook replaces the active options snapshot.
5. Runtime configuration is invalidated.
6. Options Intelligence retrieves transactions/performance through `POST /orchestrate`.

## Brokerage notes PDF

1. User can select multiple PDF notes.
2. React uploads each selected PDF to `POST /imports/brokerage-notes`.
3. Backend validates and extracts the note with `BrokerageNoteParser`.
4. The PDF is stored under the brokerage-notes import area.
5. SHA-256 fingerprint is calculated.
6. Parsed transactions are appended idempotently to `options.sqlite3`.
7. `source_manifest.sqlite3` records source, coverage and provenance.
8. UI reports processed notes and the number of newly inserted ledger transactions.

### Important architectural rule

Processing the note into the ledger does **not** automatically merge it into the Excel options snapshot.

The ledger and Excel are separate sources until the reconciliation layer determines how they relate. This prevents accidental double counting of transactions and P&L.

## Expected response

A successful brokerage upload includes:
- `status=processed`
- `parsed_count`
- `inserted_count`
- `transaction_ids`
- note number/date when available.

## Idempotency

Re-uploading the same economic transaction must not create duplicate ledger rows. The ledger tests cover this behavior.
