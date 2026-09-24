# Zepto Data & AI Platform (AI/ML Capstone)

One repository, three connected modules:

| Folder | Purpose |
|---|---|
| `/data_pipeline` | Scrape books.toscrape.com -> clean -> INR conversion -> normalized SQLite -> SQL + pandas |
| `/analytics` | Titanic profiling, cleaning, EDA data story, full modeling pipeline |
| `/support_assistant` | LangGraph + ChromaDB + FastAPI support assistant grounded in 8 policy documents (offline mock mode by default) |

## Setup

Python 3.10+ recommended. The root `requirements.txt` covers `/data_pipeline` and `/analytics`; `/support_assistant` has its own `requirements.txt` (heavier dependencies, also used by its Dockerfile).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## How to run

### Module 1 - `/data_pipeline`
```bash
cd data_pipeline
python pipeline.py
```
Needs internet (scrapes books.toscrape.com). Produces `books_raw.csv`, `books_clean.csv`,
`books.db` (rebuilt from scratch on every run), and `sql_results.md` (every query with its output,
plus the `pd.read_sql` vs `pd.merge` comparison).

### Module 2 - `/analytics`
```bash
cd analytics
jupyter notebook          # then open and "Run All" in order:
                          #   01_eda.ipynb       loads Titanic ONCE, saves titanic.csv, EDA + data story
                          #   02_modeling.ipynb  reads titanic.csv, full modeling pipeline
```
Run them in this order, from inside `/analytics`. `01_eda.ipynb` is the only place that calls
`sns.load_dataset('titanic')` (needs internet once); it writes `titanic.csv` immediately, and everything after
works from that CSV. Commit `titanic.csv` (and the executed notebooks, so the outputs are visible) so grading
works offline via `pd.read_csv("titanic.csv")`. Running the notebooks also writes `EDA_REPORT.md`,
`MODELING_REPORT.md`, `figures/*.png` and `best_pipeline.joblib`.

### Module 3 - `/support_assistant`
Has its own `requirements.txt` (it needs torch, chromadb and langgraph, which the other modules do not).
See [`support_assistant/README.md`](support_assistant/README.md) for run steps, Docker, example calls and the architecture description.
```bash
cd support_assistant
pip install -r requirements.txt
uvicorn main:app --port 7860      # MOCK_LLM left at its default (offline mock mode)
python demo_calls.py              # records the two example calls to example_calls.md
```

## Design decisions

### Module 1
- **Scope:** 4 categories (Travel, Mystery, Historical Fiction, Classics), all their paginated pages, well above the 60-book minimum.
- **Fixed rate:** `1 GBP = 105.50 INR`, a project-defined constant, no API call, no date reference. `price_inr = price_gbp * 105.50`, rounded to 2 decimals.
- **Types:** `price_gbp` float (currency symbol stripped), `rating` int 1-5 (One..Five mapped), `in_stock` bool (parsed from availability text: "out of stock" -> False, "in stock" -> True).
- **Messy rows:** numeric fields (`price_gbp`, `rating`) that fail to parse get **median imputation**, because dropping a whole book over one bad number wastes good data. `in_stock` has no meaningful median, so a row whose availability cannot be parsed is **dropped**. Nothing crashes on a bad row.
- **Schema:** `categories(category_id PK, category_name UNIQUE)` and `books(book_id PK, ..., category_id FK -> categories)`, with `PRAGMA foreign_keys=ON` and CHECK constraints on rating and in_stock.
- **Queries:** 6 SQL queries covering SELECT/WHERE, ORDER BY, LIMIT, DISTINCT, IN, BETWEEN and a JOIN (top 10 highest-rated books per category via `ROW_NUMBER()`). Ties are broken deterministically (rating, price, title) so the `pd.merge` reproduction matches the SQL result exactly; the script asserts equality.
- **Recreation:** the database is regenerated from scratch by `pipeline.py`.

### Module 2
- **One load:** raw data is loaded once (in `01_eda.ipynb`) and saved to `titanic.csv`; modeling reads that CSV.
- **Missing values (threshold rule):** `embarked`/`embark_town` (0.22% < 5%) -> drop rows; `age` (19.87%, 5-30%) -> impute with sex x pclass median; `deck` (77.2% > 30%) -> keep, encode "Missing" as its own category. Exact measured percentages are printed in `EDA_REPORT.md`.
- **Correlation:** exactly `survived, pclass, age, sibsp, parch, fare`; `adult_male` and `alone` excluded; top two pairs ranked by absolute off-diagonal value.
- **Modeling:** stratified 80/20 split *before* any fitting; imputer, one-hot encoder and scaler live inside a `ColumnTransformer` inside a `Pipeline`, so they are fit on train only. `alive` is excluded as target leakage. Models: Logistic Regression, Decision Tree (depth 4), Random Forest.
- **Imbalance:** baseline vs `class_weight='balanced'` vs SMOTE (via `imblearn`'s Pipeline, so SMOTE only touches training data).
- **Tuning:** `GridSearchCV` over `n_estimators`, `max_depth`, `max_features` with `RandomForestClassifier(oob_score=True)`; best params and OOB score reported.
- **Regression:** fare predicted from pclass, sex, age, sibsp, parch, embarked (`survived` excluded as an outcome); MAE, RMSE, R2, Adjusted R2, residual plot with a quantitative heteroscedasticity check.
- **Deployment artifact:** the best full pipeline is saved with `joblib.dump` and reloaded in the same script to confirm it predicts on raw input.
- **Written interpretations / module note:** generated into `01_eda.ipynb` (also saved as `analytics/EDA_REPORT.md`) (profiling, missing-value rule, outliers, skew, survival rates, correlations, 5 charts with interpretations, standardization check) and `02_modeling.ipynb` (also saved as `analytics/MODELING_REPORT.md`) (split, model table, imbalance comparison, tuning + OOB, regression + heteroscedasticity, comparison tables, recommendation, saved-artifact check) as rendered Markdown output when the notebooks run.

## Git workflow (scored once for the whole repo)
The history should show a feature branch with at least two commits merged back into `main`
(use `git merge --no-ff` so a merge commit exists). Check with `git log --graph --all --oneline`.

### Module 3
- **Mock by default:** `MOCK_LLM` unset or `1` runs the deterministic offline path; only `MOCK_LLM=0` calls a real LLM (optional Groq free tier).
- **Real retrieval always:** local `all-MiniLM-L6-v2` embeddings in ChromaDB (cosine), top-3 per query, in both modes.
- **Graph:** LangGraph `StateGraph` with `classify_intent`, `retrieve_and_answer`, `direct_answer` and a conditional edge.
- **Schema:** Pydantic `AskResponse(answer, sources, confidence)`; real-LLM path retries up to 2 times with a corrective prompt, then returns a marked error.
- **Serving:** FastAPI `POST /ask`; Dockerfile serves it on port 7860. Full details in the module README.
