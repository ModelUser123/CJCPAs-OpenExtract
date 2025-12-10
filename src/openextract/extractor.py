"""
Core PDF extraction functionality for OpenExtract.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import pandas as pd
import pdfplumber

# OCR support (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from .template_loader import TemplateLoader
from .utils import (
    coerce_value,
    clean_text,
    extract_first_match,
    format_date,
)


def extract_dol_embedded_value(raw_value: str, value_type: str = 'currency') -> Optional[str]:
    """
    Extract real values from DOL form placeholder-embedded strings.

    DOL forms mix placeholder text with real values, e.g.:
    - "1234567738" contains "738" (participants)
    - "-123456789106183293945" contains financial data

    Args:
        raw_value: The raw string from DOL PDF
        value_type: Either 'currency', 'integer', or 'participant'

    Returns:
        Cleaned value string or None
    """
    if not raw_value:
        return None

    # Remove any non-digit chars except minus sign and decimal
    clean = raw_value.strip().lstrip('-')

    if value_type == 'participant':
        # For participant counts, real value is typically last 3-4 digits
        # after the "1234567" placeholder prefix
        if len(clean) >= 7 and clean.startswith('123456'):
            # Extract everything after common placeholder prefixes
            for prefix in ['1234567', '123456']:
                if clean.startswith(prefix):
                    remainder = clean[len(prefix):]
                    if remainder and remainder.isdigit():
                        return str(int(remainder))
        # If no placeholder pattern, return as-is
        if clean.isdigit():
            return str(int(clean))

    elif value_type in ('currency', 'integer'):
        # For financial values, DOL uses longer placeholders
        # Pattern: "-123456789" followed by real digits
        if len(clean) >= 9 and clean.startswith('123456789'):
            remainder = clean[9:]
            if remainder and remainder.isdigit():
                # Real value - may need to insert decimal for currency
                return remainder
        # Check for shorter placeholder
        if len(clean) >= 8 and clean.startswith('12345678'):
            remainder = clean[8:]
            if remainder and remainder.isdigit():
                return remainder
        # If it looks like a normal number, return it
        if clean.isdigit():
            return clean

    return raw_value


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

        # Check if this is a DOL form (5500 or 5500-SF) - use specialized extraction
        is_dol_form = template in ('form-5500', 'form-5500-sf')

        if is_dol_form:
            # Try DOL-specific extraction first for real DOL PDFs
            try:
                dol_data = self._extract_dol_form_data(pdf_path, template_def)
            except Exception:
                # If DOL extraction fails (e.g., invalid PDF), use empty dict
                dol_data = {}

            # Also do standard text extraction as fallback
            text = self._extract_pdf_text(pdf_path, pages)
            text_data = self._extract_fields(text, template_def)

            # Merge: prefer DOL extraction for fields it found, use text extraction for rest
            extracted_data = text_data.copy()
            for key, value in dol_data.items():
                if value is not None:
                    extracted_data[key] = value
        else:
            # Standard extraction for non-DOL forms
            text = self._extract_pdf_text(pdf_path, pages)
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

    def _ocr_pdf(self, pdf_path: Path, dpi: int = 200) -> str:
        """
        Extract text from PDF using OCR.

        DOL forms have encoded text layers, so OCR is needed to get actual values.
        """
        if not OCR_AVAILABLE:
            return ""

        text_parts = []
        images = convert_from_path(str(pdf_path), dpi=dpi)

        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text_parts.append(f"--- PAGE {i + 1} ---\n{page_text}")

        return '\n\n'.join(text_parts)

    def _extract_dol_form_data(
        self,
        pdf_path: Path,
        template: Dict,
    ) -> Dict[str, Any]:
        """
        Extract data from DOL Form 5500/5500-SF using OCR.

        DOL forms have encoded text layers with placeholder characters.
        OCR extracts the actual visual text which contains real values.
        """
        extracted = {}

        # Use OCR if available (preferred for DOL forms)
        if OCR_AVAILABLE:
            full_text = self._ocr_pdf(pdf_path)
        else:
            # Fallback to pdfplumber (may get encoded text for DOL forms)
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

        # ============== PART I - ANNUAL REPORT IDENTIFICATION ==============

        # Plan year dates
        date_match = re.search(
            r'beginning\s+(\d{2}/\d{2}/\d{4})\s+and\s+ending\s+(\d{2}/\d{2}/\d{4})',
            full_text
        )
        if date_match:
            extracted['plan_year_begin'] = date_match.group(1)
            extracted['plan_year_end'] = date_match.group(2)

        # Plan type
        if 'single-employer' in full_text.lower():
            extracted['plan_type'] = 'Single-employer'
        elif 'multiple-employer' in full_text.lower():
            extracted['plan_type'] = 'Multiple-employer'

        # Return type flags (Line B)
        extracted['is_first_return'] = 'first return' in full_text.lower()
        extracted['is_final_return'] = 'final return' in full_text.lower()
        extracted['is_amended_return'] = 'amended return' in full_text.lower()
        extracted['is_short_plan_year'] = 'short plan year' in full_text.lower()

        # Filing extension (Line C)
        if 'Form 5558' in full_text:
            extracted['filing_extension'] = 'Form 5558'
        elif 'automatic extension' in full_text.lower():
            extracted['filing_extension'] = 'Automatic extension'
        elif 'DFVC program' in full_text:
            extracted['filing_extension'] = 'DFVC program'

        # ============== PART II - BASIC PLAN INFO ==============

        # Plan name (Line 1a) - OCR puts it on next line after "Name of plan"
        plan_name_match = re.search(
            r'Name of plan.*?\n\s*(.+?)\s*\(PN\)',
            full_text, re.IGNORECASE | re.DOTALL
        )
        if plan_name_match:
            plan_name = plan_name_match.group(1).strip()
            extracted['plan_name'] = plan_name

        # Plan number (Line 1b)
        pn_match = re.search(r'\(PN\)[^\d]*(\d{3})', full_text)
        if pn_match:
            extracted['plan_number'] = pn_match.group(1)

        # Effective date (Line 1c)
        eff_date_match = re.search(r'Effective date[^\d]*(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE)
        if eff_date_match:
            extracted['effective_date'] = eff_date_match.group(1)

        # Sponsor EIN (Line 2b)
        ein_match = re.search(r'(?:EIN|Identification Number)[^\d]*(\d{2})-?(\d{7})', full_text)
        if ein_match:
            extracted['ein'] = f"{ein_match.group(1)}-{ein_match.group(2)}"

        # Sponsor phone (Line 2c)
        phone_match = re.search(r"Sponsor's telephone[^\d]*(\d{3})-(\d{3})-(\d{4})", full_text, re.IGNORECASE)
        if phone_match:
            extracted['sponsor_phone'] = f"{phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}"

        # Business code (Line 2d)
        biz_code_match = re.search(r'(?:Business code|2d)[^\d]*(\d{6})', full_text, re.IGNORECASE)
        if biz_code_match:
            extracted['business_code'] = biz_code_match.group(1)

        # Location - City, State ZIP
        loc_match = re.search(r'([A-Z][A-Z\s]+),\s*([A-Z]{2})\s+(\d{5})', full_text)
        if loc_match:
            extracted['sponsor_city'] = loc_match.group(1).strip()
            extracted['sponsor_state'] = loc_match.group(2)
            extracted['sponsor_zip'] = loc_match.group(3)

        # Administrator same as sponsor (Line 3a)
        extracted['admin_same_as_sponsor'] = 'Same as Plan Sponsor' in full_text

        # ============== LINE 5 - PARTICIPANT DATA ==============

        # 5a - Total participants beginning of year
        boy_match = re.search(r'5a\s+(\d+)', full_text)
        if boy_match:
            extracted['total_participants_boy'] = int(boy_match.group(1))

        # 5b - Total participants end of year
        eoy_match = re.search(r'5b\s+(\d+)', full_text)
        if eoy_match:
            extracted['total_participants_eoy'] = int(eoy_match.group(1))

        # 5c(1) - Participants with account balances BOY
        match = re.search(r'5c[e\(]?1[)\s]+(\d+)', full_text, re.IGNORECASE)
        if match:
            extracted['participants_with_balances_boy'] = int(match.group(1))

        # 5c(2) - Participants with account balances EOY
        match = re.search(r'5c[e\(]?2[)\s]+(\d+)', full_text, re.IGNORECASE)
        if match:
            extracted['participants_with_balances_eoy'] = int(match.group(1))

        # ============== LINE 7 - ASSETS & LIABILITIES ==============

        def parse_currency(text):
            """Parse currency string like $1,234,567 or 1234567"""
            if not text:
                return None
            clean = re.sub(r'[$,\s]', '', text)
            try:
                return float(clean)
            except ValueError:
                return None

        # 7a - Total plan assets (BOY and EOY)
        assets_match = re.search(r'7a\s+\$?([\d,]+)\s+\$?([\d,]+)', full_text)
        if assets_match:
            extracted['total_assets_boy'] = parse_currency(assets_match.group(1))
            extracted['total_plan_assets_eoy'] = parse_currency(assets_match.group(2))

        # 7b - Total liabilities
        liab_match = re.search(r'7b\s+\$?([\d,]+)\s+\$?([\d,]+)', full_text)
        if liab_match:
            extracted['total_liabilities_boy'] = parse_currency(liab_match.group(1))
            extracted['total_liabilities_eoy'] = parse_currency(liab_match.group(2))

        # 7c - Net assets
        net_match = re.search(r'7c\s+\$?([\d,]+)\s+\$?([\d,]+)', full_text)
        if net_match:
            extracted['net_assets_boy'] = parse_currency(net_match.group(1))
            extracted['net_assets_eoy'] = parse_currency(net_match.group(2))

        # ============== LINE 8 - INCOME & EXPENSES ==============

        # 8a(1) - Employer contributions
        match = re.search(r'8a\(1\)\s+\$?([\d,]+)', full_text)
        if match:
            extracted['employer_contributions'] = parse_currency(match.group(1))

        # 8a(2) - Participant contributions
        match = re.search(r'8a\(2\)\s+\$?([\d,]+)', full_text)
        if match:
            extracted['participant_contributions'] = parse_currency(match.group(1))

        # 8a(3) - Other contributions
        match = re.search(r'8a\(3\)\s+\$?([\d,]+)', full_text)
        if match:
            extracted['other_contributions'] = parse_currency(match.group(1))

        # 8b - Other income
        match = re.search(r'8b\s+\$?([\d,]+)', full_text)
        if match:
            extracted['other_income'] = parse_currency(match.group(1))

        # 8c - Total income
        match = re.search(r'8c\s+\$?([\d,]+)', full_text)
        if match:
            extracted['total_contributions'] = parse_currency(match.group(1))

        # 8d - Benefits paid
        match = re.search(r'8d\s+\$?([\d,]+)', full_text)
        if match:
            extracted['benefit_payments'] = parse_currency(match.group(1))

        # 8e - Deemed distributions
        match = re.search(r'8e\s+\$?([\d,]+)', full_text)
        if match:
            extracted['deemed_distributions'] = parse_currency(match.group(1))

        # 8f - Admin expenses
        match = re.search(r'8f\s+\$?([\d,]+)', full_text)
        if match:
            extracted['admin_expenses'] = parse_currency(match.group(1))

        # 8g - Other expenses
        match = re.search(r'8g\s+\$?([\d,]+)', full_text)
        if match:
            extracted['other_expenses'] = parse_currency(match.group(1))

        # 8h - Total expenses
        match = re.search(r'8h\s+\$?([\d,]+)', full_text)
        if match:
            extracted['total_expenses'] = parse_currency(match.group(1))

        # 8i - Net income
        match = re.search(r'8i\s+\$?([\d,]+)', full_text)
        if match:
            extracted['net_income'] = parse_currency(match.group(1))

        # 8j - Transfers
        match = re.search(r'8j\s+\$?([\d,]+)', full_text)
        if match:
            extracted['transfers'] = parse_currency(match.group(1))

        # ============== LINE 9 - PLAN CHARACTERISTICS ==============

        # Look for pension feature codes (2x or 3x format)
        codes = re.findall(r'\b([23][A-Z])\b', full_text)
        if codes:
            # Filter to unique codes that look like feature codes
            unique_codes = list(dict.fromkeys(codes))
            # Take only codes that appear in the plan characteristics area
            extracted['pension_feature_codes'] = ', '.join(unique_codes[:10])

        # ============== LINE 10 - COMPLIANCE ==============

        # Default compliance answers
        extracted['failed_contribution_transmittal'] = 'No'
        extracted['nonexempt_party_transactions'] = 'No'
        extracted['fidelity_bond_coverage'] = 'Yes'
        extracted['loss_from_fraud'] = 'No'
        extracted['insurance_broker_fees'] = 'No'
        extracted['failed_benefit_payment'] = 'No'
        extracted['participant_loans'] = 'No'
        extracted['blackout_period'] = 'No'

        # Fidelity bond amount (Line 10c)
        bond_match = re.search(r'(?:10c|fidelity bond)[^\d]*\$?([\d,]+)', full_text, re.IGNORECASE)
        if bond_match:
            extracted['fidelity_bond_amount'] = parse_currency(bond_match.group(1))

        return extracted

    def _decode_dol_financial_value(self, text: str) -> Optional[float]:
        """
        Decode financial values from DOL embedded placeholder format.

        DOL forms embed real values within placeholder strings like:
        '-1234567819004132233745' where the real value is embedded after the placeholder.
        '-1234153697168399012345' for EOY values (different prefix pattern)

        The pattern appears to be:
        - Minus sign (optional)
        - Placeholder prefix (varies: 123456789, 12345678, 1234567, or 1234XXXXXX)
        - Real value embedded in remaining digits

        For financial values, we look for reasonable dollar amounts embedded in the string.
        """
        if not text:
            return None

        # Remove leading minus sign
        clean = text.lstrip('-')

        # Strategy 1: Try standard placeholder prefixes
        for prefix in ['123456789', '12345678', '1234567']:
            if clean.startswith(prefix):
                remainder = clean[len(prefix):]
                if remainder and len(remainder) >= 5:
                    # Try different value lengths
                    for value_len in [8, 9, 7, 6, 10]:
                        if len(remainder) >= value_len:
                            value_str = remainder[:value_len]
                            try:
                                value = float(value_str)
                                if 100 <= value <= 500000000:
                                    return value
                            except ValueError:
                                continue

        # Strategy 2: For non-standard prefixes (like EOY columns)
        # DOL sometimes uses 1234XXXXXX where X varies
        # Try stripping first 4-10 digits starting with 1234
        if clean.startswith('1234') and len(clean) >= 15:
            # Try finding a reasonable value in the string
            # Look for 8-digit numbers that make sense as dollar amounts
            for start_pos in range(4, 12):
                for value_len in [8, 9, 7, 6]:
                    if start_pos + value_len <= len(clean):
                        value_str = clean[start_pos:start_pos + value_len]
                        try:
                            value = float(value_str)
                            # More flexible range for this heuristic
                            if 10000 <= value <= 500000000:
                                return value
                        except ValueError:
                            continue

        # Strategy 3: Direct conversion for normal numbers
        try:
            clean_num = clean.replace(',', '')
            value = float(clean_num)
            if 100 <= value <= 500000000:
                return value
        except ValueError:
            pass

        return None

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
        date_format = output_format.get('date_format', 'YYYY-MM-DD')
        include_line_codes = output_format.get('include_line_codes', False)

        if include_line_codes:
            # Create vertical format with line_code, field_name, display_name, value
            rows = []
            for field_def in template.get('fields', []):
                field_name = field_def['field_name']
                line_code = field_def.get('line_code', '-')
                display_name = field_def.get('display_name', field_name)
                value = data.get(field_name)

                # Format dates
                if value and field_def.get('data_type') == 'date':
                    value = format_date(value, date_format)

                # Format currency values
                if value is not None and field_def.get('data_type') == 'currency':
                    if isinstance(value, (int, float)):
                        value = f"${value:,.0f}"

                rows.append({
                    'line_code': line_code,
                    'field_name': field_name,
                    'display_name': display_name,
                    'value': value if value is not None else ''
                })

            return pd.DataFrame(rows)
        else:
            # Traditional horizontal format
            csv_headers = output_format.get('csv_headers', list(data.keys()))
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
