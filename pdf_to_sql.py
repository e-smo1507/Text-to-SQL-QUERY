"""
pdf_to_sql.py

Turns a PDF containing tabular data into a queryable SQLite table.

Flow:
  1. extract_tables_from_pdf()  -> list of pandas DataFrames (one per detected table)
  2. dataframe_to_sqlite()      -> writes a chosen DataFrame into a SQLite table
  3. get_schema_description()   -> plain-English column/type summary to feed the LLM prompt
"""

import re
import sqlite3
import pandas as pd
import pdfplumber


def _clean_column_name(name: str, fallback_index: int) -> str:
    """Make a PDF header cell safe to use as a SQL column name."""
    if name is None:
        name = f"column_{fallback_index}"
    name = str(name).strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^0-9a-zA-Z_]", "", name)
    if not name:
        name = f"column_{fallback_index}"
    if name[0].isdigit():
        name = f"col_{name}"
    return name.upper()


def extract_tables_from_pdf(pdf_path: str) -> list[pd.DataFrame]:
    """
    Extract every table pdfplumber can find across all pages.
    Returns a list of DataFrames. First row of each detected table is
    treated as the header row.
    """
    dataframes = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for raw_table in tables:
                if not raw_table or len(raw_table) < 2:
                    continue  # need at least a header + one data row
                header, *rows = raw_table
                columns = [
                    _clean_column_name(col, i) for i, col in enumerate(header)
                ]
                df = pd.DataFrame(rows, columns=columns)
                # Drop fully-empty rows/columns that sometimes appear from ruled lines
                df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
                if not df.empty:
                    dataframes.append(df)
    return dataframes


def infer_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    """Try to cast columns to numeric where possible; leave the rest as text."""
    df = df.copy()
    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        # Only cast if we didn't lose real data (i.e. not everything became NaN)
        if coerced.notna().sum() >= df[col].notna().sum() * 0.8 and coerced.notna().any():
            df[col] = coerced
    return df


def dataframe_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str = "UPLOADED_DATA") -> None:
    """Overwrite (or create) `table_name` in the SQLite file at db_path with df's contents."""
    df = infer_and_cast(df)
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()


def get_schema_description(db_path: str, table_name: str = "UPLOADED_DATA") -> str:
    """
    Build a short schema description (columns + a couple of sample rows)
    that gets dropped into the LLM prompt so it knows what it's querying.
    """
    conn = sqlite3.connect(db_path)
    try:
        cols_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [c[1] for c in cols_info]
        sample_rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
    finally:
        conn.close()

    col_list = ", ".join(columns)
    sample_str = "\n".join(str(row) for row in sample_rows)
    return (
        f"Table name: {table_name}\n"
        f"Columns: {col_list}\n"
        f"Sample rows:\n{sample_str}"
    )