"""
Tests for the PDF extraction functionality.
"""

import os
import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

import pytest
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from openextract import Extractor
from openextract.utils import (
    parse_currency,
    parse_integer,
    parse_percentage,
    parse_date,
    format_date,
    clean_text,
    normalize_ein,
    normalize_ssn,
    coerce_value,
)


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_parse_currency_basic(self):
        """Test basic currency parsing."""
        assert parse_currency('$1,234.56') == 1234.56
        assert parse_currency('1234.56') == 1234.56
        assert parse_currency('$1,234') == 1234.0

    def test_parse_currency_negative(self):
        """Test negative currency parsing."""
        assert parse_currency('($1,234.56)') == -1234.56
        assert parse_currency('-$1,234.56') == -1234.56

    def test_parse_currency_invalid(self):
        """Test invalid currency values."""
        assert parse_currency('') is None
        assert parse_currency(None) is None
        assert parse_currency('abc') is None

    def test_parse_integer_basic(self):
        """Test basic integer parsing."""
        assert parse_integer('1,234') == 1234
        assert parse_integer('1234') == 1234
        assert parse_integer('0') == 0

    def test_parse_integer_invalid(self):
        """Test invalid integer values."""
        assert parse_integer('') is None
        assert parse_integer(None) is None

    def test_parse_percentage(self):
        """Test percentage parsing."""
        assert parse_percentage('12.5%') == 12.5
        assert parse_percentage('12.5') == 12.5
        assert parse_percentage('100%') == 100.0

    def test_parse_date_various_formats(self):
        """Test date parsing with various formats."""
        assert parse_date('01/15/2024') == '2024-01-15'
        assert parse_date('01-15-2024') == '2024-01-15'
        assert parse_date('2024-01-15') == '2024-01-15'

    def test_parse_date_invalid(self):
        """Test invalid date values."""
        assert parse_date('') is None
        assert parse_date(None) is None
        assert parse_date('not a date') is None

    def test_format_date(self):
        """Test date formatting."""
        assert format_date('2024-01-15', 'MM/DD/YYYY') == '01/15/2024'
        assert format_date('2024-01-15', 'YYYY-MM-DD') == '2024-01-15'

    def test_clean_text(self):
        """Test text cleaning."""
        assert clean_text('  hello   world  ') == 'hello world'
        assert clean_text('hello\n\nworld') == 'hello world'
        assert clean_text('') == ''

    def test_normalize_ein(self):
        """Test EIN normalization."""
        assert normalize_ein('123456789') == '12-3456789'
        assert normalize_ein('12-3456789') == '12-3456789'
        assert normalize_ein('12 3456789') == '12-3456789'

    def test_normalize_ein_invalid(self):
        """Test invalid EIN values."""
        assert normalize_ein('12345') is None
        assert normalize_ein('') is None
        assert normalize_ein(None) is None

    def test_normalize_ssn(self):
        """Test SSN normalization."""
        assert normalize_ssn('123456789') == '123-45-6789'
        assert normalize_ssn('123-45-6789') == '123-45-6789'

    def test_coerce_value(self):
        """Test value coercion."""
        assert coerce_value('$1,234.56', 'currency') == 1234.56
        assert coerce_value('1,234', 'integer') == 1234
        assert coerce_value('12.5%', 'percentage') == 12.5
        assert coerce_value('01/15/2024', 'date') == '2024-01-15'
        assert coerce_value('  hello  ', 'string') == 'hello'
        assert coerce_value('yes', 'boolean') is True


class TestExtractor:
    """Tests for the Extractor class."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    def test_extractor_initialization(self, extractor):
        """Test extractor initializes properly."""
        assert extractor is not None
        assert extractor.loader.template_count > 0

    def test_list_templates(self, extractor, capsys):
        """Test listing templates."""
        extractor.list_templates()
        captured = capsys.readouterr()
        assert 'AVAILABLE TEMPLATES' in captured.out
        assert 'form-5500' in captured.out

    def test_list_templates_by_category(self, extractor, capsys):
        """Test listing templates filtered by category."""
        extractor.list_templates(category='401k')
        captured = capsys.readouterr()
        assert '401K' in captured.out

    def test_get_template_info(self, extractor):
        """Test getting template info."""
        info = extractor.get_template_info('form-5500')
        assert info is not None
        assert info['template_id'] == 'form-5500'

    def test_get_nonexistent_template(self, extractor):
        """Test getting info for nonexistent template."""
        info = extractor.get_template_info('nonexistent')
        assert info is None

    def test_extract_file_not_found(self, extractor):
        """Test extraction with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            extractor.extract('nonexistent.pdf', template='form-5500')

    def test_extract_template_not_found(self, extractor, tmp_path):
        """Test extraction with nonexistent template."""
        # Create a dummy PDF file
        pdf_path = tmp_path / 'test.pdf'
        pdf_path.write_bytes(b'%PDF-1.4 dummy content')

        with pytest.raises(ValueError) as exc_info:
            extractor.extract(str(pdf_path), template='nonexistent')
        assert 'not found' in str(exc_info.value)


class TestExtractionWithMockPDF:
    """Tests for extraction with mocked PDF content."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    @pytest.fixture
    def form_5500_text(self):
        """Sample text content from a Form 5500."""
        return """
        --- PAGE 1 ---
        Form 5500 Annual Return/Report of Employee Benefit Plan

        1a Name of plan: ACME Corporation 401(k) Plan
        1b Plan number: 001
        1c Plan year beginning: 01/01/2023 and ending 12/31/2023

        2a Sponsor's name: ACME Corporation
        2b EIN: 12-3456789
        2c Address: 123 Main Street, Anytown, CA 90210
        2d Phone: (555) 123-4567

        3a Administrator's name: ACME Corporation
        3b Administrator's EIN: 12-3456789

        8a Type of plan: 401(k) Plan

        5 Total number of participants beginning of year: 150
        6 Total number of participants end of year: 175
        7a Active participants: 160
        7b Retired/Separated participants: 10
        7c Deceased participants: 5

        --- PAGE 2 ---
        Part III - Financial Information

        1a Total assets beginning of year: $2,500,000.00
        1b Total assets end of year: $3,000,000.00
        2a Total liabilities beginning of year: $50,000.00
        2b Total liabilities end of year: $45,000.00
        3a Net assets beginning of year: $2,450,000.00
        3b Net assets end of year: $2,955,000.00
        """

    @pytest.fixture
    def form_5500_sf_text(self):
        """Sample text content from a Form 5500-SF."""
        return """
        --- PAGE 1 ---
        Form 5500-SF Short Form Annual Return/Report

        1a Name of plan: Small Business 401(k) Plan
        1b Plan number: 001
        Plan year beginning: 01/01/2023 and ending 12/31/2023

        2a Sponsor's name: Small Business Inc
        2b EIN: 98-7654321

        5 Total number of participants beginning of year: 25
        6 Total number of participants end of year: 30
        6a Eligible participants: 35
        6b Active participants with account balances: 28

        --- PAGE 2 ---
        Part V - Financial Information

        8 Total plan assets: $750,000.00
        9a Employer contributions: $50,000.00
        9b Participant contributions: $75,000.00
        9c Rollover contributions: $10,000.00
        9d Other contributions: $5,000.00
        9e Total contributions: $140,000.00
        10 Total distributions: $25,000.00
        11 Administrative expenses: $3,500.00
        """

    def test_extract_form_5500(self, extractor, form_5500_text, tmp_path):
        """Test extraction from Form 5500."""
        # Create a mock PDF
        pdf_path = tmp_path / 'form5500.pdf'
        pdf_path.write_bytes(b'%PDF-1.4')  # Minimal PDF header

        with patch.object(extractor, '_extract_pdf_text', return_value=form_5500_text):
            results = extractor.extract(str(pdf_path), template='form-5500')

        assert isinstance(results, pd.DataFrame)
        assert len(results) == 1

        # Check key fields were extracted
        assert results['plan_name'].iloc[0] == 'ACME Corporation 401(k) Plan'
        assert results['ein'].iloc[0] == '12-3456789'
        assert results['plan_number'].iloc[0] == '001'
        assert results['total_participants_boy'].iloc[0] == 150
        assert results['total_participants_eoy'].iloc[0] == 175
        assert results['total_assets_eoy'].iloc[0] == 3000000.00

    def test_extract_form_5500_sf(self, extractor, form_5500_sf_text, tmp_path):
        """Test extraction from Form 5500-SF."""
        pdf_path = tmp_path / 'form5500sf.pdf'
        pdf_path.write_bytes(b'%PDF-1.4')

        with patch.object(extractor, '_extract_pdf_text', return_value=form_5500_sf_text):
            results = extractor.extract(str(pdf_path), template='form-5500-sf')

        assert isinstance(results, pd.DataFrame)
        # Form 5500-SF uses vertical format with line codes (78 rows)
        assert len(results) == 78
        assert list(results.columns) == ['line_code', 'field_name', 'display_name', 'value']

        # Helper to get value by field name from vertical format
        def get_value(field_name):
            row = results[results['field_name'] == field_name]
            return row['value'].iloc[0] if len(row) > 0 else None

        # Check key fields were extracted
        assert get_value('plan_name') == 'Small Business 401(k) Plan'
        assert get_value('ein') == '98-7654321'
        assert get_value('total_participants_eoy') == 30
        # Currency values are formatted as strings in vertical format
        assert get_value('total_plan_assets_eoy') == '$750,000'
        assert get_value('total_contributions') == '$140,000'

    def test_validate_extraction(self, extractor, form_5500_text, tmp_path):
        """Test extraction validation."""
        pdf_path = tmp_path / 'form5500.pdf'
        pdf_path.write_bytes(b'%PDF-1.4')

        with patch.object(extractor, '_extract_pdf_text', return_value=form_5500_text):
            results = extractor.extract(str(pdf_path), template='form-5500')
            validation = extractor.validate_extraction(results, 'form-5500')

        assert validation['valid'] is True
        assert len(validation['errors']) == 0
        assert validation['fields_extracted'] > 0


class TestExtractionRegex:
    """Tests for regex extraction patterns."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    def test_ein_extraction_formats(self, extractor):
        """Test EIN extraction with various formats."""
        test_cases = [
            ("EIN: 12-3456789", "12-3456789"),
            ("Employer Identification Number: 12-3456789", "12-3456789"),
            ("EIN 123456789", "123456789"),
        ]

        template = extractor.loader.get_template('form-5500')
        ein_field = next(f for f in template['fields'] if f['field_name'] == 'ein')

        from openextract.utils import extract_first_match

        for text, expected in test_cases:
            result = extract_first_match(text, ein_field['regex_pattern'])
            assert result is not None, f"Failed to extract EIN from: {text}"

    def test_currency_extraction_formats(self, extractor):
        """Test currency extraction with various formats."""
        test_cases = [
            "$1,234,567.89",
            "1,234,567.89",
            "$1234567.89",
            "1234567",
        ]

        for value in test_cases:
            result = parse_currency(value)
            assert result is not None, f"Failed to parse currency: {value}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
