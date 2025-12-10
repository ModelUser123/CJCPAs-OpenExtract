# OpenExtract

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ModelUser123/CJCPAs-OpenExtract/blob/main/notebooks/OpenExtract_Quickstart.ipynb)
[![Tests](https://github.com/ModelUser123/CJCPAs-OpenExtract/workflows/Tests/badge.svg)](https://github.com/ModelUser123/CJCPAs-OpenExtract/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**PDF Data Extraction for Accountants** - Extract structured data from tax forms, 401(k) documents, invoices, and more. No coding required!

OpenExtract is an open-source tool that lets accountants upload PDFs, pick a template, and get structured CSV data back. Templates are community-contributed JSON files that define what fields to extract from each document type.

---

## Quick Start (Google Colab)

**No installation required!** Just click the button below:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ModelUser123/CJCPAs-OpenExtract/blob/main/notebooks/OpenExtract_Quickstart.ipynb)

### 5 Steps to Extract Data:

1. **Click the Colab button** above to open the notebook
2. **Run the Setup cell** to install dependencies
3. **Upload your PDF** using the upload widget
4. **Pick a template** (e.g., `form-5500`, `1099-nec`)
5. **Download your CSV** with extracted data!

---

## Available Templates

| Category | Template ID | Description |
|----------|-------------|-------------|
| **401(k)** | `form-5500` | DOL/IRS Form 5500 (large plans) |
| **401(k)** | `form-5500-sf` | Form 5500-SF (small plans) |
| **401(k)** | `schedule-h` | Schedule H - Financial Information |
| **401(k)** | `schedule-c` | Schedule C - Service Provider Info |
| **401(k)** | `participant-statement` | 401(k) Participant Statement |
| **Tax** | `1099-misc` | IRS 1099-MISC |
| **Tax** | `1099-nec` | IRS 1099-NEC |
| **Tax** | `1099-int` | IRS 1099-INT |
| **Tax** | `k1-1065` | Schedule K-1 (Form 1065) |
| **Invoice** | `generic-invoice` | Generic Invoice/Bill |
| **Bank** | `generic-bank-statement` | Bank Account Statement |

---

## Local Installation

For power users who want to run OpenExtract locally:

```bash
# Clone the repository
git clone https://github.com/ModelUser123/CJCPAs-OpenExtract.git
cd CJCPAs-OpenExtract

# Install dependencies
pip install -r requirements.txt

# Run Python
python
```

```python
from src.openextract import Extractor

extractor = Extractor()
extractor.list_templates()

results = extractor.extract("path/to/form5500.pdf", template="form-5500")
results.to_csv("extracted_data.csv", index=False)
```

---

## How It Works

1. **PDF Processing**: OpenExtract uses [pdfplumber](https://github.com/jsvine/pdfplumber) to extract text from PDFs
2. **Template Matching**: Templates define regex patterns and extraction rules for each field
3. **Data Extraction**: Fields are extracted using pattern matching
4. **Output**: Results are returned as a pandas DataFrame (easily exported to CSV)

---

## Contributing Templates

We welcome new templates! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Quick version:**

1. Fork this repository
2. Copy `templates/_example.json` as your starting point
3. Define fields with regex patterns
4. Test your template
5. Submit a Pull Request

---

## Project Structure

```
openextract/
├── templates/           # Extraction templates (JSON)
│   ├── 401k/           # 401(k) and retirement documents
│   ├── tax-forms/      # IRS tax forms
│   ├── invoices/       # Invoices and bills
│   └── bank-statements/# Bank statements
├── src/openextract/    # Python source code
│   ├── extractor.py    # Main extraction logic
│   ├── template_loader.py
│   └── utils.py        # Utility functions
├── tests/              # Test suite
├── notebooks/          # Jupyter notebooks
└── .github/workflows/  # CI/CD
```

---

## Requirements

- Python 3.9+
- pdfplumber >= 0.10.0
- pandas >= 2.0.0

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ModelUser123/CJCPAs-OpenExtract/issues)
- **Template Requests**: Use the [Template Request](https://github.com/ModelUser123/CJCPAs-OpenExtract/issues/new?template=template-request.md) issue template

---

Made with love for accountants everywhere!
