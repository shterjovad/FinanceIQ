# Slice 10: Manual Testing Plan

This document outlines the manual testing plan for validating the FinanceIQ PDF processing pipeline with real-world documents.

## Test Environment

- **Application**: FinanceIQ Phase 1 (PDF Upload & Text Extraction)
- **Branch**: feature/slice-10-testing
- **Python Version**: 3.12+
- **Date**: November 4, 2025

## Prerequisites

1. Application is running: `./run.sh` or `PYTHONPATH=. uv run streamlit run src/ui/app.py`
2. Browser open at: `http://localhost:8501`
3. Test documents prepared in `data/sample/`

## Test Documents Needed

### Real Financial Documents (Download Required)
1. **10-K Report** - Large, complex financial document
   - Recommended: Tesla 10-K or Apple 10-K from SEC EDGAR
   - Expected: 100+ pages, several MB

2. **Earnings Report** - Shorter quarterly report
   - Recommended: Any company's quarterly earnings from investor relations page
   - Expected: 20-50 pages

### Error Scenario Documents
3. **Non-PDF File** - For type validation
   - Use: `test-invalid.txt` (already created)

4. **Large File** - For size validation (>50MB)
   - Create or find a PDF larger than 50MB

5. **Password-Protected PDF** (optional)
   - If available, for encryption detection testing

## Test Cases

### Test 1: Upload Valid 10-K Report
**Objective**: Verify successful processing of large financial document

**Steps**:
1. Upload a 10-K PDF (e.g., Tesla or Apple)
2. Observe progress bar (validation → extraction → complete)
3. Wait for processing to complete

**Expected Results**:
- ✅ Success message: "Document uploaded successfully! [filename] is ready for analysis..."
- ✅ Metadata displayed:
  - Pages: 100+ pages
  - Size: Actual file size in MB
  - Characters: Large number (50,000+)
  - Processing Time: < 30 seconds for typical 10-K
- ✅ Text preview shows first 1000 characters
- ✅ Preview text is readable and matches document content

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 2: Upload Earnings Report
**Objective**: Verify metadata accuracy with shorter document

**Steps**:
1. Upload an earnings report PDF
2. Wait for processing

**Expected Results**:
- ✅ Success message displayed
- ✅ Metadata accurate:
  - Page count matches actual pages
  - File size is correct
  - Character count is reasonable
- ✅ Processing time is fast (< 10 seconds)

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 3: Upload File > 50MB
**Objective**: Verify file size validation

**Steps**:
1. Attempt to upload a PDF larger than 50MB
2. Observe error handling

**Expected Results**:
- ✅ Error message: "File size exceeds 50MB limit. Please upload a smaller document."
- ✅ No crash or unexpected behavior
- ✅ User can upload another file immediately

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 4: Upload Non-PDF File
**Objective**: Verify file type validation

**Steps**:
1. Attempt to upload `test-invalid.txt`
2. Observe error handling

**Expected Results**:
- ✅ Error message: "Only PDF files are supported. Please upload a .pdf file."
- ✅ File is rejected cleanly

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 5: Upload Password-Protected PDF (Optional)
**Objective**: Verify encryption detection

**Steps**:
1. Upload a password-protected PDF (if available)
2. Observe error handling

**Expected Results**:
- ✅ Error message: "This PDF is password-protected. Please upload an unprotected version."

**Pass/Fail**: _____ (N/A if no password-protected PDF available)

**Notes**: _______________________________________________

---

### Test 6: Upload Multiple Files
**Objective**: Verify multi-file upload handling

**Steps**:
1. Select and upload 2-3 PDFs simultaneously
2. Observe processing

**Expected Results**:
- ✅ Each file shows its own progress bar
- ✅ Files are processed sequentially
- ✅ Each file shows separate results
- ✅ Visual separators between files
- ✅ All files process successfully

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 7: Verify File Storage Structure
**Objective**: Validate files are saved correctly

**Steps**:
1. After uploading files, check `data/uploads/` directory
2. Verify date-based organization

**Expected Results**:
- ✅ Structure: `data/uploads/YYYY/MM/DD/filename.pdf`
- ✅ Today's date matches directory structure
- ✅ Uploaded files are present
- ✅ Filename collision handling works (if same file uploaded twice)

**Command to check**:
```bash
ls -R data/uploads/
```

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

### Test 8: Verify Logging
**Objective**: Validate structured logging

**Steps**:
1. After testing, check logs/financeiq.log
2. Review log entries

**Expected Results**:
- ✅ Log file exists: `logs/financeiq.log`
- ✅ Contains entries for each upload
- ✅ Shows validation, extraction, storage steps
- ✅ Includes file names and processing results
- ✅ No sensitive data in logs

**Command to check**:
```bash
tail -50 logs/financeiq.log
```

**Pass/Fail**: _____

**Notes**: _______________________________________________

---

## Test Summary

| Test # | Test Name | Pass/Fail | Notes |
|--------|-----------|-----------|-------|
| 1 | Valid 10-K Upload | _____ | _____ |
| 2 | Earnings Report | _____ | _____ |
| 3 | File Size Validation | _____ | _____ |
| 4 | File Type Validation | _____ | _____ |
| 5 | Password-Protected PDF | _____ | _____ |
| 6 | Multi-file Upload | _____ | _____ |
| 7 | File Storage Structure | _____ | _____ |
| 8 | Logging Verification | _____ | _____ |

**Overall Result**: _______ (All Pass / Issues Found)

## Issues Found

Document any issues discovered during testing:

1. ________________________________________________________________

2. ________________________________________________________________

3. ________________________________________________________________

## Recommendations

Based on testing results:

- ________________________________________________________________

- ________________________________________________________________

## Sign-off

**Tester**: _____________________
**Date**: _____________________
**Version Tested**: Phase 1 - Slice 10
