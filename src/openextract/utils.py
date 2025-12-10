"""
Utility functions for OpenExtract PDF data extraction.
"""

import re
from datetime import datetime
from typing import Any, Optional


def parse_currency(value: str) -> Optional[float]:
    """
    Parse a currency string into a float value.

    Args:
        value: String containing currency value (e.g., "$1,234.56", "1234.56")

    Returns:
        Float value or None if parsing fails
    """
    if not value:
        return None

    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[$£€¥,\s]', '', str(value))

    # Handle negative values in parentheses
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_integer(value: str) -> Optional[int]:
    """
    Parse a string into an integer value.

    Args:
        value: String containing integer value (e.g., "1,234", "1234")

    Returns:
        Integer value or None if parsing fails
    """
    if not value:
        return None

    # Remove commas and whitespace
    cleaned = re.sub(r'[,\s]', '', str(value))

    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def parse_percentage(value: str) -> Optional[float]:
    """
    Parse a percentage string into a float value.

    Args:
        value: String containing percentage (e.g., "12.5%", "12.5")

    Returns:
        Float value (as percentage, not decimal) or None if parsing fails
    """
    if not value:
        return None

    # Remove % sign and whitespace
    cleaned = re.sub(r'[%\s]', '', str(value))

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_date(value: str, input_formats: Optional[list] = None) -> Optional[str]:
    """
    Parse a date string and return in ISO format (YYYY-MM-DD).

    Args:
        value: String containing date
        input_formats: List of strptime format strings to try

    Returns:
        Date string in YYYY-MM-DD format or None if parsing fails
    """
    if not value:
        return None

    if input_formats is None:
        input_formats = [
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%m/%d/%y',
            '%m-%d-%y',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
        ]

    cleaned = str(value).strip()

    for fmt in input_formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def format_date(date_str: str, output_format: str = 'YYYY-MM-DD') -> Optional[str]:
    """
    Format a date string to the specified output format.

    Args:
        date_str: Date string in YYYY-MM-DD format
        output_format: Desired output format string

    Returns:
        Formatted date string or None if formatting fails
    """
    if not date_str:
        return None

    # Map common format strings to strftime format
    format_map = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'YYYY/MM/DD': '%Y/%m/%d',
        'MM-DD-YYYY': '%m-%d-%Y',
        'DD-MM-YYYY': '%d-%m-%Y',
    }

    strftime_format = format_map.get(output_format, '%Y-%m-%d')

    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime(strftime_format)
    except ValueError:
        return date_str


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text string
    """
    if not text:
        return ''

    # Replace multiple whitespace with single space
    cleaned = re.sub(r'\s+', ' ', str(text))

    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


def normalize_ein(ein: str) -> Optional[str]:
    """
    Normalize an EIN to XX-XXXXXXX format.

    Args:
        ein: EIN string in various formats

    Returns:
        Normalized EIN string or None if invalid
    """
    if not ein:
        return None

    # Remove all non-digits
    digits = re.sub(r'\D', '', str(ein))

    if len(digits) != 9:
        return None

    return f"{digits[:2]}-{digits[2:]}"


def normalize_ssn(ssn: str) -> Optional[str]:
    """
    Normalize an SSN to XXX-XX-XXXX format.

    Args:
        ssn: SSN string in various formats

    Returns:
        Normalized SSN string or None if invalid
    """
    if not ssn:
        return None

    # Remove all non-digits
    digits = re.sub(r'\D', '', str(ssn))

    if len(digits) != 9:
        return None

    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def validate_value(value: Any, validation_pattern: str) -> bool:
    """
    Validate a value against a regex pattern.

    Args:
        value: Value to validate
        validation_pattern: Regex pattern for validation

    Returns:
        True if valid, False otherwise
    """
    if value is None:
        return False

    try:
        return bool(re.match(validation_pattern, str(value)))
    except re.error:
        return False


def extract_first_match(text: str, pattern: str, group: int = 1) -> Optional[str]:
    """
    Extract the first regex match from text.

    Args:
        text: Text to search
        pattern: Regex pattern with capturing groups
        group: Which capturing group to return (default: 1)

    Returns:
        Matched string or None if no match
    """
    if not text or not pattern:
        return None

    try:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match and group <= len(match.groups()):
            return match.group(group)
    except re.error:
        pass

    return None


def coerce_value(value: str, data_type: str) -> Any:
    """
    Coerce an extracted string value to the specified data type.

    Args:
        value: Extracted string value
        data_type: Target data type (string, integer, currency, date, boolean, decimal, percentage)

    Returns:
        Coerced value of appropriate type
    """
    if value is None:
        return None

    if data_type == 'string':
        return clean_text(value)
    elif data_type == 'integer':
        return parse_integer(value)
    elif data_type == 'currency':
        return parse_currency(value)
    elif data_type == 'decimal':
        return parse_currency(value)  # Same parsing logic
    elif data_type == 'percentage':
        return parse_percentage(value)
    elif data_type == 'date':
        return parse_date(value)
    elif data_type == 'boolean':
        return str(value).lower() in ('true', 'yes', '1', 'x', 'checked')
    else:
        return clean_text(value)
