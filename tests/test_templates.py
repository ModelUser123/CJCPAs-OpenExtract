"""
Tests for template validation and loading.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from openextract.template_loader import TemplateLoader


class TestTemplateLoader:
    """Tests for the TemplateLoader class."""

    @pytest.fixture
    def loader(self):
        """Create a template loader instance."""
        templates_dir = Path(__file__).parent.parent / 'templates'
        return TemplateLoader(templates_dir)

    def test_loader_initialization(self, loader):
        """Test that loader initializes and finds templates."""
        assert loader.template_count > 0, "Should find at least one template"

    def test_list_templates(self, loader):
        """Test listing all templates."""
        templates = loader.list_templates()
        assert len(templates) > 0, "Should return list of templates"

        # Check structure of returned data
        for t in templates:
            assert 'id' in t
            assert 'name' in t
            assert 'description' in t
            assert 'category' in t

    def test_get_template(self, loader):
        """Test getting a specific template."""
        template = loader.get_template('form-5500')
        assert template is not None, "Should find form-5500 template"
        assert template['template_id'] == 'form-5500'

    def test_get_nonexistent_template(self, loader):
        """Test getting a template that doesn't exist."""
        template = loader.get_template('nonexistent-template')
        assert template is None

    def test_categories(self, loader):
        """Test getting template categories."""
        categories = loader.categories
        assert len(categories) > 0, "Should have at least one category"
        assert '401k' in categories, "Should have 401k category"

    def test_search_templates(self, loader):
        """Test searching templates."""
        results = loader.search_templates('5500')
        assert len(results) > 0, "Should find templates with '5500'"

    def test_templates_by_category(self, loader):
        """Test getting templates by category."""
        templates = loader.get_templates_by_category('401k')
        assert len(templates) > 0, "Should find 401k templates"


class TestTemplateValidation:
    """Tests for template JSON validation."""

    @pytest.fixture
    def templates_dir(self):
        """Get templates directory."""
        return Path(__file__).parent.parent / 'templates'

    @pytest.fixture
    def schema(self, templates_dir):
        """Load the template schema."""
        schema_path = templates_dir / '_schema.json'
        with open(schema_path, 'r') as f:
            return json.load(f)

    def get_all_template_files(self, templates_dir):
        """Get all template JSON files."""
        return [
            f for f in templates_dir.rglob('*.json')
            if not f.name.startswith('_')
        ]

    def test_all_templates_valid_json(self, templates_dir):
        """Test that all template files are valid JSON."""
        for template_file in self.get_all_template_files(templates_dir):
            try:
                with open(template_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {template_file}: {e}")

    def test_all_templates_have_required_fields(self, templates_dir):
        """Test that all templates have required fields."""
        required_fields = [
            'template_id', 'template_name', 'description',
            'document_type', 'version', 'fields', 'output_format'
        ]

        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for field in required_fields:
                assert field in template, \
                    f"Missing '{field}' in {template_file}"

    def test_all_templates_have_valid_fields(self, templates_dir):
        """Test that all template fields have required properties."""
        required_field_props = [
            'field_name', 'display_name', 'data_type',
            'required', 'extraction_method'
        ]

        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for i, field in enumerate(template.get('fields', [])):
                for prop in required_field_props:
                    assert prop in field, \
                        f"Missing '{prop}' in field {i} of {template_file}"

    def test_template_ids_are_unique(self, templates_dir):
        """Test that all template IDs are unique."""
        ids = []
        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)
            template_id = template.get('template_id')
            assert template_id not in ids, \
                f"Duplicate template_id: {template_id}"
            ids.append(template_id)

    def test_template_ids_format(self, templates_dir):
        """Test that template IDs follow naming convention."""
        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            template_id = template.get('template_id', '')
            assert template_id == template_id.lower(), \
                f"Template ID should be lowercase: {template_id}"
            assert ' ' not in template_id, \
                f"Template ID should not contain spaces: {template_id}"

    def test_field_names_format(self, templates_dir):
        """Test that field names follow snake_case convention."""
        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for field in template.get('fields', []):
                field_name = field.get('field_name', '')
                assert field_name == field_name.lower(), \
                    f"Field name should be lowercase in {template_file}: {field_name}"
                assert ' ' not in field_name, \
                    f"Field name should not contain spaces in {template_file}: {field_name}"

    def test_valid_data_types(self, templates_dir):
        """Test that all data types are valid."""
        valid_types = [
            'string', 'integer', 'currency', 'date',
            'boolean', 'decimal', 'percentage'
        ]

        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for field in template.get('fields', []):
                data_type = field.get('data_type')
                assert data_type in valid_types, \
                    f"Invalid data_type '{data_type}' in {template_file}"

    def test_valid_extraction_methods(self, templates_dir):
        """Test that all extraction methods are valid."""
        valid_methods = ['regex', 'coordinates', 'table', 'keyword_proximity']

        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for field in template.get('fields', []):
                method = field.get('extraction_method')
                assert method in valid_methods, \
                    f"Invalid extraction_method '{method}' in {template_file}"

    def test_regex_patterns_compile(self, templates_dir):
        """Test that all regex patterns are valid."""
        import re

        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            for field in template.get('fields', []):
                pattern = field.get('regex_pattern')
                if pattern:
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        pytest.fail(
                            f"Invalid regex in {template_file}, "
                            f"field '{field.get('field_name')}': {e}"
                        )

                # Also check fallback patterns
                for fb_pattern in field.get('fallback_patterns', []):
                    try:
                        re.compile(fb_pattern)
                    except re.error as e:
                        pytest.fail(
                            f"Invalid fallback regex in {template_file}, "
                            f"field '{field.get('field_name')}': {e}"
                        )

    def test_csv_headers_match_fields(self, templates_dir):
        """Test that CSV headers reference valid field names."""
        for template_file in self.get_all_template_files(templates_dir):
            with open(template_file, 'r') as f:
                template = json.load(f)

            field_names = {f.get('field_name') for f in template.get('fields', [])}
            csv_headers = template.get('output_format', {}).get('csv_headers', [])

            for header in csv_headers:
                assert header in field_names, \
                    f"CSV header '{header}' not in fields for {template_file}"


class TestPriorityTemplates:
    """Specific tests for priority Form 5500 templates."""

    @pytest.fixture
    def loader(self):
        """Create a template loader instance."""
        templates_dir = Path(__file__).parent.parent / 'templates'
        return TemplateLoader(templates_dir)

    def test_form_5500_exists(self, loader):
        """Test that Form 5500 template exists."""
        template = loader.get_template('form-5500')
        assert template is not None, "Form 5500 template should exist"

    def test_form_5500_sf_exists(self, loader):
        """Test that Form 5500-SF template exists."""
        template = loader.get_template('form-5500-sf')
        assert template is not None, "Form 5500-SF template should exist"

    def test_form_5500_required_fields(self, loader):
        """Test that Form 5500 has all required fields."""
        template = loader.get_template('form-5500')
        field_names = {f['field_name'] for f in template['fields']}

        required = [
            'plan_name', 'ein', 'plan_number',
            'plan_year_begin', 'plan_year_end',
            'sponsor_name', 'total_participants_boy',
            'total_participants_eoy', 'total_assets_boy',
            'total_assets_eoy'
        ]

        for field in required:
            assert field in field_names, \
                f"Form 5500 should have '{field}' field"

    def test_form_5500_sf_required_fields(self, loader):
        """Test that Form 5500-SF has all required fields."""
        template = loader.get_template('form-5500-sf')
        field_names = {f['field_name'] for f in template['fields']}

        required = [
            'plan_name', 'ein', 'plan_number',
            'plan_year_begin', 'plan_year_end',
            'sponsor_name', 'total_participants_eoy',
            'total_plan_assets_eoy', 'total_contributions',
            'benefit_payments'
        ]

        for field in required:
            assert field in field_names, \
                f"Form 5500-SF should have '{field}' field"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
