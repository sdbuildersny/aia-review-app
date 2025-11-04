"""
AIA Pay App Checker — Total Completed vs Previous Amount Billed
"""

import streamlit as st
import pdfplumber
import pandas as pd
import openai

st.title("AIA Pay App Checker — G703 Totals Match")

st.write(
    "Upload previous and current AIA G703 PDFs or Excel files. "
    "The app checks if the total completed to date from the previous pay app matches "
    "the previous amount billed in the current pay app."
)

# ---------------------
# OpenAI API key
# ---------------------
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.warning("OpenAI API key not found! Please add OPENAI_API_KEY in Streamlit Secrets.")

# ---------------------
# File uploads
# ---------------------
prev_file = st.file_uploader("Previous G703 Pay App (PDF or Excel)", type=["pdf", "xlsx"])
curr_file = st.file_uploader("Current G703 Pay App (PDF or Excel)", type=["pdf", "xlsx"])

# ---------------------
# PDF parsing helpers
# ---------------------
def parse_pdf_column_sum(file, column_index):
    """Sum values from a specific column index across all lines in all pages."""
    total = 0
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table[1:]:  # skip header
                        if row[column_index]:
                            try:
                                total += float(row[column_index].replace(",", "").replace("$", ""))
                            except:
                                pass
        return total
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return None

# ---------------------
# Excel parsing helpers
# ---------------------
def parse_excel_column_sum(file, column_name):
    try:
        df = pd.read_excel(file)
        if column_name not in df.columns:
            st.error(f"Excel missing required column: {column_name}")
            return None
        return df[column_name].sum()
    except Exception as e:
        st.error(f"Error parsing Excel: {e}")
        return None

# ---------------------
# Determine totals
# ---------------------
prev_total = None
curr_prev_total = None

# Previous pay app → Total Completed to Date
if prev_file:
    if prev_file.type == "application/pdf":
        # G703 typically has "Total Completed to Date" in 3rd column (index 2)
        prev_total = parse_pdf_column_sum(prev_file, column_index=2)
    else:
        prev_total = parse_excel_column_sum(prev_file, column_name="Total Completed to Date")

# Current pay app → Previous Amount Billed
if curr_file:
    if curr_file.type == "application/pdf":
        # G703 typically has "Previous Amount Billed" in 1st column (index 0)
        curr_prev_total = parse_pdf_column_sum(curr_file, column_index=0)
    else:
        curr_prev_total = parse_excel_column_sum(curr_file, column_name="Previous Amount Billed")

# ---------------------
# Display results
# ---------------------
if prev_total is not None and curr_prev_total is not None:
    st.write(f"**Total Completed to Date (Previous G703):** {prev_total:,.2f}")
    st.write(f"**Previous Amount Billed (Current G703):** {curr_prev_total:,.2f}")

    if abs(prev_total - curr_prev_total) < 0.01:
        st.success("✅ Totals match!")
    else:
        st.error("❌ Totals do NOT match!")

        # Optional AI explanation
        try:
            ai_input = f"""
            Check if the total completed to date from the previous pay app matches
            the previous amount billed in the current pay app.

            Total Completed to Date (Previous G703): {prev_total:,.2f}
            Previous Amount Billed (Current G703): {curr_prev_total:,.2f}

            Explain if they match, and if not, provide recommendations for the reviewer.
            """
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=200
            )
            st.markdown("### AI Summary")
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Error generating AI summary: {e}")
