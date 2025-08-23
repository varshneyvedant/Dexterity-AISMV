#!/bin/bash

# Attempt to install wkhtmltopdf for PDF generation.
# Note: This may fail on some platforms with read-only filesystems.
apt-get update && apt-get install -y wkhtmltopdf

# Install Python dependencies
pip install -r requirements.txt

# Initialize the database on every deployment
# This is necessary for ephemeral filesystems on free hosting tiers.
flask init-db
