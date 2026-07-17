"""Clean the BioPharmCatalyst scrape: strip whitespace, drop scraper-garbage
rows (SVG markup leaked into the status column) and exact duplicate rows.

Source: github.com/Tejas1415/Web-Scrape-Stock-Ticker-and-Company-Name-Datasets
        (BioPharmCatalyst.csv) -- pulled 2026-07-15, covers 2009-07-05 to
        2020-01-16 only (NOT the trailing 10 years -- flag this to anyone
        using the output).
"""
import pandas as pd

RAW = "data/raw/biopharmcatalyst/BioPharmCatalyst.csv"
OUT = "data/interim/25_biopharmcatalyst_clean.csv"

df = pd.read_csv(RAW)
df["Approved or CRL"] = df["Approved or CRL"].str.strip()
df["Ticker"] = df["Ticker"].str.strip()
df["Drug Name"] = df["Drug Name"].str.strip()

n0 = len(df)
garbage_mask = df["Approved or CRL"].str.contains("svg", case=False, na=False)
n_garbage = int(garbage_mask.sum())
df = df[~garbage_mask].copy()

df["Catalyst Date"] = pd.to_datetime(df["Catalyst Date"], format="%m/%d/%Y")

n1 = len(df)
df = df.drop_duplicates(subset=["Ticker", "Drug Name", "Catalyst Date", "Approved or CRL"])
n_dupes = n1 - len(df)

df = df.sort_values(["Ticker", "Drug Name", "Catalyst Date"]).reset_index(drop=True)
df.to_csv(OUT, index=False)

print(f"raw rows: {n0}")
print(f"dropped as scraper-garbage status: {n_garbage}")
print(f"dropped as exact duplicates: {n_dupes}")
print(f"clean rows: {len(df)}")
print(f"date range: {df['Catalyst Date'].min().date()} to {df['Catalyst Date'].max().date()}")
print(f"status value counts:\n{df['Approved or CRL'].value_counts()}")
