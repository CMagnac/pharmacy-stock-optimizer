# Pharmacy Stock Optimization & Historical Monitoring System

A Python-based data and logistics project designed to analyze, monitor, and optimize medication inventory in a community pharmacy.

The project combines historical inventory snapshots, a full pharmacy inventory, and one year of billing transactions to investigate stock evolution, medication demand, and inventory-management strategies.

The pilot focuses on two medication categories :

- **Thermosensitive medications**, requiring temperature-controlled storage ;
- **Generic oral medications**, particularly tablets and capsules.

The initial monitoring period runs from **August to December 2026**.

## Project Objectives

The project has two main objectives.

1. **Historical stock monitoring** : track inventory levels, stock values, and inventory discrepancies over time.
2. **Stock optimization** : evaluate stock levels in relation to consumption, product value, demand variability, movement frequency, storage space, and logistical constraints.

The final objective is to develop a data-driven decision-support tool that helps identify appropriate stock-management strategies for different medication categories.

## Project Context

Medication inventory management in a community pharmacy involves balancing several competing objectives :

- Accounting for differences in product value, demand patterns, and storage requirements ;
- Avoiding unnecessary overstock and reducing capital immobilized in inventory ;
- Reducing the risk of medicines expiring before dispensing ;
- Maintaining sufficient stock to meet patient demand ;
- Identifying slow-moving and non-moving products ;
- Making efficient use of limited storage space.

The project will explore established inventory-analysis methods and compare their usefulness in a real community-pharmacy environment.

## Data Sources

The project currently uses three complementary datasets.

### 1. Monthly monitored inventory

Monthly inventory exports provide stock observations for a monitored group of medications.

The August 2026 inventory establishes the baseline. Subsequent observations are added without replacing previous snapshots.

The current pilot began with **699 monitored products**.

The historical inventory pipeline preserves products that are absent from a later snapshot as missing observations rather than automatically interpreting them as zero stock.

### 2. Full pharmacy inventory

A full inventory export provides the wider product reference and allows the monitored group to be compared with the pharmacy's complete inventory.

The cleaned September 2026 inventory contains **5,674 unique product codes**.

This dataset provides context for the monitored products but does not, by itself, describe historical consumption.

### 3. One-year billing history

The billing history records dated stock movements associated with dispensing transactions.

The cleaned dataset currently contains :

| Metric | Current result |
| ------ | -------------: |
| Original records | 170,735 |
| Cleaned records | 161,978 |
| Unique products | 6,324 |
| Total recorded boxes dispensed | 274,032 |
| Date range | 11 October 2025 – 10 October 2026 |

The cleaning process retains negative stock movements, excludes records without a product code, removes exact duplicate rows, and converts negative movements into positive dispensed quantities.

These quantities will be used to build product-level demand metrics. The billing dataset remains separate from the inventory snapshots and will be linked through product identifiers when needed.

*These figures describe the current processed dataset and may change as the data pipeline is refined.*

## Inventory Data Format

The source inventory CSV uses French column names and a semicolon separator.

Relevant fields include :

| Source column | Description |
| ------------- | ----------- |
| `Code produit` | Product identifier |
| `Désignation` | Product description |
| `Stock avant` | Stock before inventory modification |
| `Stock modifié` | Stock after inventory modification |
| `Ecart` | Difference between recorded and modified stock |
| `PAMP net` | Net weighted average purchase price |

The source files use decimal commas and dates formatted as `DD/MM/YYYY HH:MM`.

Example:

```text
Code produit;Désignation;Stock avant;Stock modifié;Ecart;PAMP net
3400930069325;TENOFOVIR DISOP 245MG BIOG CPR 30;1;1;0,00;75,97
```

The processing pipeline standardizes column names, data types, and formats for analysis while preserving the original source files.

## Historical Stock Monitoring

The first development phase transforms static inventory exports into a historical monitoring system.

Each inventory is stored as a separate observation. Previous snapshots are preserved so that changes can be analyzed over time.

Planned inventory observations:

- August 2026, baseline.
- September 2026.
- October 2026.
- November 2026.
- December 2026.

The historical dataset will support analysis of :

- Differences between observed stock and dispensing patterns.
- Products missing from a subsequent observation.
- Positive and negative inventory discrepancies.
- Changes in estimated inventory value.
- Stock evolution by product.

A missing observation will remain distinct from a confirmed zero stock level.

## Initial Inventory Metrics

### Stock value

Using the modified stock quantity and the net weighted average purchase price Estimated Stock Value = Stock modifié × PAMP net.

This estimates the acquisition value represented by the recorded inventory, subject to the accuracy and interpretation of the source data.

### Inventory discrepancies

- Absolute discrepancy quantities ;
- Positive discrepancies ;
- Negative discrepancies ;
- Zero discrepancies.

### Financial impact of discrepancies

```text
Estimated Discrepancy Value = Ecart × PAMP net
```

This provides an estimated financial measure of inventory discrepancies. The interpretation depends on the source system's accounting and stock-movement conventions.

## Planned Inventory Analyses

The project will compare three complementary classification methods.

### 1. ABC Analysis : Economic Importance

ABC analysis classifies products according to their contribution to annual consumption value.

- **A:** products contributing the largest share of consumption value.
- **B:** products of intermediate economic importance.
- **C:** products contributing the smallest share.

The analysis will use dispensed quantities and an appropriate unit acquisition cost. Classification thresholds will be documented and configurable.

### 2. XYZ Analysis : Demand Variability

XYZ analysis classifies products according to the stability and predictability of demand.

- **X:** relatively stable demand.
- **Y:** variable demand.
- **Z:** irregular or difficult-to-predict demand.

Monthly dispensing quantities will be used to estimate demand variability. The treatment of zero-demand months, intermittent demand, and incomplete calendar months will be defined explicitly.

### 3. FSN Analysis : Movement Frequency

FSN analysis classifies products according to their movement over a defined observation period.

- **F — Fast-moving:** frequent product movement.
- **S — Slow-moving:** less frequent movement.
- **N — Non-moving:** no recorded movement during the observation period.

The analysis will consider transaction frequency and, where useful, total quantity dispensed. The observation period and category thresholds will be documented.

### Comparative Analysis

ABC, XYZ, and FSN measure different dimensions of inventory management. The project will compare their results rather than assume that one method is sufficient on its own.

The final analysis will investigate combined classifications, such as ABC–XYZ–FSN, to distinguish products with different economic importance, demand patterns, and movement frequencies.

## Stock Coverage and Replenishment

Once demand metrics have been calculated and validated, the project will investigate stock coverage.

A basic estimate is Stock Coverage (months) = Current Stock / Average Monthly Demand.

This calculation is meaningful only when demand is positive and the stock observation is valid.

Later developments may incorporate :

- Minimum order quantities and packaging constraints ;
- Service-level objectives ;
- Supplier lead times ;
- Demand variability ;
- Reorder points ;
- Safety stock.

These parameters will be introduced only when the required data and assumptions are available.

## Technologies

- **Python** — core application and analysis logic.
- **Pandas** — data cleaning, transformation, and aggregation.
- **Parquet** — storage of processed analytical datasets.
- **Pytest** — automated testing.
- **Matplotlib / Plotly** — charts and visual analysis.
- **Streamlit** — potential interactive dashboard.
- **SQLite** — a possible future option for structured historical storage.

Optimization libraries such as SciPy or OR-Tools may be introduced if the project later requires formal optimization models.

## Project Structure

The repository is organized around reusable Python modules and separate processing scripts.

```text
STOCK-OPTIMIZATION/
│
├── data/
│   ├── processed/
│   └── raw/
│
├── scripts/
│   ├── analyze_inventory.py
│   ├── analyze_scope.py
│   ├── build_inventory_history.py
│   ├── check_encoding.py
│   ├── clean_billing_history.py
│   ├── clean_full_inventory.py
│   ├── extract_september_monitored.py
│   ├── inspect_billing_history.py
│   ├── process_inventory.py
│   └── visualize_inventory.py
│
├── src/
│   └── pharmacy_stock/
│       ├── analysis.py
│       ├── data_loader.py
│       ├── historical.py
│       ├── pipeline.py
│       ├── scope.py
│       ├── transformations.py
│       ├── validator.py
│       └── visualization.py
│
├── tests/
├── .gitignore
├── pyproject.toml
└── README.md
```

The architecture will be extended as new analyses and optimization components are implemented.

Raw and processed datasets are kept separate from the source code and should not be committed to the public repository when they contain sensitive pharmacy information.

## Disclaimer

This project is an analytical and decision-support prototype.

It does not replace professional judgment, established pharmacy procedures, regulatory requirements, cold-chain obligations, or the pharmacy's existing stock-management system. Recommendations will depend on data quality, explicit assumptions, and validation against operational practice.
