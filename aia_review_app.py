"""
AIA Pay App Reviewer — Full Version with PDF and Excel Support
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
import openai

st.title("AIA Pay App Reviewer")

st.write(
    "Upload previous and current AIA PDFs or Excel files to validate totals, flag issues, and get a detailed AI summary."
)

# ---------------------
# Set OpenAI API key from Streamlit Secrets
# ---------------------
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.warning("OpenAI API key not found! Please add OPENAI_API_KEY in Streamlit Secrets.")

# ---------------------
# Upload PDFs or Excel
# ---------------------
prev_file = st.file_uploader("Previous Pay App (PDF or Excel)", type=["pdf", "xlsx"])
curr_file = st.file_uploader("Current Pay App (PDF or Excel)", type=["pdf", "xlsx"])

# ---------------------
# Helper: parse PDF
# ---------------------
def parse_pdf_to_table(file):
    rows = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                    if len(numbers) >= 3:
                        desc = re.sub(r"\d", "", line).strip()[:50]
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

# ---------------------
# Helper: parse Excel
# ---------------------
def parse_excel_to_table(file):
    try:
        df = pd.read_excel(file)
        # Ensure required columns exist
        required_cols = ["Description", "Previous", "This Period", "Total"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Excel file missing required column: {col}")
                return None
        # Optional: % Complete
        if "% Complete" not in df.columns:
            df["% Complete"] = None
        return df[["Description", "Previous", "This Period", "Total", "% Complete"]]
    except Exception as e:
        st.error(f"Error parsing Excel: {e}")
        return None

# ---------------------
# General parse function
# ---------------------
def parse_file(file):
    if file is None:
        return None
    if file.type == "application/pdf":
        return parse_pdf_to_table(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        return parse_excel_to_table(file)
    else:
        st.error("Unsupported file type")
        return None

prev_df = parse_file(prev_file)
curr_df = parse_file(curr_file)

# Show parsed counts
if prev_df is not None:
    st.write(f"Previous file parsed {len(prev_df)} line items")
if curr_df is not None:
    st.write(f"Current file parsed {len(curr_df)} line items")

# ---------------------
# Merge and flag discrepancies
# ---------------------
def merge_and_flag(prev, curr):
    if prev is None or curr is None:
        return None
    df = pd.merge(prev, curr, on="Description", how="outer", suffixes=("_prev", "_curr"))
    df["Mismatch"] = (
        df["Previous_prev"].fillna(0) + df["This Period_curr"].fillna(0) != df["Total_curr"].fillna(0)
    )
    df["Pct_Inconsistency"] = (
        df["% Complete_prev"] != df["% Complete_curr"]
    )
    return df

merged_df = merge_and_flag(prev_df, curr_df)

if merged_df is not None:
    # Highlight flagged rows
    def highlight_flags(row):
        color = ""
        if row["Mismatch"] or row["Pct_Inconsistency"]:
            color = "background-color: #FFDDDD"
        return [color]*len(row)

    st.write("Merged table with flagged mismatches (highlighted in red):")
    st.dataframe(merged_df.style.apply(highlight_flags, axis=1))

    # CSV download
    csv = merged_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download flagged table as CSV",
        data=csv,
        file_name="merged_aia_pay_app.csv",
        mime="text/csv"
    )

# ---------------------
# AI Review Summary with Chunking
# ---------------------
if prev_file and curr_file:
    user_prompt = st.text_input(
        "Ask the AI to review your pay app (e.g., 'Check for errors and summarize')"
    )

    if user_prompt and openai.api_key and merged_df is not None:
        try:
            rows_per_chunk = 50
            chunks = [
                merged_df.iloc[i:i+rows_per_chunk].to_string(index=False)
                for i in range(0, len(merged_df), rows_per_chunk)
            ]

            ai_responses = []
            for i, chunk in enumerate(chunks):
                ai_input = f"""
                {user_prompt}

                Here is pay app data chunk {i+1} of {len(chunks)}:

                {chunk}

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
                ai_responses.append(response.choices[0].message.content)

            full_summary = "\n\n".join(ai_responses)
            st.markdown("### AI Review Summary")
            st.write(full_summary)

        except Exception as e:
            st.error(f"Error generating AI summary: {e}")

# ---------------------
# Notes
# ---------------------
st.markdown(
    """
**Notes:**
- This version supports both PDF and Excel uploads.
- All line items are chunked for AI review.
- Mismatched rows and percent complete inconsistencies are highlighted in red.
- Download the CSV for further review or import into Sage Intacct.
"""
)
