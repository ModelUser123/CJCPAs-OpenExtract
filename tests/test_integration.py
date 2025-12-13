"""
Integration tests that run actual extractions against sample data.

These tests verify the full extraction pipeline works correctly
by comparing extracted data against expected outputs.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
import tempfile

import pytest
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from openextract import Extractor


class TestForm5500Integration:
    """Integration tests for Form 5500 extraction."""

    @pytest.fixture
    def extractor(self):
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    @pytest.fixture
    def sample_text(self):
        sample_path = Path(__file__).parent / 'sample_data' / 'inputs' / 'sample_form_5500.txt'
        with open(sample_path, 'r') as f:
            return f.read()

    def _get_value(self, results, field_name):
        """Helper to get value by field name from vertical format DataFrame."""
        row = results[results['field_name'] == field_name]
        return row['value'].iloc[0] if len(row) > 0 else None

    def test_form_5500_extracts_plan_name(self, extractor, sample_text):
        """Test that plan name is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                plan_name = self._get_value(results, 'plan_name')
                assert plan_name is not None and 'Midwest Manufacturing' in plan_name
        finally:
            os.unlink(pdf_path)

    def test_form_5500_extracts_ein(self, extractor, sample_text):
        """Test that EIN is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                assert self._get_value(results, 'ein') == '36-1234567'
        finally:
            os.unlink(pdf_path)

    def test_form_5500_extracts_participant_counts(self, extractor, sample_text):
        """Test that participant counts are extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                assert self._get_value(results, 'total_participants_boy') == 487
                assert self._get_value(results, 'total_participants_eoy') == 512
        finally:
            os.unlink(pdf_path)

    def test_form_5500_extracts_financial_data(self, extractor, sample_text):
        """Test that financial data is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                # Currency values are formatted in vertical output
                assert self._get_value(results, 'total_assets_boy') == '$28,620,000'
                assert self._get_value(results, 'total_assets_eoy') == '$31,444,000'
                assert self._get_value(results, 'net_assets_eoy') == '$31,426,000'
        finally:
            os.unlink(pdf_path)


class TestForm5500SFIntegration:
    """Integration tests for Form 5500-SF extraction."""

    @pytest.fixture
    def extractor(self):
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    @pytest.fixture
    def sample_text(self):
        sample_path = Path(__file__).parent / 'sample_data' / 'inputs' / 'sample_form_5500_sf.txt'
        with open(sample_path, 'r') as f:
            return f.read()

    def _get_value(self, results, field_name):
        """Helper to get value by field name from vertical format DataFrame."""
        row = results[results['field_name'] == field_name]
        return row['value'].iloc[0] if len(row) > 0 else None

    def test_form_5500_sf_extracts_plan_name(self, extractor, sample_text):
        """Test that plan name is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500-sf')
                plan_name = self._get_value(results, 'plan_name')
                assert plan_name is not None and 'Johnson Family Dental' in plan_name
        finally:
            os.unlink(pdf_path)

    def test_form_5500_sf_extracts_contributions(self, extractor, sample_text):
        """Test that contribution data is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500-sf')
                # Currency values are formatted as strings in vertical format
                assert self._get_value(results, 'employer_contributions') == '$42,000'
                assert self._get_value(results, 'participant_contributions') == '$68,500'
                assert self._get_value(results, 'total_contributions') == '$125,000'
        finally:
            os.unlink(pdf_path)

    def test_form_5500_sf_extracts_assets(self, extractor, sample_text):
        """Test that asset data is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500-sf')
                # Currency values are formatted as strings in vertical format
                assert self._get_value(results, 'total_plan_assets_eoy') == '$485,000'
        finally:
            os.unlink(pdf_path)


class Test1099NECIntegration:
    """Integration tests for 1099-NEC extraction."""

    @pytest.fixture
    def extractor(self):
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    @pytest.fixture
    def sample_text(self):
        sample_path = Path(__file__).parent / 'sample_data' / 'inputs' / 'sample_1099_nec.txt'
        with open(sample_path, 'r') as f:
            return f.read()

    def test_1099_nec_extracts_payer_info(self, extractor, sample_text):
        """Test that payer information is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='1099-nec')
                assert 'ABC Consulting' in results['payer_name'].iloc[0]
                assert results['payer_tin'].iloc[0] == '94-3456789'
        finally:
            os.unlink(pdf_path)

    def test_1099_nec_extracts_compensation(self, extractor, sample_text):
        """Test that compensation is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='1099-nec')
                assert results['box_1_nonemployee_compensation'].iloc[0] == 78500.0
        finally:
            os.unlink(pdf_path)


class TestInvoiceIntegration:
    """Integration tests for invoice extraction."""

    @pytest.fixture
    def extractor(self):
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    @pytest.fixture
    def sample_text(self):
        sample_path = Path(__file__).parent / 'sample_data' / 'inputs' / 'sample_invoice.txt'
        with open(sample_path, 'r') as f:
            return f.read()

    def test_invoice_extracts_vendor(self, extractor, sample_text):
        """Test that vendor name is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='generic-invoice')
                assert 'TechPro' in results['vendor_name'].iloc[0]
        finally:
            os.unlink(pdf_path)

    def test_invoice_extracts_subtotal(self, extractor, sample_text):
        """Test that subtotal is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='generic-invoice')
                assert results['subtotal'].iloc[0] == 16600.0
        finally:
            os.unlink(pdf_path)


class TestFullExtractionPipeline:
    """Test the complete extraction pipeline with output to CSV."""

    @pytest.fixture
    def extractor(self):
        templates_dir = Path(__file__).parent.parent / 'templates'
        return Extractor(templates_dir)

    def test_extraction_to_csv_round_trip(self, extractor, tmp_path):
        """Test extracting data and saving/loading from CSV."""
        sample_path = Path(__file__).parent / 'sample_data' / 'inputs' / 'sample_form_5500.txt'
        with open(sample_path, 'r') as f:
            sample_text = f.read()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                csv_path = tmp_path / 'output.csv'
                results.to_csv(csv_path, index=False)
                loaded = pd.read_csv(csv_path)
                # Vertical format: find values by field_name column
                ein_row = loaded[loaded['field_name'] == 'ein']
                participants_row = loaded[loaded['field_name'] == 'total_participants_eoy']
                assert ein_row['value'].iloc[0] == '36-1234567'
                assert int(participants_row['value'].iloc[0]) == 512
        finally:
            os.unlink(pdf_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
