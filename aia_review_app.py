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
