"""
OpenExtract - PDF Data Extraction for Accountants

A simple, template-based PDF extraction tool designed for accountants.
Extract structured data from tax forms, financial statements, and more.

Example usage:
    >>> from openextract import Extractor
    >>> extractor = Extractor()
    >>> extractor.list_templates()
    >>> results = extractor.extract("form5500.pdf", template="form-5500")
    >>> results.to_csv("output.csv", index=False)

For use in Google Colab:
    !pip install pdfplumber pandas
    !git clone https://github.com/YOUR_USERNAME/openextract.git
    import sys
    sys.path.insert(0, 'openextract/src')
    from openextract import Extractor
"""

from .extractor import Extractor
from .template_loader import TemplateLoader
from .utils import (
    parse_currency,
    parse_integer,
    parse_percentage,
    parse_date,
    format_date,
    clean_text,
    normalize_ein,
    normalize_ssn,
)

__version__ = '1.0.0'
__author__ = 'OpenExtract Community'
__all__ = [
    'Extractor',
    'TemplateLoader',
    'parse_currency',
    'parse_integer',
    'parse_percentage',
    'parse_date',
    'format_date',
    'clean_text',
    'normalize_ein',
    'normalize_ssn',
]
