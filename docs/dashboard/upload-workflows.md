# Dashboard Upload Workflows

## Portfolio Excel

1. User selects a BTG workbook.
2. React sends it to `POST /imports/portfolio`.
3. The backend validates it with `BtgRendaVariavelLoader`.
4. The validated workbook atomically replaces the active portfolio snapshot.
5. Runtime configuration is invalidated.
6. Portfolio is subsequently retrieved through `POST /orchestrate`.

The UI exposes the resulting snapshot quality and `as_of`.

## Options Excel

1. User selects an options workbook.
2. React sends it to `POST /imports/options`.
3. The backend validates it with `OptionsTransactionLoader`.
4. The validated workbook replaces the active options snapshot.
5. Runtime configuration is invalidated.
6. Options Intelligence retrieves transactions/performance through `POST /orchestrate`.

## Brokerage notes

1. User can select multiple PDF notes in the React Dashboard.
2. React uploads each selected PDF to `POST /imports/brokerage-notes`.
3. The backend stores each PDF under the brokerage-notes import area.
4. The current response is `STAGED`; this means stored for processing.
5. Parsing into the options ledger is not implied by upload.

This distinction is intentional and must remain visible in the Dashboard until the processing contract is implemented.
