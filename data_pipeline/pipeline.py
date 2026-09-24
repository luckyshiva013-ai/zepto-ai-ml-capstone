"""Module 1 - Data pipeline: scrape -> clean -> convert -> store -> query.

Run from inside /data_pipeline:   python pipeline.py
Outputs (all written next to this file):
    books_raw.csv, books_clean.csv, books.db, sql_results.md
"""
import os
import re
import sqlite3
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://books.toscrape.com/"
GBP_TO_INR = 105.50  # fixed, project-defined baseline rate (not a market rate)
CATEGORIES = ["Travel", "Mystery", "Historical Fiction", "Classics"]
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
DB_PATH = os.path.join(HERE, "books.db")


# ----------------------------------------------------------------- scraping
def get_soup(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # site omits charset; avoids "Â£" garbage
    return BeautifulSoup(resp.text, "html.parser")


def find_category_urls(wanted):
    soup = get_soup(BASE_URL)
    links = soup.select("div.side_categories ul li ul li a")
    found = {a.get_text(strip=True): urljoin(BASE_URL, a["href"]) for a in links}
    missing = [c for c in wanted if c not in found]
    if missing:
        raise ValueError(f"Categories not found on site: {missing}")
    return {c: found[c] for c in wanted}


def scrape_category(name, start_url):
    rows, url = [], start_url
    while url:
        soup = get_soup(url)
        for pod in soup.select("article.product_pod"):
            rating_classes = pod.select_one("p.star-rating")["class"]
            rows.append(
                {
                    "title": pod.h3.a["title"],
                    "price": pod.select_one("p.price_color").get_text(strip=True),
                    "star_rating": next((c for c in rating_classes if c != "star-rating"), None),
                    "availability": pod.select_one("p.availability").get_text(strip=True),
                    "category": name,
                }
            )
        nxt = soup.select_one("li.next a")
        url = urljoin(url, nxt["href"]) if nxt else None
        time.sleep(0.3)  # be polite to the server
    return rows


def scrape_all():
    rows = []
    for name, url in find_category_urls(CATEGORIES).items():
        cat_rows = scrape_category(name, url)
        print(f"scraped {len(cat_rows):3d} books from {name}")
        rows.extend(cat_rows)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- cleaning
def parse_in_stock(text):
    """True / False / None (None = unparseable)."""
    t = str(text).strip().lower()
    if "out of stock" in t:
        return False
    if "in stock" in t:
        return True
    return None


def clean(raw):
    df = raw.copy()

    # price: strip currency symbol -> float; unparseable becomes NaN
    df["price_gbp"] = pd.to_numeric(
        df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    # rating: text -> int 1..5; unparseable becomes NaN
    df["rating"] = df["star_rating"].map(RATING_MAP)
    # availability text -> bool; unparseable becomes None
    df["in_stock"] = df["availability"].map(parse_in_stock)

    # Policy: numeric fields (price_gbp, rating) -> median imputation;
    # in_stock (boolean, no meaningful median) -> drop the row.
    for col in ["price_gbp", "rating"]:
        n_bad = int(df[col].isna().sum())
        if n_bad:
            print(f"median-imputing {n_bad} bad value(s) in {col}")
            df[col] = df[col].fillna(df[col].median())
    n_before = len(df)
    df = df.dropna(subset=["in_stock", "title", "category"]).copy()
    if len(df) != n_before:
        print(f"dropped {n_before - len(df)} row(s) with unparseable availability/title/category")

    df["rating"] = df["rating"].round().astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)
    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR).round(2)
    df = df.drop_duplicates(subset=["title", "category"]).reset_index(drop=True)
    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]]


# ----------------------------------------------------------------- database
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE categories (
    category_id   INTEGER PRIMARY KEY,
    category_name TEXT UNIQUE NOT NULL
);
CREATE TABLE books (
    book_id     INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    price_gbp   REAL,
    price_inr   REAL,
    rating      INTEGER CHECK (rating BETWEEN 1 AND 5),
    in_stock    INTEGER CHECK (in_stock IN (0, 1)),
    category_id INTEGER NOT NULL REFERENCES categories(category_id)
);
"""


def build_database(df):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # regenerate from scratch every run
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO categories(category_name) VALUES (?)",
        [(c,) for c in sorted(df["category"].unique())],
    )
    cat_ids = dict(con.execute("SELECT category_name, category_id FROM categories"))
    con.executemany(
        "INSERT INTO books(title, price_gbp, price_inr, rating, in_stock, category_id) "
        "VALUES (?,?,?,?,?,?)",
        [
            (r.title, r.price_gbp, r.price_inr, int(r.rating), int(r.in_stock), cat_ids[r.category])
            for r in df.itertuples()
        ],
    )
    con.commit()
    return con


# ----------------------------------------------------------------- queries
QUERIES = {
    "Q1 SELECT + WHERE: in-stock books priced above 40 GBP": """
SELECT title, price_gbp, rating
FROM books
WHERE in_stock = 1 AND price_gbp > 40""",
    "Q2 ORDER BY + LIMIT: 10 most expensive books (INR)": """
SELECT title, price_gbp, price_inr
FROM books
ORDER BY price_inr DESC, title
LIMIT 10""",
    "Q3 DISTINCT: distinct star ratings present": """
SELECT DISTINCT rating
FROM books
ORDER BY rating""",
    "Q4 IN: books in Travel or Mystery": """
SELECT title, category_id, price_gbp
FROM books
WHERE category_id IN (SELECT category_id FROM categories
                      WHERE category_name IN ('Travel', 'Mystery'))
ORDER BY title
LIMIT 15""",
    "Q5 BETWEEN: books priced 20-30 GBP with rating 4-5": """
SELECT title, price_gbp, rating
FROM books
WHERE price_gbp BETWEEN 20 AND 30 AND rating BETWEEN 4 AND 5
ORDER BY price_gbp, title""",
    "Q6 JOIN: 10 highest-rated books per category": """
SELECT category_name, title, rating, price_gbp
FROM (
    SELECT c.category_name, b.title, b.rating, b.price_gbp,
           ROW_NUMBER() OVER (
               PARTITION BY c.category_id
               ORDER BY b.rating DESC, b.price_gbp DESC, b.title
           ) AS rn
    FROM books b
    JOIN categories c ON c.category_id = b.category_id
)
WHERE rn <= 10
ORDER BY category_name, rn""",
}
JOIN_QUERY_KEY = "Q6 JOIN: 10 highest-rated books per category"


def run_queries(con):
    log, results = [], {}
    for name, sql in QUERIES.items():
        out = pd.read_sql(sql, con)
        results[name] = out
        log.append(f"### {name}\n\n```sql{sql}\n```\n\nRows returned: {len(out)}\n\n```\n{out.to_string(index=False)}\n```\n")
        print(f"\n=== {name} ===\n{out.to_string(index=False)}")
    return log, results


def pandas_join_equivalent(df):
    """Reproduce Q6 with pd.merge on in-memory DataFrames (no SQL)."""
    cats = pd.DataFrame({"category_name": sorted(df["category"].unique())})
    cats["category_id"] = range(1, len(cats) + 1)
    books = df.merge(cats, left_on="category", right_on="category_name")
    books = books.sort_values(
        ["category_name", "rating", "price_gbp", "title"],
        ascending=[True, False, False, True],
    )
    top = books.groupby("category_name", sort=True).head(10)
    return top[["category_name", "title", "rating", "price_gbp"]].reset_index(drop=True)


def main():
    raw = scrape_all()
    raw.to_csv(os.path.join(HERE, "books_raw.csv"), index=False)

    df = clean(raw)
    df.to_csv(os.path.join(HERE, "books_clean.csv"), index=False)
    print(f"\nclean dataset: {df.shape[0]} rows, {df['category'].nunique()} categories")
    print(df.dtypes)
    assert len(df) >= 60 and df["category"].nunique() >= 3

    con = build_database(df)
    log, results = run_queries(con)

    sql_join = results[JOIN_QUERY_KEY]
    pd_join = pandas_join_equivalent(df)
    same = sql_join.equals(pd_join)
    side = pd.concat(
        [sql_join.add_prefix("sql_"), pd_join.add_prefix("pandas_")], axis=1
    ).head(12)
    print(f"\npd.read_sql result equals pd.merge result: {same}")
    print(side.to_string(index=False))
    assert same, "SQL join and pandas merge disagree"

    log.append(
        "### pd.read_sql vs pd.merge (Q6, first 12 rows side by side)\n\n"
        f"Equivalent: **{same}** (all {len(sql_join)} rows compared)\n\n```\n{side.to_string(index=False)}\n```\n"
    )
    with open(os.path.join(HERE, "sql_results.md"), "w", encoding="utf-8") as f:
        f.write("# SQL queries and outputs\n\n" + "\n".join(log))
    con.close()


if __name__ == "__main__":
    main()
