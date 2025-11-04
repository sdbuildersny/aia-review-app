"""
AIA Pay App Reviewer — Enhanced with Line Item Analysis and AI Summary
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
import openai

st.title("AIA Pay App Reviewer")

st.write(
    "Upload previous and current AIA G702/G703 PDFs to validate totals, flag issues, and get a detailed AI summary."
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
# Helper: parse PDF lines into structured table
# ---------------------
def parse_pdf_to_table(file):
    if not file:
        return None
    rows = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    # Attempt to parse lines with 4-5 numeric fields
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                    if len(numbers) >= 3:
                        # Very basic parsing: Description + numbers
                        desc = re.sub(r"\d", "", line).strip()[:50]  # take first 50 chars
                        prev_amt = float(numbers[0])
                        this_period = float(numbers[1])
                        total = float(numbers[2])
                        pct_complete = float(numbers[3]) if len(numbers) > 3 else None
                        rows.append({
                            "Description": desc,
                            "Previous": prev_amt,
                            "This Period": this_period,
                            "Total": total,
                            "% Complete": pct_complete
                        })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return None

prev_df = parse_pdf_to_table(prev_file)
curr_df = parse_pdf_to_table(curr_file)

# Show parsed counts
if prev_df is not None:
    st.write(f"Previous PDF parsed {len(prev_df)} line items")
if curr_df is not None:
    st.write(f"Current PDF parsed {len(curr_df)} line items")

# ---------------------
# Merge and flag discrepancies
# ---------------------
def merge_and_flag(prev, curr):
    if prev is None or curr is None:
        return None
    df = pd.merge(prev, curr, on="Description", how="outer", suffixes=("_prev", "_curr"))
    # Flag mismatches
    df["Mismatch"] = (
        df["Previous_prev"].fillna(0) + df["This Period_curr"].fillna(0) != df["Total_curr"].fillna(0)
    )
    df["Pct_Inconsistency"] = (
        df["% Complete_prev"] != df["% Complete_curr"]
    )
    return df

merged_df = merge_and_flag(prev_df, curr_df)

if merged_df is not None:
    st.write("Merged table with flagged mismatches:")
    st.dataframe(merged_df.head(10))  # show first 10 rows

# ---------------------
# AI Review Summary
# ---------------------
if prev_file and curr_file:
    user_prompt = st.text_input(
        "Ask the AI to review your pay app (e.g., 'Check for errors and summarize')"
    )

    if user_prompt and openai.api_key and merged_df is not None:
        try:
            # Convert first 20 rows to text to send to AI
            table_text = merged_df.head(20).to_string(index=False)

            ai_input = f"""
            {user_prompt}

            Here is a sample of the pay app data (first 20 rows):

            {table_text}

            Please provide:
            - Lines with mismatches
            - Percent complete inconsistencies
            - Recommendations for reviewer
            """

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=400
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
- This version sends actual line items to the AI for review.
- Currently only the first 20 rows are sent for performance; you can increase if needed.
- The AI will flag mismatches and percent complete inconsistencies, making it actionable.
"""
)
