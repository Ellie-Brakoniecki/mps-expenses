# MP Expenses Audit Analytics

## Project Summary

This project analyses IPSA MP expenses data to support audit prioritisation.

The pipeline collects yearly source files from scraping the IPSA website, combines them, cleans and validates the data, applies explainable risk indicators, and produces outputs for a Dash dashboard.

This is a decision-support tool. It highlights notable patterns that may be worthy of further review. It does not make allegations or replace auditor judgement.

## Project Structure

```text
mps-expenses-project/
|-- data/
|   |-- raw/          # downloaded yearly IPSA CSVs
|   |-- interim/      # combined raw and cleaned datasets
|   `-- processed/    # analytics and dashboard datasets
|-- dashboard/        # Dash app
|-- outputs/          # validation, analytics, dashboard, presentation outputs
|-- src/              # project package code
|-- tests/
|-- requirements.txt
|-- run.py            # pipeline entry point
`-- README.md
```

## Main Outputs

- `data/interim/ingested_total_spend.csv`: combined raw dataset
- `data/interim/cleaned_total_spend.csv`: cleaned and standardised dataset
- `data/processed/mp_expenses_audit_dataset.csv`: full analytics dataset
- `data/processed/dashboard_dataset.csv`: dashboard-ready dataset
- `outputs/validation/validation_report.csv`: QA checks
- `outputs/validation/limitations_summary.csv`: assumptions and limitations

## Setup And Run

These steps assume you are starting in the project root.

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

### 2. Activate the virtual environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run the activation command again.

### 3. Install dependencies

Simplest option:

```powershell
pip install -r requirements.txt

Alternative (installs the project as a package and enables CLI command):
```powershell
pip install -e .
```

This installs the package and creates the `mp-expenses-audit` command.

### 4. Run the pipeline

```powershell
mp-expenses-audit
```

Alternative:

```powershell
python run.py
```

The pipeline will:

- download the IPSA annual source files
- combine the yearly data
- clean and validate the dataset
- create analytics outputs and risk flags
- write the dashboard input files

Main files created or refreshed:

- `data/processed/mp_expenses_audit_dataset.csv`
- `data/processed/dashboard_dataset.csv`
- `outputs/validation/validation_report.csv`
- `outputs/validation/limitations_summary.csv`

### 5. Run the dashboard

The dashboard will run immediately using the included processed data.

From the project root:

```powershell
python dashboard/app.py
```

Then open the local address shown in the terminal, usually:

```text
http://127.0.0.1:8050/
```

## Quick Start

If your environment is already set up, the usual run flow is:

```powershell
.\.venv\Scripts\Activate.ps1
mp-expenses-audit
python dashboard/app.py
```

## Methodology

### Peer Groups

MPs are compared within simple peer groups rather than as one full population.

The current peer groups are based on:

- whether the MP is treated as new or returning
- whether they have an accommodation budget
- whether they fall into a London or non-London grouping

This helps to make comparisons fairer and more useful for audit review.

### Feature Engineering

After cleaning, the pipeline creates a set of analysis fields from the base spend and budget data.

These include:

- total spend
- total budget
- remaining budget
- uncapped spend total
- utilisation percentages by category
- overall utilisation percentage
- peer-group percentiles
- peer-group z-scores

These fields are used to highlight notable patterns in a way that can still be explained clearly.

### Risk Flags

Risk flags are rule-based and use a mix of thresholds and peer-group comparisons.

The current flags cover:

- high overall utilisation
- low staffing utilisation
- high travel spend relative to peers
- high uncapped spend relative to peers
- accommodation spend outliers
- high total spend relative to peers

The number of triggered flags is then converted into a simple review priority:

- Low: 0 or 1 flags
- Medium: 2 flags
- High: 3 or more flags

This approach is intended to support audit prioritisation with explainable indicators rather than complex modelling.

## Limitations And Assumptions

The analysis is designed to help auditors decide where to look first. It can highlight unusual patterns, but it cannot explain individual claims or show wrongdoing on its own.

Key points to keep in mind:

- The IPSA source files are annual summaries, not full transaction-level records.
- Some context is missing, including local circumstances, office setup, and workload differences.
- File structures vary by year, so the data is standardised before comparison.
- Currency fields are cleaned into numeric values, with blanks and `N/A` treated as missing.
- Missing remaining budget values may be calculated as `budget - spend` where both inputs exist.
- `financial_year` is added during cleaning so records can be compared across years.
- Peer groups are simplified to make comparisons more practical, not perfect.

## Notes

- Raw yearly files are kept in `data/raw/annual_publications/` for traceability.
- `financial_year` is added during cleaning, not in the combined raw file.
- The dashboard reads from the processed outputs, not from raw data.


## Future Improvements

- Expanded QA reporting and automated alerts  
- Additional dashboard views and drill-down analysis  
- Improved documentation, including docstrings and README expansion  
- Linting and pre-commit hooks for code quality  
- Extended test coverage across key pipeline stages  
- Parameterised thresholds for easier tuning and audit input  
- Scheduled pipeline runs for continuous monitoring  
- Potential extensions: automated summaries (e.g. LLM-assisted explanations)

