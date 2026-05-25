# AI SQL Query Generator using Generative AI

An AI-powered application that converts natural language questions into SQL queries and retrieves data directly from a database.

This project uses Generative AI to help users interact with databases without writing SQL manually. Users can simply type queries in plain English, and the AI automatically converts them into SQL commands and fetches the required data.

---

## Features

- Convert natural language into SQL queries
- Execute SQL queries automatically
- Retrieve data from SQLite database
- Simple and interactive Streamlit UI
- Powered by Google Gemini API
- Beginner-friendly Generative AI project

---

## Tech Stack

- Python
- Streamlit
- SQLite
- Google Gemini API
- dotenv

---

## Project Workflow

1. User enters a question in plain English
2. Gemini AI converts the question into an SQL query
3. SQL query is executed on the database
4. Data is fetched and displayed to the user

---

## Example

### User Input
```text
Show all students studying in ML class

### SQL QUERY
SELECT * FROM STUDENT WHERE CLASS='ML';

### Output
('Esmoli', 'ML', 'A')
('Gungun', 'ML', 'A')
