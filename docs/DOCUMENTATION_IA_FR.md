# Documentation synthétique - CryptoSync (Odoo 19)

Ce document a été généré principalement par IA et vérifié.

## Objectif

Ce document donne une vue simple et exploitable de CryptoSync pour deux publics :

- le BA, qui doit comprendre les flux métier et les réglages
- le développeur, qui doit pouvoir reprendre le module rapidement

Modules couverts :

- `cryptosync` : cœur commun
- `cryptosync_bitcoin`
- `cryptosync_coingecko`
- `cryptosync_ethereum`
- `cryptosync_kraken`

---

## À quoi sert CryptoSync ?

CryptoSync permet d'intégrer des opérations crypto dans Odoo en trois étapes :

1. Importer les transactions depuis une API ou un CSV
2. Transformer ces transactions en lignes exploitables métier et comptabilité
3. Générer soit des relevés bancaires, soit des écritures comptables

En pratique :

- les blockchains comme Bitcoin et Ethereum produisent des relevés
- les exchanges comme Kraken produisent des écritures comptables
- CoinGecko sert à récupérer les taux, pas les transactions

---

## Les objets métier à connaître

### Wallet crypto

Le wallet est stocké dans `res.partner.bank`.

Il contient notamment :

- le provider crypto
- les devises gérées
- le mode de sortie : relevé ou écriture
- l'option pour désactiver l'API

### Transaction brute

Objet : `crypto.transaction`

C'est la donnée source importée. Elle contient le JSON brut et pilote le traitement.

États principaux :

- `draft` : à traiter
- `error` : en erreur
- `ready` : prête à générer des sorties comptables
- `done` : entièrement générée
- `ignored` : ignorée manuellement

### Ligne traitée

Objet : `crypto.transaction.line`

C'est l'unité réellement exploitable. Elle porte :

- la date
- la devise
- le montant
- l'adresse
- le partenaire éventuel
- le journal et le compte comptable éventuels

### Provider

Objet : `crypto.provider`

Il définit le comportement du connecteur :

- code technique
- ordre d'affichage
- type de sortie
- capacités : transactions, taux, exchange ou non

### Règle comptable

Objet : `crypto.account.rule`

Elle sert à affecter un compte comptable à une ligne crypto selon un domaine Odoo.

Ces règles ne s'appliquent que pour les providers générant directement des pièces comptables, pas des relevés.

---

## Fonctionnement global

### 1. Paramétrage

L'utilisateur :

- active les modules voulus dans les paramètres
- configure les clés API ou URLs nécessaires
- crée un wallet
- choisit le provider et les devises

Selon le provider, des journaux crypto sont créés automatiquement.

### 2. Import

Deux modes existent :

- import par API
- import par CSV

L'import crée des `crypto.transaction` en état `draft`.

### 3. Traitement

Une transaction brute est ensuite transformée en une ou plusieurs `crypto.transaction.line`.

Actions utilisateur possibles :

- Process
- Reprocess
- Ignore
- Reset

Si le traitement réussit, la transaction passe en `ready`.
Sinon, elle passe en `error` avec un message explicite.

### 4. Génération comptable

Deux sorties possibles :

#### Relevés bancaires

Utilisés pour les providers de type blockchain.

Le système peut :

- grouper par semaine, mois ou année
- découper les relevés si trop de lignes

#### Écritures comptables

Utilisées pour les providers de type exchange.

Le système :

- construit les lignes d'écriture
- trouve les comptes et journaux correspondant en appliquant les règles comptables (crypto.account.rule)
- ajoute une ligne d'écart si l'écriture n'est pas équilibrée

### 5. Rejouabilité

Si une ligne de relevé ou une ligne d'écriture est supprimée, la ligne crypto repasse en `ready`.
Le flux peut donc être rejoué.

---

## Résumé par module

### `cryptosync`

Module cœur. Il gère :

- les providers
- les transactions brutes
- les lignes traitées
- les assistants d'import et de génération
- les règles comptables
- les crons
- les menus dynamiques

### `cryptosync_bitcoin`

Rôle : synchroniser des transactions Bitcoin et produire des relevés.

Particularités :

- support des adresses simples et HD wallets
- génération d'adresses enfants
- gestion du gap limit
- génération de QR code Bitcoin pour les factures

### `cryptosync_coingecko`

Rôle : récupérer les taux de change crypto.

Particularités :

- récupération historique des taux
- assistant de recherche pour enrichir une devise Odoo (Currency Manager)

### `cryptosync_ethereum`

Rôle : synchroniser les transactions Ethereum et tokens, puis produire des relevés.

Particularités :

- support des transactions externes, internes et tokens
- gestion d'une blacklist de tokens spam
- recalcul possible des balances historiques des relevés

### `cryptosync_kraken`

Rôle : synchroniser les écritures Kraken et produire des écritures comptables.

Particularités :

- API privée signée
- pagination par curseurs internes
- logique orientée exchange

---

## Points de configuration importants

### Paramètres généraux

Dans l'application Cryptocurrencies :

- activation des modules
- configuration des clés API

### Paramètres par provider

- Bitcoin : URL API, gap limit HD wallet
- CoinGecko : clé API éventuelle
- Ethereum : clé API Etherscan et blacklist spam
- Kraken : clés API au niveau du wallet

### Devise crypto

Sur `res.currency`, on trouve selon les cas :

- provider de taux
- unité crypto
- identifiant CoinGecko
- smart contract Ethereum
- code Kraken

---

## Ce qu'un BA doit retenir

- Un wallet crypto est géré comme un compte bancaire enrichi.
- Une transaction brute n'est pas encore comptable.
- Le traitement fabrique les lignes réellement exploitables.
- Selon le provider, la sortie finale est un relevé ou une écriture.
- Le système reste rejouable si une sortie comptable est supprimée.

---

## Ce qu'un développeur doit retenir

- Le cœur est dans `cryptosync`, les providers héritent et spécialisent.
- Les deux points d'extension principaux sont :
  - `res.partner.bank`.`get_transactions_from_api()`
  - `crypto.transaction`.`_process()`
- Les menus providers sont générés dynamiquement.
- Les sorties comptables sont pilotées par le type `statement` ou `move`.
- Les règles comptables ne s'appliquent vraiment que pour les providers en mode `move`.

---

## Jobs automatiques

- `CryptoRate` : récupère les taux manquants
- `CryptoSync` : synchronise les wallets crypto actifs

---

## Droits d'accès et sécurité

- Le groupe `Cryptocurrencies` doit être donné à l'administrateur du module CryptoSync. Il n'y a pas de niveau de droit et donc pas de rôle utilisateur crypto.
- Clés d'API : tous les champs contenant une clé d'API sont en fait des Many2one vers `crypto.api.key`. Cela permet d'isoler simplement les accès. E.g. `etherscan_api_key_id`.

---

## Points de vigilance

- Plusieurs appels HTTP n'ont pas de timeout explicite.
- Certaines erreurs remontent encore sous forme de traceback brut.
- Le recalcul de balance Ethereum dépend d'Etherscan et peut nécessiter une offre PRO.
- Le CSV générique crée des transactions brutes, mais le parsing utile dépend du provider.

---

## Reprise rapide d'un nouveau provider

Pour ajouter ou reprendre un provider, il faut en général :

1. Déclarer le `crypto.provider`
2. Étendre le wallet si des paramètres spécifiques sont nécessaires
3. Implémenter l'import API ou CSV
4. Implémenter `_process()` pour créer des `crypto.transaction.line`
5. Ajouter les champs devise/configuration nécessaires
6. Vérifier la génération des relevés ou écritures

---

## Glossaire

- Wallet : compte ou adresse crypto rattaché à un provider (`res.partner.bank`)
- Transaction brute : donnée source importée (`crypto.transaction`)
- Ligne traitée : ligne exploitable pour la comptabilité (`crypto.transaction.line`)
- Statement : relevé bancaire Odoo (`account.statement`)
- Move : écriture comptable Odoo (`account.move`)
- Provider : connecteur technique vers une blockchain, un exchange ou un service de taux (`crypto.provider`)
