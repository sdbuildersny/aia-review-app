"""
AIA G703 Pay App Checker — Excel Only, Batch Upload
"""

import streamlit as st
import pandas as pd
import openai
import os

st.title("AIA G703 Pay App Checker — Batch Excel")
st.write(
    "Upload one or more previous and current G703 Excel files. "
    "The app checks if the 'Total Completed to Date' from previous pay apps matches "
    "the 'Previous Amount Billed' in current pay apps."
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
prev_files = st.file_uploader(
    "Previous G703 Excel files (multiple allowed)", type=["xlsx"], accept_multiple_files=True
)
curr_files = st.file_uploader(
    "Current G703 Excel files (multiple allowed)", type=["xlsx"], accept_multiple_files=True
)

# ---------------------
# Excel parser
# ---------------------
def parse_excel(file, prev_column="Previous Amount Billed", completed_column="Total Completed to Date"):
    try:
        df = pd.read_excel(file)
        if prev_column not in df.columns or completed_column not in df.columns:
            st.error(f"Excel file {file.name} missing required columns: {prev_column} or {completed_column}")
            return None, None
        prev_total = df[prev_column].sum()
        completed_total = df[completed_column].sum()
        return prev_total, completed_total
    except Exception as e:
        st.error(f"Error parsing Excel {file.name}: {e}")
        return None, None

# ---------------------
# Process all files
# ---------------------
results = []

if prev_files and curr_files:
    # Ensure same number of previous and current files
    if len(prev_files) != len(curr_files):
        st.warning("Number of previous and current files must match for comparison.")
    else:
        for prev_file, curr_file in zip(prev_files, curr_files):
            prev_total, _ = parse_excel(prev_file)
            curr_prev_total, _ = parse_excel(curr_file)

            if prev_total is not None and curr_prev_total is not None:
                match = abs(prev_total - curr_prev_total) < 0.01
                results.append({
                    "Previous File": prev_file.name,
                    "Current File": curr_file.name,
                    "Total Completed to Date (Prev)": prev_total,
                    "Previous Amount Billed (Curr)": curr_prev_total,
                    "Match": "✅" if match else "❌"
                })

# ---------------------
# Display results
# ---------------------
if results:
    df_results = pd.DataFrame(results)
    # Format numbers
    df_results["Total Completed to Date (Prev)"] = df_results["Total Completed to Date (Prev)"].map(lambda x: f"{x:,.2f}")
    df_results["Previous Amount Billed (Curr)"] = df_results["Previous Amount Billed (Curr)"].map(lambda x: f"{x:,.2f}")
    st.dataframe(df_results)

    # Optional AI summary for mismatches
    mismatches = [r for r in results if r["Match"] == "❌"]
    if mismatches:
        try:
            ai_input = "Review the following G703 pay apps mismatches:\n"
            for m in mismatches:
                ai_input += f"{m['Previous File']} vs {m['Current File']}: Prev Total = {m['Total Completed to Date (Prev)']}, Curr Previous = {m['Previous Amount Billed (Curr)']}\n"
            ai_input += "Explain possible reasons for mismatches and recommendations."

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": ai_input}],
                max_tokens=300
            )
            st.markdown("### AI Summary for Mismatches")
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Error generating AI summary: {e}")
else:
    st.info("Upload previous and current G703 Excel files to see results.")
