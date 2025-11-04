"""
AIA G703 Pay App Checker — Total Completed vs Previous Amount Billed
"""

import streamlit as st
import pandas as pd
import re
import openai

st.title("AIA G703 Pay App Checker")
st.write(
    "Upload previous and current G703 PDFs or Excel files. "
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
# PDF parser using header positions
# ---------------------
def parse_g703_pdf(file):
    """
    Extracts and sums:
    - Previous Amount Billed
    - Total Completed to Date
    from a G703 PDF using header positions.
    Returns a tuple: (previous_total, completed_total)
    """
    try:
        import pdfplumber
        prev_total = 0
        completed_total = 0
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split("\n")
                header_idx = None
                col_positions = {}
                
                # Detect header line containing keywords
                for i, line in enumerate(lines):
                    if "Previous" in line and "Completed" in line:
                        header_idx = i
                        # Get approximate start positions of each column
                        for col_name in ["Previous", "Completed"]:
                            pos = line.find(col_name)
                            if pos >= 0:
                                col_positions[col_name] = pos
                        break
                
                if header_idx is None:
                    continue
                
                # Process lines below header
                for line in lines[header_idx + 1:]:
                    if not line.strip():
                        continue
                    # Previous Amount Billed
                    if "Previous" in col_positions:
                        start = col_positions["Previous"]
                        end = col_positions.get("Completed", None)
                        prev_text = line[start:end].strip() if end else line[start:].strip()
                        prev_text = prev_text.replace(",", "").replace("$", "")
                        try:
                            prev_total += float(prev_text)
                        except:
                            continue
                    # Total Completed to Date
                    if "Completed" in col_positions:
                        start = col_positions["Completed"]
                        completed_text = line[start:].strip().replace(",", "").replace("$", "")
                        try:
                            completed_total += float(completed_text)
                        except:
                            continue
        return prev_total, completed_total
    except Exception as e:
        st.error(f"Error parsing G703 PDF: {e}")
        return None, None

# ---------------------
# Excel parser
# ---------------------
def parse_excel(file, prev_column="Previous Amount Billed", completed_column="Total Completed to Date"):
    try:
        df = pd.read_excel(file)
        if prev_column not in df.columns or completed_column not in df.columns:
            st.error(f"Excel file missing required columns: {prev_column} or {completed_column}")
            return None, None
        prev_total = df[prev_column].sum()
        completed_total = df[completed_column].sum()
        return prev_total, completed_total
    except Exception as e:
        st.error(f"Error parsing Excel: {e}")
        return None, None

# ---------------------
# Compute totals
# ---------------------
prev_total = None
curr_prev_total = None

if prev_file:
    if prev_file.type == "application/pdf":
        _, prev_total = parse_g703_pdf(prev_file)
    else:
        _, prev_total = parse_excel(prev_file)

if curr_file:
    if curr_file.type == "application/pdf":
        curr_prev_total, _ = parse_g703_pdf(curr_file)
    else:
        curr_prev_total, _ = parse_excel(curr_file)

# ---------------------
# Display results
# ---------------------
if prev_total is not None and curr_prev_total is not None:
    st.write(f"**Total Completed to Date (Previous G703):** {prev_total:,.2f}")
    st.write(f"**Previous Amount Billed (Current G703):** {curr_prev_total:,.2f}")

    if abs(prev_total - curr_prev_total) < 0.01:
        st.success("✅ Totals match!")
    else:
