## Overview

Removed unused `fpdf`-based PDF generation code and stopped requiring the `fpdf` dependency.

### Description

The codebase defined `create_pdf()` in `pdf_generator.py` using `fpdf`, but the function/module is not used by the application. `app.py` already generates PDFs using `reportlab` in `make_pdf()`. This change removes dead `fpdf` code paths and prevents users from having to install an extra heavyweight PDF library.

### Files touched:

- `requirements.txt` — removed `fpdf>=1.7.2`
- `pdf_generator.py` — removed/disabled the `fpdf` implementation (kept a clear error if `create_pdf()` is called)

### Core Motivation

Keeping both `reportlab` and `fpdf` unnecessarily increases installation size and dependency footprint. Since `create_pdf()` is unused, `fpdf` is dead weight.

### Proposed Changes

1. `requirements.txt`: delete `fpdf>=1.7.2` since PDF generation is performed via `reportlab`.
2. `pdf_generator.py`: disable the `fpdf`-based `create_pdf()` entrypoint to reflect that it is unused by the app.

### How Has This Been Tested?

- `python -m py_compile app.py pdf_generator.py` (ensured syntax correctness)

## Checklist

- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my own code
- [x] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [x] Submitting AI-generated code without review is strictly prohibited (`gssoc:spam`)
