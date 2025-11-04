"""
AIA Pay App Reviewer — Subtotal-Level Analysis with Number Formatting
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
import openai

st.title("AIA Pay App Reviewer — Subtotal Analysis")

st.write(
    "Upload previous and current AIA PDFs or Excel files to validate subtotals, flag issues, and get an AI summary."
)

# ---------------------
# Set OpenAI API key
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
def parse_pdf(file):
    rows = []
    try:
        with pdfplumber.open(file) as pdf:
            section = None
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    # Detect section header (all caps, short)
                    if line.isupper() and len(line.split()) <= 5:
                        section = line.strip()
                        continue
                    # Parse numbers
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                    if len(numbers) >= 3:
                        prev_amt = float(numbers[0])
                        this_period = float(numbers[1])
                        total = float(numbers[2])
                        pct_complete = float(numbers[3]) if len(numbers) > 3 else None
                        rows.append({
                            "Section": section or "Unspecified",
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
def parse_excel(file):
    try:
        df = pd.read_excel(file)
        required_cols = ["Section", "Previous", "This Period", "Total"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Excel file missing required column: {col}")
                return None
        if "% Complete" not in df.columns:
            df["% Complete"] = None
        return df[["Section", "Previous", "This Period", "Total", "% Complete"]]
    except Exception as e:
        st.error(f"Error parsing Excel: {e}")
        return None

# ---------------------
# General parse
# ---------------------
def parse_file(file):
    if file is None:
        return None
    if file.type == "application/pdf":
        return parse_pdf(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       "application/vnd.ms-excel"]:
        return parse_excel(file)
    else:
        st.error("Unsupported file type")
        return None

prev_df = parse_file(prev_file)
curr_df = parse_file(curr_file)

# Show parsed counts
if prev_df is not None:
    st.write(f"Previous file parsed {len(prev_df)} rows")
if curr_df is not None:
    st.write(f"Current file parsed {len(curr_df)} rows")

# ---------------------
# Compute subtotals per section
# ---------------------
def subtotal_by_section(df):
    if df is None:
        return None
    return df.groupby("Section").agg({
        "Previous": "sum",
        "This Period": "sum",
        "Total": "sum",
        "% Complete": "mean"
    }).reset_index()

prev_subtotals = subtotal_by_section(prev_df)
curr_subtotals = subtotal_by_section(curr_df)

# ---------------------
# Merge and flag subtotal mismatches
# ---------------------
def merge_subtotals(prev, curr):
    if prev is None or curr is None:
        return None
    df = pd.merge(prev, curr, on="Section", how="outer", suffixes=("_prev", "_curr"))
    df["Mismatch"] = (df["Previous_prev"].fillna(0) + df["This Period_curr"].fillna(0) != df["Total_curr"].fillna(0))
    df["Pct_Inconsistency"] = (df["% Complete_prev"] != df["% Complete_curr"])
    return df

merged_subtotals = merge_subtotals(prev_subtotals, curr_subtotals)

# ---------------------
# Format numeric columns
# ---------------------
def format_numbers(df):
    num_cols = ["Previous_prev", "This Period_curr", "Total_curr", "% Complete_prev", "% Complete_curr"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
    return df

if merged_subtotals is not None:
    merged_subtotals = format_numbers(merged_subtotals)

    # Highlight flagged sections
    def highlight_flags(row):
        color = ""
        if row["Mismatch"] or row["Pct_Inconsistency"]:
            color = "background-color: #FFDDDD"
        return [color]*len(row)

    st.write("Merged subtotals with flagged mismatches (highlighted in red):")
    st.dataframe(merged_subtotals.style.apply(highlight_flags, axis=1))

    # CSV download (numbers formatted)
    csv = merged_subtotals.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download flagged subtotals as CSV",
        data=csv,
        file_name="merged_aia_subtotals_formatted.csv",
        mime="text/csv"
    )

# ---------------------
# AI summary for subtotals
# ---------------------
if prev_file and curr_file:
    user_prompt = st.text_input(
        "Ask the AI to review subtotals (e.g., 'Check section-level totals and summarize')"
    )

    if user_prompt and openai.api_key and merged_subtotals is not None:
        try:
            table_text = merged_subtotals.to_string(index=False)
            ai_input = f"""
            {user_prompt}

            Here is the pay app subtotal data by section:

            {table_text}

            Please provide:
            - Sections with mismatches
            - Percent complete inconsistencies
            - Recommendations for reviewer
            """

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=400
            )
            ai_summary = response.choices[0].message.content
            st.markdown("### AI Review Summary (Subtotal-Level)")
            st.write(ai_summary)

        except Exception as e:
            st.error(f"Error generating AI summary: {e}")

# ---------------------
# Notes
# ---------------------
st.markdown(
    """
**Notes:**
- All numeric columns are now formatted as standard accounting numbers (e.g., 10,000.00).
- This version summarizes at the section/subtotal level.
- Mismatched subtotals and % complete inconsistencies are highlighted in red.
- CSV download contains formatted subtotal-level data.
"""
)
