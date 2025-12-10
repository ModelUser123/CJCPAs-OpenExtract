"""
Core PDF extraction functionality for OpenExtract.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import pandas as pd
import pdfplumber

from .template_loader import TemplateLoader
from .utils import (
    coerce_value,
    clean_text,
    extract_first_match,
    format_date,
)


class Extractor:
    """
    Main class for extracting structured data from PDFs using templates.

    Example usage:
        >>> extractor = Extractor()
        >>> extractor.list_templates()
        >>> results = extractor.extract("form5500.pdf", template="form-5500")
        >>> results.to_csv("output.csv", index=False)
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the Extractor.

        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        self.loader = TemplateLoader(templates_dir)

    def list_templates(self, category: Optional[str] = None) -> None:
        """
        Pretty print available templates.

        Args:
            category: Optional category to filter by (e.g., '401k', 'tax-forms')
        """
        templates = self.loader.list_templates()

        if category:
            templates = [t for t in templates if category.lower() in t['category'].lower()]

        if not templates:
            print("No templates found.")
            return

        # Group by category
        by_category: Dict[str, List] = {}
        for t in templates:
            cat = t['category'] or 'other'
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(t)

        print("\n" + "=" * 60)
        print("AVAILABLE TEMPLATES")
        print("=" * 60)

        for cat in sorted(by_category.keys()):
            print(f"\n[{cat.upper()}]")
            print("-" * 40)
            for t in by_category[cat]:
                print(f"  {t['id']:<30} v{t['version']}")
                if t['description']:
                    # Truncate long descriptions
                    desc = t['description'][:50] + "..." if len(t['description']) > 50 else t['description']
                    print(f"    {desc}")

        print("\n" + "=" * 60)
        print(f"Total: {len(templates)} templates")
        print("=" * 60 + "\n")

    def get_template_info(self, template_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific template.

        Args:
            template_id: The template identifier

        Returns:
            Template dictionary with all details, or None if not found
        """
        return self.loader.get_template(template_id)

    def extract(
        self,
        pdf_path: Union[str, Path],
        template: str,
        pages: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Extract data from a PDF using the specified template.

        Args:
            pdf_path: Path to the PDF file
            template: Template ID to use for extraction
            pages: Optional list of page numbers to process (1-indexed).
                   If None, processes all pages.

        Returns:
            pandas DataFrame with extracted data

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If template is not found
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        template_def = self.loader.get_template(template)
        if not template_def:
            available = [t['id'] for t in self.loader.list_templates()]
            raise ValueError(
                f"Template '{template}' not found. "
                f"Available templates: {', '.join(available[:10])}..."
            )

        # Extract text from PDF
        text = self._extract_pdf_text(pdf_path, pages)

        # Extract fields using template
        extracted_data = self._extract_fields(text, template_def)

        # Format output
        return self._format_output(extracted_data, template_def)

    def extract_batch(
        self,
        pdf_paths: List[Union[str, Path]],
        template: str,
        continue_on_error: bool = True,
    ) -> pd.DataFrame:
        """
        Extract data from multiple PDFs using the same template.

        Args:
            pdf_paths: List of paths to PDF files
            template: Template ID to use for extraction
            continue_on_error: If True, continue processing on errors

        Returns:
            pandas DataFrame with extracted data from all PDFs
        """
        all_results = []

        for pdf_path in pdf_paths:
            try:
                result = self.extract(pdf_path, template)
                result['_source_file'] = str(pdf_path)
                all_results.append(result)
            except Exception as e:
                if continue_on_error:
                    print(f"Error processing {pdf_path}: {e}")
                    continue
                else:
                    raise

        if not all_results:
            return pd.DataFrame()

        return pd.concat(all_results, ignore_index=True)

    def _extract_pdf_text(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
    ) -> str:
        """Extract text content from PDF."""
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            page_indices = range(len(pdf.pages))

            if pages:
                # Convert 1-indexed to 0-indexed
                page_indices = [p - 1 for p in pages if 0 < p <= len(pdf.pages)]

            for i in page_indices:
                page = pdf.pages[i]
                page_text = page.extract_text() or ''
                text_parts.append(f"--- PAGE {i + 1} ---\n{page_text}")

        return '\n\n'.join(text_parts)

    def _extract_fields(self, text: str, template: Dict) -> Dict[str, Any]:
        """Extract all fields from text using template definition."""
        extracted = {}

        for field_def in template.get('fields', []):
            field_name = field_def['field_name']
            extraction_method = field_def.get('extraction_method', 'regex')

            value = None

            if extraction_method == 'regex':
                value = self._extract_with_regex(text, field_def)
            elif extraction_method == 'coordinates':
                # Coordinate extraction would require page-level processing
                # For now, fall back to regex if available
                value = self._extract_with_regex(text, field_def)
            elif extraction_method == 'keyword_proximity':
                value = self._extract_with_keyword_proximity(text, field_def)

            # Coerce to appropriate type
            data_type = field_def.get('data_type', 'string')
            extracted[field_name] = coerce_value(value, data_type)

        return extracted

    def _extract_with_regex(self, text: str, field_def: Dict) -> Optional[str]:
        """Extract field value using regex patterns."""
        patterns = [field_def.get('regex_pattern')]
        patterns.extend(field_def.get('fallback_patterns', []))

        for pattern in patterns:
            if not pattern:
                continue

            value = extract_first_match(text, pattern)
            if value:
                return clean_text(value)

        return field_def.get('default_value')

    def _extract_with_keyword_proximity(
        self,
        text: str,
        field_def: Dict,
    ) -> Optional[str]:
        """Extract field value based on proximity to keywords."""
        keywords = field_def.get('keywords', [])
        max_distance = field_def.get('max_distance', 50)

        for keyword in keywords:
            # Find keyword in text
            pattern = rf'{re.escape(keyword)}\s*[:=]?\s*(\S+(?:\s+\S+)*)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get text after keyword, limited by distance
                value = match.group(1)[:max_distance]
                return clean_text(value.split('\n')[0])

        return field_def.get('default_value')

    def _format_output(self, data: Dict[str, Any], template: Dict) -> pd.DataFrame:
        """Format extracted data as a DataFrame."""
        output_format = template.get('output_format', {})
        csv_headers = output_format.get('csv_headers', list(data.keys()))
        date_format = output_format.get('date_format', 'YYYY-MM-DD')

        # Build row with columns in specified order
        row = {}
        for header in csv_headers:
            value = data.get(header)

            # Format dates according to output format
            if value and self._is_date_field(header, template):
                value = format_date(value, date_format)

            row[header] = value

        return pd.DataFrame([row])

    def _is_date_field(self, field_name: str, template: Dict) -> bool:
        """Check if a field is a date type."""
        for field_def in template.get('fields', []):
            if field_def.get('field_name') == field_name:
                return field_def.get('data_type') == 'date'
        return False

    def validate_extraction(
        self,
        results: pd.DataFrame,
        template: str,
    ) -> Dict[str, Any]:
        """
        Validate extraction results against template requirements.

        Args:
            results: DataFrame with extraction results
            template: Template ID used for extraction

        Returns:
            Dictionary with validation results
        """
        template_def = self.loader.get_template(template)
        if not template_def:
            return {'valid': False, 'errors': ['Template not found']}

        errors = []
        warnings = []

        for field_def in template_def.get('fields', []):
            field_name = field_def['field_name']
            required = field_def.get('required', False)
            validation = field_def.get('validation')

            if field_name not in results.columns:
                if required:
                    errors.append(f"Required field '{field_name}' not in results")
                continue

            value = results[field_name].iloc[0] if len(results) > 0 else None

            # Check required fields
            if required and (value is None or value == ''):
                errors.append(f"Required field '{field_name}' is empty")

            # Validate against pattern if provided
            if validation and value:
                if not re.match(validation, str(value)):
                    warnings.append(
                        f"Field '{field_name}' value '{value}' "
                        f"doesn't match pattern '{validation}'"
                    )

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'fields_extracted': len([c for c in results.columns if results[c].notna().any()]),
            'fields_total': len(template_def.get('fields', [])),
        }
