"""Streamlit page for AI Receipt Categorization (#349)."""

import streamlit as st
from src.utils.receipt_categorization import render_receipt_categorization

render_receipt_categorization()
