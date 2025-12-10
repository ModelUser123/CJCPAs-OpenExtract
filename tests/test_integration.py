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

    def test_form_5500_extracts_plan_name(self, extractor, sample_text):
        """Test that plan name is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500')
                assert 'Midwest Manufacturing' in results['plan_name'].iloc[0]
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
                assert results['ein'].iloc[0] == '36-1234567'
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
                assert results['total_participants_boy'].iloc[0] == 487
                assert results['total_participants_eoy'].iloc[0] == 512
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
                assert results['total_assets_boy'].iloc[0] == 28620000.0
                assert results['total_assets_eoy'].iloc[0] == 31444000.0
                assert results['net_assets_eoy'].iloc[0] == 31426000.0
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

    def test_form_5500_sf_extracts_plan_name(self, extractor, sample_text):
        """Test that plan name is extracted correctly."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4')
            pdf_path = f.name

        try:
            with patch.object(extractor, '_extract_pdf_text', return_value=sample_text):
                results = extractor.extract(pdf_path, template='form-5500-sf')
                assert 'Johnson Family Dental' in results['plan_name'].iloc[0]
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
                assert results['employer_contributions'].iloc[0] == 42000.0
                assert results['participant_contributions'].iloc[0] == 68500.0
                assert results['total_contributions'].iloc[0] == 125000.0
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
                assert results['total_plan_assets_eoy'].iloc[0] == 485000.0
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
                assert loaded['ein'].iloc[0] == '36-1234567'
                assert loaded['total_participants_eoy'].iloc[0] == 512
        finally:
            os.unlink(pdf_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
