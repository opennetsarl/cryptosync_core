# Concise Documentation - CryptoSync (Odoo 19)

This document was generated primarily using AI. Only the French version was reviewed.

## Purpose

This document provides a simple and practical overview of CryptoSync for two audiences:

- Business Analysts (BA), who need to understand the business workflows and configuration
- Developers, who need to quickly understand and maintain the module

Covered modules:

- `cryptosync`: core module
- `cryptosync_bitcoin`
- `cryptosync_coingecko`
- `cryptosync_ethereum`
- `cryptosync_kraken`

---

## What is CryptoSync?

CryptoSync integrates cryptocurrency operations into Odoo in three steps:

1. Import transactions from an API or a CSV file
2. Transform those transactions into business and accounting-ready records
3. Generate either bank statements or accounting entries

In practice:

- blockchains such as Bitcoin and Ethereum generate bank statements
- exchanges such as Kraken generate accounting entries
- CoinGecko is used to retrieve exchange rates, not transactions

---

## Core Business Objects

### Crypto Wallet

The wallet is stored in `res.partner.bank`.

It includes, among other things:

- the crypto provider
- the supported currencies
- the output mode: statement or accounting entry
- an option to disable API synchronization

### Raw Transaction

Object: `crypto.transaction`

This is the imported source data. It contains the raw JSON payload and drives the processing workflow.

Main states:

- `draft`: pending processing
- `error`: processing failed
- `ready`: ready to generate accounting outputs
- `done`: fully processed
- `ignored`: manually ignored

### Processed Line

Object: `crypto.transaction.line`

This is the actual business object used by the system. It contains:

- the date
- the currency
- the amount
- the address
- the related partner (if any)
- the accounting journal and account (if any)

### Provider

Object: `crypto.provider`

Defines the connector behavior:

- technical code
- display order
- output type
- capabilities: transactions, exchange rates, exchange provider or not

### Accounting Rule

Object: `crypto.account.rule`

Assigns an accounting account to a crypto transaction line based on an Odoo domain.

These rules are only applied to providers that generate accounting entries directly, not bank statements.

---

## Overall Workflow

### 1. Configuration

The user:

- enables the desired modules in the settings
- configures the required API keys or URLs
- creates a wallet
- selects the provider and supported currencies

Depending on the provider, crypto journals are created automatically.

### 2. Import

Two import methods are available:

- API import
- CSV import

The import creates `crypto.transaction` records in the `draft` state.

### 3. Processing

Each raw transaction is transformed into one or more `crypto.transaction.line` records.

Available user actions:

- Process
- Reprocess
- Ignore
- Reset

If processing succeeds, the transaction moves to `ready`.

Otherwise, it moves to `error` with an explicit error message.

### 4. Accounting Output Generation

Two output types are available.

#### Bank Statements

Used by blockchain providers.

The system can:

- group statements by week, month, or year
- split statements when they become too large

#### Accounting Entries

Used by exchange providers.

The system:

- builds the journal entry lines
- determines the appropriate accounts and journals by applying accounting rules (`crypto.account.rule`)
- adds a balancing line if the journal entry is not balanced

### 5. Replayability

If a bank statement line or an accounting entry line is deleted, the corresponding crypto transaction line returns to the `ready` state.

The entire workflow can therefore be replayed.

---

## Module Summary

### `cryptosync`

Core module. It manages:

- providers
- raw transactions
- processed transaction lines
- import and generation wizards
- accounting rules
- scheduled jobs
- dynamic menus

### `cryptosync_bitcoin`

Purpose: synchronize Bitcoin transactions and generate bank statements.

Key features:

- support for single addresses and HD wallets
- child address generation
- gap limit management
- Bitcoin QR code generation for invoices

### `cryptosync_coingecko`

Purpose: retrieve cryptocurrency exchange rates.

Key features:

- historical exchange rate retrieval
- lookup wizard to enrich an Odoo currency (Currency Manager)

### `cryptosync_ethereum`

Purpose: synchronize Ethereum and token transactions, then generate bank statements.

Key features:

- support for external, internal, and token transactions
- spam token blacklist
- optional recalculation of historical statement balances

### `cryptosync_kraken`

Purpose: synchronize Kraken transactions and generate accounting entries.

Key features:

- signed private API
- pagination using internal cursors
- exchange-oriented processing logic

---

## Important Configuration Points

### General Settings

In the Cryptocurrencies application:

- enable the desired modules
- configure API keys

### Provider-Specific Settings

- Bitcoin: API URL, HD wallet gap limit
- CoinGecko: optional API key
- Ethereum: Etherscan API key and spam token blacklist
- Kraken: wallet-level API keys

### Cryptocurrency Configuration

Depending on the use case, `res.currency` contains:

- exchange rate provider
- crypto unit
- CoinGecko identifier
- Ethereum smart contract
- Kraken asset code

---

## What a Business Analyst Should Remember

- A crypto wallet is managed as an enhanced bank account.
- A raw transaction is not yet accounting-ready.
- Processing creates the business-ready transaction lines.
- Depending on the provider, the final output is either a bank statement or an accounting entry.
- The workflow remains replayable if an accounting output is deleted.

---

## What a Developer Should Remember

- The core logic resides in `cryptosync`; provider modules inherit from and specialize it.
- The two primary extension points are:
  - `res.partner.bank`.`get_transactions_from_api()`
  - `crypto.transaction`.`_process()`
- Provider menus are generated dynamically.
- Accounting outputs are driven by the `statement` or `move` output type.
- Accounting rules are only applied to providers operating in `move` mode.

---

## Scheduled Jobs

- `CryptoRate`: retrieves missing exchange rates
- `CryptoSync`: synchronizes active crypto wallets

---

## Access Rights and Security

- The `Cryptocurrencies` security group must be assigned to the CryptoSync module administrator. There is no permission hierarchy or dedicated crypto user role.
- API keys: all fields storing API keys are actually Many2one relationships to `crypto.api.key`, making access isolation straightforward. For example: `etherscan_api_key_id`.

---

## Points of Attention

- Several HTTP requests do not define an explicit timeout.
- Some errors are still returned as raw Python tracebacks.
- Ethereum balance recalculation depends on Etherscan and may require a PRO subscription.
- The generic CSV importer creates raw transactions, but the actual parsing logic depends on the provider.

---

## Quickly Adding a New Provider

Adding or implementing a new provider typically involves:

1. Declaring the `crypto.provider`
2. Extending the wallet model if provider-specific settings are required
3. Implementing API and/or CSV import
4. Implementing `_process()` to generate `crypto.transaction.line` records
5. Adding the required currency and configuration fields
6. Verifying bank statement or accounting entry generation

---

## Glossary

- Wallet: crypto account or address associated with a provider (`res.partner.bank`)
- Raw Transaction: imported source data (`crypto.transaction`)
- Processed Line: accounting-ready transaction line (`crypto.transaction.line`)
- Statement: Odoo bank statement (`account.statement`)
- Move: Odoo journal entry (`account.move`)
- Provider: technical connector to a blockchain, exchange, or exchange rate service (`crypto.provider`)
