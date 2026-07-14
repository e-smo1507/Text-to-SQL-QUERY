
from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import tempfile
import time

import streamlit as st
from google import genai
from google.genai import errors as genai_errors

from pdf_to_sql import extract_tables_from_pdf, dataframe_to_sqlite, get_schema_description

client = genai.Client(api_key=os.getenv("google_api_key"))

UPLOADED_DB_PATH = "uploaded_data.db"
UPLOADED_TABLE_NAME = "UPLOADED_DATA"

STUDENT_PROMPT = """
You are an expert in converting English questions to SQL query!
The SQL database has the name STUDENT and has the following columns - NAME, CLASS, SECTION.

Example 1 - How many entries of records are present?
SELECT COUNT(*) FROM STUDENT;

Example 2 - Tell me all the students studying in Data Science class?
SELECT * FROM STUDENT where CLASS = "Data Science";

The sql code should not have ``` in the beginning or end, and should not contain the word 'sql'.
"""


def build_prompt_for_uploaded_data(schema_description: str) -> str:
    """Dynamically build the SQL-generation prompt from whatever table the user uploaded."""
    return f"""
You are an expert in converting English questions to SQL query!
The SQL database has a table described below:

{schema_description}

Write a single SQL query that answers the user's question against this table.
Only use the columns listed above - do not invent column names.
The sql code should not have ``` in the beginning or end, and should not contain the word 'sql'.
"""


def get_gemini_response(question: str, prompt: str, max_retries: int = 3) -> str:
    """Call Gemini, retrying with backoff if the API is temporarily overloaded (503)."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[prompt, question],
            )
            return response.text.strip()
        except genai_errors.ServerError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise last_error


def read_sql_query(sql: str, db: str):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.commit()
    finally:
        conn.close()
    return columns, rows


st.set_page_config(page_title="I can Retrieve Any SQL query")
st.header("Gemini App To Retrieve SQL Data")

st.subheader("1. Choose your data source")
data_source = st.radio(
    "Where should questions be answered from?",
    ["Built-in Student DB", "Upload a PDF"],
    horizontal=True,
)

active_db_path = "student.db"
active_prompt = STUDENT_PROMPT

if data_source == "Upload a PDF":
    uploaded_file = st.file_uploader("Upload a PDF containing a table", type=["pdf"])

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_pdf_path = tmp.name

        tables = extract_tables_from_pdf(tmp_pdf_path)

        if not tables:
            st.error(
                "No table could be detected in this PDF. Make sure the data is laid "
                "out as an actual table (ruled lines or clearly aligned columns), "
                "not as free-flowing text."
            )
        else:
            if len(tables) > 1:
                table_index = st.selectbox(
                    f"Found {len(tables)} tables in this PDF. Which one should I use?",
                    options=list(range(len(tables))),
                    format_func=lambda i: f"Table {i + 1} ({tables[i].shape[0]} rows x {tables[i].shape[1]} cols)",
                )
            else:
                table_index = 0

            chosen_df = tables[table_index]
            st.write("Preview of the detected table:")
            st.dataframe(chosen_df.head(10))

            dataframe_to_sqlite(chosen_df, UPLOADED_DB_PATH, UPLOADED_TABLE_NAME)
            schema_description = get_schema_description(UPLOADED_DB_PATH, UPLOADED_TABLE_NAME)

            active_db_path = UPLOADED_DB_PATH
            active_prompt = build_prompt_for_uploaded_data(schema_description)

            st.success("Table loaded. You can now ask questions about it below.")
    else:
        st.info("Upload a PDF to enable question answering over it.")

st.subheader("2. Ask a question")
question = st.text_input("Input:", key="input")
submit = st.button("Ask the question")

if submit:
    if data_source == "Upload a PDF" and active_db_path == "student.db":
        st.warning("Please upload a PDF first.")
    else:
        try:
            sql_query = get_gemini_response(question, active_prompt)
        except genai_errors.ServerError:
            st.error(
                "Gemini is temporarily overloaded (503) and didn't respond after "
                "several retries. Please wait a moment and try again."
            )
            st.stop()

        st.caption(f"Generated SQL: `{sql_query}`")
        try:
            columns, rows = read_sql_query(sql_query, active_db_path)
            st.subheader("The Response is")
            if columns:
                st.dataframe([dict(zip(columns, row)) for row in rows])
            else:
                st.write(rows)
        except sqlite3.Error as e:
            st.error(f"That query couldn't be run against the database: {e}")
