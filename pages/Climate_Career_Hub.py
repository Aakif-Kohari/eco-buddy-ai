"""Streamlit page for Climate Career Hub."""

import streamlit as st
from src.environment.climate_careers import render_climate_careers

render_climate_careers()
