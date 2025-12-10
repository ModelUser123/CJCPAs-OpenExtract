# Contributing to OpenExtract

Thank you for your interest in contributing! OpenExtract thrives on community contributions, especially new templates for different document types.

## Ways to Contribute

1. **Add new templates** - The most valuable contribution!
2. **Improve existing templates** - Better regex patterns, more fields
3. **Report bugs** - Help us fix issues
4. **Improve documentation** - Make it easier for others

---

## Adding a New Template

### Step 1: Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/CJCPAs-OpenExtract.git
cd CJCPAs-OpenExtract
```

### Step 2: Create Your Template

1. Find the appropriate category folder in `templates/`:
   - `401k/` - Retirement plan documents
   - `tax-forms/` - IRS tax forms
   - `invoices/` - Invoices and bills
   - `bank-statements/` - Bank statements
   - Create a new folder if needed

2. Copy the example template:
   ```bash
   cp templates/_example.json templates/YOUR_CATEGORY/your-template.json
   ```

3. Edit the template with your document's fields

### Step 3: Template Structure

Every template must include:

```json
{
  "template_id": "your-template-id",
  "template_name": "Human Readable Name",
  "description": "What this template extracts",
  "document_type": "tax-form|invoice|bank-statement|retirement-plan|other",
  "version": "1.0.0",
  "author": "Your Name",
  "tags": ["searchable", "tags"],
  "fields": [...],
  "output_format": {
    "csv_headers": [...],
    "date_format": "YYYY-MM-DD"
  }
}
```

### Step 4: Define Fields

Each field needs:

```json
{
  "field_name": "snake_case_name",
  "display_name": "Human Readable Name",
  "data_type": "string|integer|currency|date|boolean|percentage",
  "required": true,
  "extraction_method": "regex",
  "regex_pattern": "your regex with (capture group)",
  "fallback_patterns": ["alternative", "patterns"],
  "section": "Document Section Name"
}
```

### Step 5: Writing Good Regex Patterns

**Tips:**
- Use capturing groups `()` for the value you want to extract
- Make patterns flexible to handle variations
- Test with multiple real documents
- Use `(?:...)` for non-capturing groups

**Example patterns:**

```regex
# EIN (various formats)
(?:EIN|Employer\s+(?:Identification|ID)\s+(?:Number|No\.?))[:\s]*(\d{2}[- ]?\d{7})

# Currency amounts
(?:Total|Amount)[:\s]*\$?([\d,]+(?:\.\d{2})?)

# Dates
(?:Date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})
```

### Step 6: Test Your Template

```bash
# Install test dependencies
pip install pytest

# Run template validation tests
pytest tests/test_templates.py -v

# Test with a real PDF
python -c "
from src.openextract import Extractor
e = Extractor()
result = e.extract('your-test.pdf', template='your-template-id')
print(result)
"
```

### Step 7: Submit a Pull Request

1. Commit your changes:
   ```bash
   git add templates/YOUR_CATEGORY/your-template.json
   git commit -m "Add template for [Document Type]"
   ```

2. Push to your fork:
   ```bash
   git push origin main
   ```

3. Open a Pull Request with:
   - Description of what the template extracts
   - List of fields included
   - Any known limitations

---

## Template Best Practices

### DO:
- Use descriptive `field_name` values
- Include `fallback_patterns` for variations
- Add helpful `section` labels
- Test with multiple real documents
- Document any assumptions

### DON'T:
- Include sensitive test data
- Make regex patterns too specific
- Skip required fields in the schema
- Forget to update `csv_headers`

---

## Code Style

- Python: Follow PEP 8
- JSON: 2-space indentation
- Keep templates readable and well-commented

---

## Questions?

Open an issue with the "question" label and we'll help!
