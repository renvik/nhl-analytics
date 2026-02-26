# NHL Data Engineering Pipeline 🏒

An end-to-end data pipeline to fetch, transform, and visualize NHL hockey data. This project follows a professional migration path from a **local Python ETL** foundation to an **Enterprise Azure Databricks** implementation using the Medallion Architecture. One goal is to find out how far you can go in developing a program with Cursor AI, both in terms of planning and actual coding.

## 🚀 Roadmap: From Local to Cloud
- **Phase 1 (Current):** Local Python ETL. Raw JSON ingestion, Pydantic validation, and local Parquet storage.
- **Phase 2:** Cloud Migration. Data landing in Azure Data Lake Storage (ADLS Gen2) via Azure Data Factory.
- **Phase 3:** Enterprise Scale. Spark-based transformations in Azure Databricks (Bronze/Silver/Gold layers).

## 📊 Business Goals & Success Metrics
The project is considered complete when the following 5 analytical goals are achieved:
1. **Goal Leaderboard:** Top 10 scorers for the 2025-26 season.
2. **League Standings:** Real-time points ranking by team.
3. **Age vs. Performance:** Scatter plot analysis of scoring drop-off by player age.
4. **Sniper Efficiency:** Visualization of shooting percentage vs. shot volume (Goals/SOG).
5. **Home Ice Advantage:** Time-series analysis of home vs. away win rates throughout the season.

## 🛠️ Tech Stack
- **Language:** Python 3.12+
- **API Client:** `httpx` (Asynchronous HTTP requests)
- **Data Validation:** `Pydantic` (Schema enforcement)
- **Transformation:** `Pandas` / `PySpark`
- **Testing:** `Pytest`
- **Cloud (Target):** Azure Databricks, ADLS Gen2, Delta Lake

## 📁 Repository Structure
```text
nhl-analytics/
├── data/               # Local data lake (Git-ignored)
├── src/                # Modular source code
│   ├── extractor.py    # API logic
│   ├── transformer.py  # Data cleaning
│   └── utils.py        # Shared helpers
├── tests/              # Unit and integration tests
├── .env                # Secrets & Config
└── README.md