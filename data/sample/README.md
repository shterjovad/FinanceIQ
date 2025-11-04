# Sample Test Documents

This directory contains test documents for validating the FinanceIQ PDF processing pipeline.

## Test Files

- `test-valid.pdf`: A simple valid PDF for testing successful uploads
- `test-invalid.txt`: A non-PDF file for testing type validation

## Real Financial Documents

For complete testing, download real financial documents:

1. **10-K Report**: Download from SEC EDGAR
   - Tesla 10-K: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605&type=10-K
   - Apple 10-K: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K

2. **Earnings Report**: Download from company investor relations pages
   - Tesla: https://ir.tesla.com/
   - Apple: https://investor.apple.com/

Save downloaded PDFs to this directory for testing.

## Testing Scenarios

See `context/spec/001-pdf-upload-text-extraction/tasks.md` (Slice 10) for the complete test plan.
