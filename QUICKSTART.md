# OpenExtract Quickstart Guide

Get up and running in 5 minutes!

---

## Option 1: Google Colab (Recommended)

**No installation required!**

1. Click: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ModelUser123/CJCPAs-OpenExtract/blob/main/notebooks/OpenExtract_Quickstart.ipynb)

2. Run each cell in order:
   - **Setup** - Installs dependencies
   - **Upload** - Select your PDF
   - **List Templates** - See available templates
   - **Extract** - Get your data
   - **Download** - Save as CSV

That's it!

---

## Option 2: Local Installation

### Prerequisites
- Python 3.9 or higher
- pip

### Install

```bash
# Clone repository
git clone https://github.com/ModelUser123/CJCPAs-OpenExtract.git
cd CJCPAs-OpenExtract

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from src.openextract import Extractor

# Create extractor
extractor = Extractor()

# See available templates
extractor.list_templates()

# Extract data from a PDF
results = extractor.extract("form5500.pdf", template="form-5500")

# View results
print(results)

# Save to CSV
results.to_csv("extracted_data.csv", index=False)
```

---

## Common Templates

### 401(k) / Retirement

```python
# Form 5500 (large plans - 100+ participants)
results = extractor.extract("form5500.pdf", template="form-5500")

# Form 5500-SF (small plans)
results = extractor.extract("form5500sf.pdf", template="form-5500-sf")

# Participant statements
results = extractor.extract("statement.pdf", template="participant-statement")
```

### Tax Forms

```python
# 1099-MISC
results = extractor.extract("1099misc.pdf", template="1099-misc")

# 1099-NEC
results = extractor.extract("1099nec.pdf", template="1099-nec")

# 1099-INT
results = extractor.extract("1099int.pdf", template="1099-int")

# Schedule K-1
results = extractor.extract("k1.pdf", template="k1-1065")
```

### Invoices & Bank Statements

```python
# Invoice
results = extractor.extract("invoice.pdf", template="generic-invoice")

# Bank statement
results = extractor.extract("statement.pdf", template="generic-bank-statement")
```

---

## Batch Processing

Process multiple PDFs at once:

```python
from pathlib import Path

# Get all PDFs in a folder
pdf_files = list(Path("pdfs/").glob("*.pdf"))

# Process all with same template
all_results = extractor.extract_batch(pdf_files, template="form-5500")

# Save combined results
all_results.to_csv("all_forms.csv", index=False)
```

---

## Validation

Check if extraction was successful:

```python
results = extractor.extract("form5500.pdf", template="form-5500")
validation = extractor.validate_extraction(results, "form-5500")

print(f"Valid: {validation['valid']}")
print(f"Errors: {validation['errors']}")
print(f"Warnings: {validation['warnings']}")
print(f"Fields extracted: {validation['fields_extracted']}/{validation['fields_total']}")
```

---

## Troubleshooting

### "Template not found"
- Run `extractor.list_templates()` to see available templates
- Check spelling (templates use lowercase with hyphens)

### "No data extracted"
- Verify the PDF is text-based (not scanned image)
- Check that you're using the right template for your document

### "Missing required fields"
- Some PDFs may have variations in format
- Open an issue if a template consistently fails

---

## Next Steps

- Browse all templates in the `templates/` folder
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to add new templates
- Check the [README](README.md) for full documentation

---

Happy extracting!
