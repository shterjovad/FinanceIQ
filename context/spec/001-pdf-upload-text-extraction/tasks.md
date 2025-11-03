# Task List: PDF Upload & Text Extraction

**Spec:** `context/spec/001-pdf-upload-text-extraction`

**Principle:** Each major task represents a runnable increment - the application can be started and tested after completing that task.

---

## Slice 1: Project Bootstrap & Minimal Streamlit App

**Goal:** Set up the project foundation and get a basic Streamlit app running

- [x] **Initialize uv project and create basic structure**
  - [x] Run `uv init` to initialize project
  - [x] Create `pyproject.toml` with dependencies (streamlit, pypdf, pydantic, pydantic-settings, python-dotenv)
  - [x] Create directory structure: `src/`, `src/pdf_processor/`, `src/ui/components/`, `src/config/`, `data/uploads/`, `logs/`
  - [x] Create all `__init__.py` files in appropriate directories
  - [x] Create `.env.example` with configuration template
  - [x] Create `.env` file (gitignored)
  - [x] Run `uv sync` to install dependencies

- [x] **Create minimal Streamlit app that runs**
  - [x] Create `src/ui/app.py` with basic Streamlit page structure
  - [x] Add title: "FinanceIQ - Financial Document Analysis"
  - [x] Add placeholder text: "Upload financial documents to begin"
  - [x] Test: Run `streamlit run src/ui/app.py` and verify app loads

**After Slice 1:** You have a working Streamlit app that displays a welcome page ✅

---

## Slice 2: Configuration & Logging Setup

**Goal:** Add configuration management and logging infrastructure

- [ ] **Implement Pydantic Settings for configuration**
  - [ ] Create `src/config/settings.py` with `Settings` class
  - [ ] Add settings: `MAX_FILE_SIZE_MB`, `ALLOWED_MIME_TYPES`, `UPLOAD_DIR`, `LOG_LEVEL`, `LOG_DIR`
  - [ ] Create directories in `__init__` method
  - [ ] Create global `settings` instance

- [ ] **Set up logging infrastructure**
  - [ ] Create `setup_logging()` function in `src/pdf_processor/__init__.py`
  - [ ] Configure console handler (INFO level)
  - [ ] Configure file handler (DEBUG level, logs to `logs/financeiq.log`)
  - [ ] Call `setup_logging()` on package import
  - [ ] Test: Import settings and verify directories are created, check log file is created

**After Slice 2:** You have type-safe configuration and structured logging ready ✅

---

## Slice 3: Data Models & Exceptions

**Goal:** Define all Pydantic models and custom exceptions (foundation for type safety)

- [ ] **Create Pydantic data models**
  - [ ] Create `src/pdf_processor/models.py`
  - [ ] Implement `FileValidationStatus` enum (VALID, INVALID_SIZE, INVALID_TYPE, PASSWORD_PROTECTED, CORRUPTED, NO_TEXT)
  - [ ] Implement `UploadedFile` model with `size_mb` and `extension` properties
  - [ ] Implement `FileValidationResult` model
  - [ ] Implement `DocumentMetadata` model with field validators
  - [ ] Implement `ExtractedDocument` model with `document_id` property
  - [ ] Implement `ProcessingResult` model

- [ ] **Create custom exception hierarchy**
  - [ ] Create `src/pdf_processor/exceptions.py`
  - [ ] Implement `PDFProcessingError` base exception
  - [ ] Implement `FileSizeExceededError` with size details
  - [ ] Implement `InvalidFileTypeError`
  - [ ] Implement `PasswordProtectedPDFError`
  - [ ] Implement `CorruptedPDFError`
  - [ ] Implement `NoTextContentError`
  - [ ] Test: Import models and exceptions, create sample instances, verify validation works

**After Slice 3:** You have type-safe data structures and domain exceptions ready ✅

---

## Slice 4: File Validation with Mock UI

**Goal:** Implement file validation and display validation results in Streamlit

- [ ] **Implement PDF validation logic**
  - [ ] Create `src/pdf_processor/validators.py`
  - [ ] Implement `PDFValidator` class with `__init__` accepting `max_size_mb`
  - [ ] Implement `validate_file()` method that calls private validation methods
  - [ ] Implement `_validate_size()` method (raises `FileSizeExceededError`)
  - [ ] Implement `_validate_type()` method (checks extension and MIME type, raises `InvalidFileTypeError`)
  - [ ] Implement `_validate_pdf_structure()` method (uses pypdf `PdfReader`, checks encryption, raises `PasswordProtectedPDFError` or `CorruptedPDFError`)
  - [ ] Add comprehensive error handling and logging

- [ ] **Create basic file upload UI component**
  - [ ] Create `src/ui/components/upload.py`
  - [ ] Implement `PDFUploadComponent` class with `__init__` (no service yet)
  - [ ] Implement `render()` method with `st.file_uploader()`
  - [ ] When file is uploaded, convert to `UploadedFile` model
  - [ ] Create a `PDFValidator` instance and call `validate_file()`
  - [ ] Display validation result (success or error message from functional spec)
  - [ ] Update `src/ui/app.py` to import and render `PDFUploadComponent`
  - [ ] Test: Run Streamlit, upload various files (valid PDF, non-PDF, large file), verify error messages appear correctly

**After Slice 4:** You can upload files and see validation results with proper error messages ✅

---

## Slice 5: Text Extraction

**Goal:** Add PDF text extraction capability and display extracted text preview

- [ ] **Implement PDF text extraction logic**
  - [ ] Create `src/pdf_processor/extractors.py`
  - [ ] Implement `PDFTextExtractor` class with `__init__` accepting `min_text_length`
  - [ ] Implement `extract_text()` method:
    - Open PDF with `PdfReader(BytesIO(file.content))`
    - Iterate through pages and extract text
    - Concatenate with `\n\n` separator
    - Validate minimum text length
    - Raise `NoTextContentError` if insufficient text
    - Add logging for success and page-level failures
  - [ ] Implement `extract_metadata()` method:
    - Extract page count, file size, text length
    - Return `DocumentMetadata` model

- [ ] **Update UI to show extracted text preview**
  - [ ] After successful validation in `upload.py`, create `PDFTextExtractor` instance
  - [ ] Call `extract_text()` and handle `NoTextContentError`
  - [ ] Display success message: "Text extraction successful!"
  - [ ] Show text preview in expander (first 1000 characters)
  - [ ] Display basic metrics: page count (from pypdf), text length
  - [ ] Test: Upload valid PDF, verify text is extracted and preview is shown; upload scanned PDF, verify "no text" error

**After Slice 5:** You can extract and preview text from uploaded PDFs ✅

---

## Slice 6: File Storage

**Goal:** Save uploaded PDFs to disk with organized structure

- [ ] **Implement file storage management**
  - [ ] Create `src/pdf_processor/storage.py`
  - [ ] Implement `FileStorageManager` class with `__init__` accepting `base_dir`
  - [ ] Implement `save_file()` method:
    - Create date-based path using `_get_date_path()` helper
    - Generate unique filename using `_generate_unique_path()` helper (timestamp suffix for collisions)
    - Write file with `Path.write_bytes()`
    - Add logging
    - Handle IOError exceptions
  - [ ] Implement `_get_date_path()` helper (returns `YYYY/MM/DD` path)
  - [ ] Implement `_generate_unique_path()` helper (handles filename collisions)

- [ ] **Update UI to save files and display file path**
  - [ ] After successful text extraction in `upload.py`, create `FileStorageManager` instance
  - [ ] Call `save_file()` and get file path
  - [ ] Display success message with file location
  - [ ] Test: Upload PDF, verify file is saved to `data/uploads/YYYY/MM/DD/filename.pdf`, upload same file twice, verify collision handling works

**After Slice 6:** You can upload PDFs, extract text, and save them to disk ✅

---

## Slice 7: Service Orchestration Layer

**Goal:** Consolidate all processing steps into a service with proper error handling

- [ ] **Implement PDF processing service**
  - [ ] Create `src/pdf_processor/service.py`
  - [ ] Implement `PDFProcessingService` class with `__init__` accepting validator, extractor, storage_manager (dependency injection)
  - [ ] Implement `process_upload()` method:
    - Measure processing time
    - Step 1: Validate file (return failed `ProcessingResult` if invalid)
    - Step 2: Extract text (catch exceptions, convert to failed `ProcessingResult`)
    - Step 3: Save file (catch exceptions)
    - Step 4: Extract metadata
    - Step 5: Create `ExtractedDocument` and wrap in successful `ProcessingResult`
    - Comprehensive try-except with logging

- [ ] **Refactor UI to use service**
  - [ ] Update `PDFUploadComponent.__init__` to accept/create `PDFProcessingService`
  - [ ] Refactor `render()` to call `service.process_upload()` instead of individual components
  - [ ] Display `ProcessingResult`:
    - If success: show success message from functional spec, display metadata in 4 columns (pages, size, characters, processing time)
    - If failure: show error message
  - [ ] Test: Upload various PDFs (valid, invalid, password-protected), verify all error scenarios work end-to-end

**After Slice 7:** You have a complete, orchestrated pipeline with proper error handling ✅

---

## Slice 8: Progress Indicators & UI Polish

**Goal:** Add progress bar and finalize UI according to functional spec

- [ ] **Add progress bar to upload process**
  - [ ] In `upload.py`, add `st.progress(0, text="Validating file...")` before processing
  - [ ] Update progress to 30% with text "Extracting text..." after validation
  - [ ] Update progress to 100% with text "Complete!" after processing
  - [ ] Clear progress bar after displaying results

- [ ] **Polish UI to match functional spec**
  - [ ] Add header: "Upload Financial Documents"
  - [ ] Add description text about supported documents
  - [ ] Verify all success/error messages match functional spec exactly
  - [ ] Add text preview in expander with exact format from functional spec
  - [ ] Test multi-file upload (verify each file shows separate progress and results)
  - [ ] Test: Upload multiple files simultaneously, verify UI shows progress for each

**After Slice 8:** You have a polished, user-friendly upload experience matching the spec ✅

---

## Slice 9: Code Quality & Documentation

**Goal:** Ensure code meets portfolio quality standards

- [ ] **Configure and run code quality tools**
  - [ ] Create `ruff.toml` with configuration (line-length: 100, select: E, W, F, I, B, C4, UP)
  - [ ] Run `ruff check src/` and fix all issues
  - [ ] Run `ruff format src/` to format code
  - [ ] Add type hints to all functions (ensure 100% coverage)
  - [ ] Run `mypy src/` in strict mode and fix all type errors

- [ ] **Add documentation**
  - [ ] Add docstrings to all public classes and methods
  - [ ] Update `README.md` with:
    - Project description and purpose
    - Setup instructions (uv installation, dependency sync)
    - How to run: `streamlit run src/ui/app.py`
    - Configuration via `.env` file
    - Project structure overview
  - [ ] Verify all logging statements are appropriate and helpful

**After Slice 9:** Code is clean, type-safe, and well-documented ✅

---

## Slice 10: Testing with Real Documents

**Goal:** Validate the feature works with real financial documents

- [ ] **Prepare test documents**
  - [ ] Download a real 10-K PDF (e.g., Tesla, Apple)
  - [ ] Download an earnings report PDF
  - [ ] Create/find test PDFs for error scenarios (password-protected, corrupted if possible)
  - [ ] Save sample documents to `data/sample/`

- [ ] **Execute manual test plan**
  - [ ] Test 1: Upload valid 10-K, verify success message, check extracted text quality
  - [ ] Test 2: Upload valid earnings report, verify metadata accuracy
  - [ ] Test 3: Upload file > 50MB, verify size error
  - [ ] Test 4: Upload non-PDF file, verify type error
  - [ ] Test 5: Upload password-protected PDF (if available), verify encryption error
  - [ ] Test 6: Upload multiple files at once, verify all process correctly
  - [ ] Test 7: Check `data/uploads/` structure is correct
  - [ ] Test 8: Check `logs/financeiq.log` has appropriate log entries
  - [ ] Document any issues found and fix them

**After Slice 10:** Feature is fully tested and validated with real-world documents ✅

---

## Summary

**Total Slices:** 10 vertical, runnable increments

**Key Principles Applied:**
- Each slice delivers working, testable functionality
- Application remains runnable after every slice
- Dependencies are built incrementally
- UI feedback is available early and improves with each slice
- Testing happens throughout, not just at the end

**Estimated Timeline:** 2-3 days for full implementation (aligns with Phase 1, Days 1-3 from roadmap)
