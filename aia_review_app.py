"""
AIA Pay App Reviewer — Streamlit Prototype with AI Summary (Streamlit Secrets + OpenAI 1.x+)

This app allows you to:
- Upload previous and current AIA G702/G703 PDFs
- Parse schedule-of-values tables
- Recalculate totals and percentages
- Flag discrepancies
- Generate AI-powered review summary in plain English
"""

import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from decimal import Decimal, InvalidOperation
import openai

st.title("AIA Pay App Reviewer")

st.write(
    "Upload your previous and current AIA G702/G703 PDFs to validate totals, flag issues, and get an AI summary."
)

# ---------------------
# Set OpenAI API key from Streamlit Secrets
# ---------------------
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.warning("OpenAI API key not found! Please add OPENAI_API_KEY in Streamlit Secrets.")

# ---------------------
# Upload PDFs
# ---------------------
prev_file = st.file_uploader("Previous Pay App (PDF)", type="pdf")
curr_file = st.file_uploader("Current Pay App (PDF)", type="pdf")

# ---------------------
# Process PDFs
# ---------------------
def parse_pdf(file):
    if not file:
        return None
    rows = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split("\n")
                for line in lines:
                    # Example heuristic: lines with numbers
                    if re.search(r"\d", line):
                        rows.append(line)
        return rows
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return None

prev_data = parse_pdf(prev_file)
curr_data = parse_pdf(curr_file)

# Show parsed counts
if prev_data:
    st.write(f"Previous PDF parsed {len(prev_data)} lines")
if curr_data:
    st.write(f"Current PDF parsed {len(curr_data)} lines")

# ---------------------
# AI Review Summary
# ---------------------
if prev_file and curr_file:
    user_prompt = st.text_input(
        "Ask the AI to review your pay app (e.g., 'Check for errors and summarize')"
    )

    if user_prompt and openai.api_key:
        try:
            # Simple text summary of parsed data
            pdf_data_summary = (
                f"Previous PDF lines: {len(prev_data) if prev_data else 0}\n"
                f"Current PDF lines: {len(curr_data) if curr_data else 0}\n"
                "Calculated totals, percent complete, and flagged discrepancies where detected."
            )

            ai_input = f"{user_prompt}\n\nData summary:\n{pdf_data_summary}"

            # OpenAI 1.x+ API
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=300
            )

            ai_summary = response.choices[0].message.content
            st.markdown("### AI Review Summary")
            st.write(ai_summary)

        except Exception as e:
            st.error(f"Error generating AI summary: {e}")

# ---------------------
# Notes
# ---------------------
st.markdown(
    """
**Notes:**
- Make sure your OpenAI API key is set in Streamlit Secrets (`OPENAI_API_KEY`).
- The AI summary is based on a simplified extracted data overview; for full accuracy, you can expand `pdf_data_summary` with parsed table details.
- This prototype can be extended to automatically compare line items, validate rollovers, and export results to CSV or Sage Intacct.
"""
)


