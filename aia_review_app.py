"""
AIA Pay App Checker — Previous Amount Billed Match Only
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
import openai

st.title("AIA Pay App Checker — Previous Amount Billed Match")

st.write(
    "Upload the previous pay app and the current pay app (PDF or Excel). "
    "The app will check if the total billed on the previous pay app matches the 'Previous' column on the current pay app."
)

# ---------------------
# Set OpenAI API key
# ---------------------
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.warning("OpenAI API key not found! Please add OPENAI_API_KEY in Streamlit Secrets.")

# ---------------------
# Upload files
# ---------------------
prev_file = st.file_uploader("Previous Pay App (PDF or Excel)", type=["pdf", "xlsx"])
curr_file = st.file_uploader("Current Pay App (PDF or Excel)", type=["pdf", "xlsx"])

# ---------------------
# Helper functions to parse PDF and Excel
# ---------------------
def parse_pdf_total(file):
    try:
        total = 0
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                    if len(numbers) >= 3:
                        total += float(numbers[2])  # Take the Total column
        return total
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return None

def parse_excel_total(file):
    try:
        df = pd.read_excel(file)
        if "Total" not in df.columns:
            st.error("Excel file missing 'Total' column")
            return None
        return df["Total"].sum()
    except Exception as e:
        st.error(f"Error parsing Excel: {e}")
        return None

def parse_file_total(file):
    if file is None:
        return None
    if file.type == "application/pdf":
        return parse_pdf_total(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       "application/vnd.ms-excel"]:
        return parse_excel_total(file)
    else:
        st.error("Unsupported file type")
        return None

# ---------------------
# Compute totals
# ---------------------
prev_total = parse_file_total(prev_file)
curr_prev_total = None

if prev_total is not None and curr_file is not None:
    # Parse the 'Previous' column from current pay app
    try:
        if curr_file.type == "application/pdf":
            curr_total = 0
            with pdfplumber.open(curr_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    for line in text.split("\n"):
                        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                        if len(numbers) >= 1:
                            curr_total += float(numbers[0])  # Previous column
            curr_prev_total = curr_total
        elif curr_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                "application/vnd.ms-excel"]:
            df = pd.read_excel(curr_file)
            if "Previous" not in df.columns:
                st.error("Current Excel file missing 'Previous' column")
            else:
                curr_prev_total = df["Previous"].sum()
    except Exception as e:
        st.error(f"Error parsing current file: {e}")

# ---------------------
# Display results
# ---------------------
if prev_total is not None and curr_prev_total is not None:
    st.write(f"**Total from previous pay app:** {prev_total:,.2f}")
    st.write(f"**Previous column total from current pay app:** {curr_prev_total:,.2f}")

    if abs(prev_total - curr_prev_total) < 0.01:
        st.success("✅ Totals match!")
    else:
        st.error("❌ Totals do NOT match!")

        # Optional: AI explanation
        try:
            ai_input = f"""
            Check the previous pay app total vs the previous column total in the current pay app:

            Previous pay app total: {prev_total:,.2f}
            Current pay app 'Previous' total: {curr_prev_total:,.2f}

            Explain if they match and if not, provide recommendations for the reviewer.
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
