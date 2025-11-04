"""
AIA Pay App Review — Streamlit Prototype

This prototype parses G702/G703 PDFs and validates totals.
"""

import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from decimal import Decimal, InvalidOperation
import os

st.title("AIA Pay App Reviewer")

st.write("Upload your previous and current AIA G702/G703 PDFs to validate totals and flag inconsistencies.")

# Upload previous PDF
prev_file = st.file_uploader("Previous Pay App (PDF)", type="pdf")
# Upload current PDF
curr_file = st.file_uploader("Current Pay App (PDF)", type="pdf")

import openai
import os

# Optional: Set your OpenAI API key in Streamlit secrets or environment
# os.environ["OPENAI_API_KEY"] = "your_api_key_here"

# Show prompt box only if both files are uploaded
if prev_file and curr_file:
    user_prompt = st.text_input(
        "Ask the AI to review your pay app (e.g., 'Check for errors and summarize')"
    )

    if user_prompt:
        try:
            # Convert your parsed tables to CSV strings or simple dicts
            # Here we just create a placeholder summary text
            pdf_data_summary = "Previous and current AIA PDFs uploaded. Calculated totals, percent complete, and flagged discrepancies."

            # Combine your user prompt with extracted data
            ai_input = f"{user_prompt}\n\nData summary:\n{pdf_data_summary}"

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=300
            )

            # Display AI summary
            ai_summary = response['choices'][0]['message']['content']
            st.markdown("### AI Review Summary")
            st.write(ai_summary)

        except Exception as e:
            st.error(f"Error generating AI summary: {e}")
