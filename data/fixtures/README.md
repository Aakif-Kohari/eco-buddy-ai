# Fixtures Directory

## Overview
This directory is dedicated to storing static data payloads, mock data, sample files, and other artifacts required for testing, demonstration, or application seed data.

## Purpose
In order to keep the project root clean and maintain a clear separation of concerns, all non-code static assets that are strictly data-oriented should be placed here. This prevents the repository root from becoming cluttered with JSON payloads, sample PDFs, and other test fixtures.

## Current Contents
- **Sample PDFs**: Sample reports (`eco_report.pdf`, `sample_utility_bill.pdf`) used for demonstrating generation capabilities or testing OCR/parsing.
- **JSON Payloads**: Various `*_pr.json` and `*_issue.json` payloads used for mocking API responses or testing data ingestion pipelines.

## Guidelines for Adding New Fixtures
1. **No Sensitive Data**: Never commit real user data, API keys, or sensitive credentials in these mock files.
2. **Descriptive Naming**: Ensure files are named clearly to indicate what feature or test suite they belong to.
3. **Format**: Please pretty-print JSON files before committing them so that git diffs are readable.
4. **Scope**: Keep fixtures reasonably sized. Do not commit massive multi-megabyte mock datasets.

*Note: This directory was established as part of the Phase 1 Root Directory Cleanup (Issue #1205).*
