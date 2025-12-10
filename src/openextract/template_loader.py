"""
Template loading and management for OpenExtract.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class TemplateLoader:
    """Loads and manages extraction templates."""

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template loader.

        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to templates directory relative to this file's package
            package_dir = Path(__file__).parent.parent.parent
            templates_dir = package_dir / 'templates'

        self.templates_dir = Path(templates_dir)
        self._templates: Dict[str, Dict] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the templates directory."""
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

        # Walk through all subdirectories
        for json_file in self.templates_dir.rglob('*.json'):
            # Skip schema and example files
            if json_file.name.startswith('_'):
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)

                # Validate required fields
                if 'template_id' in template and 'fields' in template:
                    self._templates[template['template_id']] = template

                    # Calculate relative path for categorization
                    rel_path = json_file.relative_to(self.templates_dir)
                    template['_category'] = str(rel_path.parent)
                    template['_file_path'] = str(json_file)
            except (json.JSONDecodeError, KeyError) as e:
                # Skip invalid templates
                print(f"Warning: Could not load template {json_file}: {e}")

    def get_template(self, template_id: str) -> Optional[Dict]:
        """
        Get a template by its ID.

        Args:
            template_id: The unique template identifier

        Returns:
            Template dictionary or None if not found
        """
        return self._templates.get(template_id)

    def list_templates(self) -> List[Dict[str, str]]:
        """
        Get a list of all available templates.

        Returns:
            List of dicts with template info (id, name, description, category)
        """
        templates = []
        for template_id, template in self._templates.items():
            templates.append({
                'id': template_id,
                'name': template.get('template_name', template_id),
                'description': template.get('description', ''),
                'category': template.get('_category', 'other'),
                'document_type': template.get('document_type', 'other'),
                'version': template.get('version', '1.0.0'),
            })

        # Sort by category then name
        templates.sort(key=lambda x: (x['category'], x['name']))
        return templates

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """
        Get all templates in a specific category.

        Args:
            category: Category name (e.g., '401k', 'tax-forms')

        Returns:
            List of template dictionaries
        """
        return [
            t for t in self._templates.values()
            if t.get('_category', '').lower() == category.lower()
        ]

    def get_templates_by_type(self, document_type: str) -> List[Dict]:
        """
        Get all templates for a specific document type.

        Args:
            document_type: Document type (e.g., 'tax-form', 'invoice')

        Returns:
            List of template dictionaries
        """
        return [
            t for t in self._templates.values()
            if t.get('document_type', '').lower() == document_type.lower()
        ]

    def search_templates(self, query: str) -> List[Dict[str, str]]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query string

        Returns:
            List of matching template info dicts
        """
        query_lower = query.lower()
        results = []

        for template_id, template in self._templates.items():
            # Search in name
            if query_lower in template.get('template_name', '').lower():
                results.append(self._template_info(template))
                continue

            # Search in description
            if query_lower in template.get('description', '').lower():
                results.append(self._template_info(template))
                continue

            # Search in tags
            tags = template.get('tags', [])
            if any(query_lower in tag.lower() for tag in tags):
                results.append(self._template_info(template))
                continue

            # Search in template_id
            if query_lower in template_id.lower():
                results.append(self._template_info(template))

        return results

    def _template_info(self, template: Dict) -> Dict[str, str]:
        """Extract summary info from a template."""
        return {
            'id': template.get('template_id', ''),
            'name': template.get('template_name', ''),
            'description': template.get('description', ''),
            'category': template.get('_category', 'other'),
            'document_type': template.get('document_type', 'other'),
        }

    def validate_template(self, template: Dict) -> List[str]:
        """
        Validate a template against the schema.

        Args:
            template: Template dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required top-level fields
        required_fields = ['template_id', 'template_name', 'description',
                          'document_type', 'version', 'fields', 'output_format']

        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")

        # Validate template_id format
        template_id = template.get('template_id', '')
        if template_id and not template_id.replace('-', '').replace('_', '').isalnum():
            errors.append("template_id must contain only lowercase letters, numbers, and hyphens")

        # Validate version format
        version = template.get('version', '')
        if version:
            parts = version.split('.')
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append("version must be in semantic format (e.g., 1.0.0)")

        # Validate fields
        fields = template.get('fields', [])
        if not isinstance(fields, list):
            errors.append("fields must be an array")
        else:
            for i, field in enumerate(fields):
                field_errors = self._validate_field(field, i)
                errors.extend(field_errors)

        # Validate output_format
        output_format = template.get('output_format', {})
        if 'csv_headers' not in output_format:
            errors.append("output_format must include csv_headers")

        return errors

    def _validate_field(self, field: Dict, index: int) -> List[str]:
        """Validate a single field definition."""
        errors = []
        prefix = f"Field {index}"

        required = ['field_name', 'display_name', 'data_type', 'required', 'extraction_method']
        for req in required:
            if req not in field:
                errors.append(f"{prefix}: Missing required property '{req}'")

        # Validate field_name format
        field_name = field.get('field_name', '')
        if field_name and not field_name.replace('_', '').isalnum():
            errors.append(f"{prefix}: field_name must be snake_case")

        # Validate data_type
        valid_types = ['string', 'integer', 'currency', 'date', 'boolean', 'decimal', 'percentage']
        data_type = field.get('data_type', '')
        if data_type and data_type not in valid_types:
            errors.append(f"{prefix}: Invalid data_type '{data_type}'")

        # Validate extraction_method
        valid_methods = ['regex', 'coordinates', 'table', 'keyword_proximity']
        method = field.get('extraction_method', '')
        if method and method not in valid_methods:
            errors.append(f"{prefix}: Invalid extraction_method '{method}'")

        # If regex method, require regex_pattern
        if method == 'regex' and 'regex_pattern' not in field:
            errors.append(f"{prefix}: regex extraction_method requires regex_pattern")

        # If coordinates method, require coordinates
        if method == 'coordinates' and 'coordinates' not in field:
            errors.append(f"{prefix}: coordinates extraction_method requires coordinates object")

        return errors

    def reload(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_templates()

    @property
    def template_count(self) -> int:
        """Get the number of loaded templates."""
        return len(self._templates)

    @property
    def categories(self) -> List[str]:
        """Get list of all template categories."""
        categories = set()
        for template in self._templates.values():
            cat = template.get('_category', 'other')
            if cat:
                categories.add(cat)
        return sorted(list(categories))
