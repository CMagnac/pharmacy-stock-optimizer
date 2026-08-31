# Pharmacy Stock Optimization & Historical Monitoring System

A Python-based data and logistics project designed to analyze and optimize medication inventory in a community pharmacy.

The project focuses on two objectives :

1. **Historical stock monitoring** tracking how pharmacy inventory evolves over time ;
2. **Stock optimization** determining appropriate stock levels while considering demand, storage space, product value, and other logistical constraints.

The project will be developed progressively using real inventory data collected during monthly physical inventories from **August to December 2026**.

## Project Context

Medication inventory management in a pharmacy involves balancing several competing objectives :

* Maintaining sufficient stock to meet patient demand.
* Avoiding unnecessary overstock.
* Limiting capital immobilized in inventory.
* Making efficient use of limited storage space.
* Identifying slow-moving or non-moving products.
* Reducing the risk of products expiring before being dispensed.
* Taking into account different storage constraints.

The objective of this project is to build a data-driven tool that can help analyze these problems.

The project initially focuses on **oral generic medications**, particularly tablets and capsules, and will later incorporate **refrigerated injectable medications**.

## Current Data

The first dataset is an inventory export containing **700 records**.

The original CSV contains several columns, but the following fields are currently relevant.

| Column          | Description                                    |
| --------------- | ---------------------------------------------- |
| `Code produit`  | Product identifier                             |
| `Désignation`   | Medication/product description                 |
| `Stock avant`   | Stock recorded before inventory modification   |
| `Stock modifié` | Stock recorded after inventory                 |
| `Ecart`         | Difference between recorded and modified stock |
| `PAMP net`      | Net weighted average purchase price            |

The CSV uses:

* `;` as the separator.
* `,` as the decimal separator.
* French column names.
* Dates formatted as `DD/MM/YYYY HH:MM`.

Example:

```text
Code produit;Désignation;Stock avant;Stock modifié;Ecart;PAMP net
3400930069325;TENOFOVIR DISOP 245MG BIOG CPR 30;1;1;0,00;75,97
```

## Important Limitation

The current inventory dataset is a **stock snapshot**. It does not provide **sufficient information** to calculate medication consumption. Therefore, **consumption data will be integrated later**. This distinction is important for the statistical and logistical validity of the project.

## Historical Stock Monitoring

The first development objective is to transform the current static inventory export into a **historical stock-monitoring system**. Each monthly inventory will be stored as a separate observation rather than replacing the previous inventory.

Planned inventory observations:

```text
August 2026 (Baseline)
September 2026
October 2026
November 2026
December 2026
```

This will allow the project to move from current stock to stock evolution over time.

## Initial Metrics

The first version will focus on **descriptive inventory analysis**.

### Stock Value

Using `Stock modifié` and `PAMP net`:

```text
Stock Value = Stock modifié X PAMP net
```

This provides an **estimate of the capital** represented by the inventory.

### Inventory Difference

The project will analyze :

* positive discrepancies ;
* negative discrepancies ;
* zero discrepancies ;
* absolute discrepancies.

### Financial Impact of Discrepancies

```text
Difference Value = Ecart X PAMP net
```

This allows discrepancies to be evaluated financially rather than only by quantity.

## Planned Logistics Analyses

The project will not rely exclusively on **ABC analysis**.

### 1. Stock Coverage

Once consumption data is available, we calculate Stock Coverage = Current Stock / Average Monthly Consumption

This will identify :

* understocked products ;
* normally stocked products ;
* overstocked products.

## 2. FSN Analysis

Products will be classified according to their movement:

* **F Fast moving**
* **S Slow moving**
* **N Non-moving**

This will help identify slow and dead stock.

## 3. Space Efficiency

The physical size of medication boxes will be incorporated into the analysis. Box sizes may be represented by simple categories : Small, Medium and Large. These can potentially be replaced by actual dimensions or volumes.

## 4. Demand Variability

Once enough historical consumption data is available, demand variability may be analyzed using approaches such as XYZ analysis and other forecasting methods.

## Oral vs Refrigerated Medications

The final system will distinguish between different logistical categories.

### Generic oral medications

The analysis will focus primarily on:

* consumption ;
* stock coverage ;
* rotation ;
* stock value ;
* storage space.

### Refrigerated injectable medications

Additional constraints will be considered, such as:

* refrigerated storage ;
* limited refrigerator capacity ;
* product value ;
* demand variability ;
* cold-chain requirements.

The optimization model will therefore not necessarily apply **identical rules to every medication**.

## Planned Technologies

* **Python**
* **Pandas** for data processing
* **SQLite** for historical data
* **Streamlit** for visualization
* **Matplotlib / Plotly** for analysis and charts

Optimization methods such as **OR-Tools, SciPy, or other operations-research techniques** may be introduced later if justified by the collected data.

## Planned Project Structure

The repository will progressively evolve, but the initial structure is expected to follow this direction:

```text
pharmacy-stock-optimization/
│
├── data/
│   ├── raw/
│   │   ├── inventory_2026_08.csv
│   │   ├── inventory_2026_09.csv
│   │   ├── inventory_2026_10.csv
│   │   ├── inventory_2026_11.csv
│   │   └── inventory_2026_12.csv
│   │
│   └── processed/
│
├── src/
│   ├── data/
│   ├── inventory/
│   ├── analysis/
│   ├── forecasting/
│   ├── optimization/
│   └── dashboard/
│
├── tests/
│
├── README.md
├── pyproject.toml
└── .gitignore
```

The exact architecture will be refined as the project develops.

## Disclaimer

This project is an analytical and decision-support prototype.

It is not intended to replace professional judgment, pharmacy procedures, regulatory requirements, or the pharmacy's existing stock-management system.
