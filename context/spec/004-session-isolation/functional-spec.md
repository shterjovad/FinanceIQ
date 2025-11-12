# Phase 4: Session-Based Isolation - Functional Specification

## Overview

Enable anonymous users to safely use the application with isolated document storage and queries. Each browser tab gets its own isolated workspace that lasts only while the tab is open. This makes the application safe for public deployment and demo purposes with minimal complexity.

## Problem Statement

**Current Issue:**
- All uploaded documents are mixed together in one shared space
- User A can see/query User B's documents → **Data leakage**
- Not safe for public demo with sensitive financial documents
- Cannot deploy to resume/portfolio without security risk

**Solution:**
- Each browser tab gets unique isolated workspace
- Documents automatically tagged with session ID
- Queries only search within current session
- Session cleared when user closes tab/browser

## Design Philosophy: Browser Session Only

**Key Decision: No Persistent Storage**

This is a **browser-session-only** system:
- ✅ Session lives only while browser tab is open
- ✅ Close tab → session gone (simple, automatic cleanup)
- ✅ Refresh page → session persists (Streamlit session state)
- ✅ Open new tab → new session (isolated)
- ❌ No 24-hour persistence
- ❌ No background cleanup jobs needed
- ❌ No session database

**Why This Approach?**
1. **Much simpler**: No background jobs, no cleanup complexity
2. **Adequate for demos**: Users typically spend 5-10 minutes trying it
3. **Safer**: Documents gone when user leaves
4. **Faster to build**: 2-3 days vs 5+ days
5. **Lower cost**: Minimal storage, simple infrastructure

## User Stories

### Story 1: Isolated Document Upload
**As a** anonymous user visiting the public demo
**I want to** upload my company's financial documents
**So that** I can analyze them without worrying about data leakage

**Acceptance Criteria:**
- ✅ Each browser tab gets unique session ID on first load
- ✅ Documents tagged with session ID automatically
- ✅ Clear messaging: "Session cleared when you close this tab"
- ✅ Other users in other tabs cannot see my documents

**Example:**
```
User opens site in Chrome:
→ Gets session ID: abc123
→ Sees banner: "🔒 Private session. Documents cleared when you close this tab."
→ Uploads Apple 10-K → Tagged as session_abc123_aapl-10k.pdf
→ User in Firefox (session def456) cannot see this document
→ User closes Chrome tab → Documents available for manual cleanup
```

### Story 2: Isolated Queries
**As a** anonymous user with uploaded documents
**I want to** query only MY documents
**So that** results don't include other users' data

**Acceptance Criteria:**
- ✅ Queries automatically filtered by session ID
- ✅ No manual selection needed
- ✅ Clear indication of how many documents in session
- ✅ Cannot access documents from other sessions

**Example:**
```
Tab 1 (session abc123):
- Uploads: Apple 10-K, Microsoft 10-K
- Queries: "What was Apple's revenue?"
- Result: Only searches Apple & Microsoft docs from session abc123

Tab 2 (session def456):
- Uploads: Google 10-K
- Queries: "What was Apple's revenue?"
- Result: "I don't have information about Apple" (correct - not in their session)
```

### Story 3: Session Persistence During Visit
**As a** user who refreshes the page
**I want to** see my previously uploaded documents
**So that** I can continue my analysis without re-uploading

**Acceptance Criteria:**
- ✅ Session persists across page refreshes (same tab)
- ✅ Documents remain available until tab is closed
- ✅ Clear indication of active session

**Example:**
```
User uploads documents → Refreshes page:
- Same session ID retrieved from Streamlit session state
- Previously uploaded documents still available
- Can continue querying

User closes tab → Opens new tab:
- NEW session ID created
- Previous documents NOT available (expected)
```

### Story 4: Multi-Tab Isolation
**As a** user who opens multiple tabs
**I want** each tab to have its own isolated workspace
**So that** I can compare different document sets

**Acceptance Criteria:**
- ✅ Each browser tab gets independent session
- ✅ Documents in Tab 1 not visible in Tab 2
- ✅ Can have different documents in each tab

**Example:**
```
User opens 2 tabs:

Tab 1:
- Session abc123
- Uploads Apple 10-K
- Queries only see Apple docs

Tab 2:
- Session def456 (different!)
- Uploads Google 10-K
- Queries only see Google docs

Perfect isolation ✅
```

## Features

### Feature 1: Browser-Session Management
**Session Creation:**
- Auto-generate UUID on first page load
- Store in `st.session_state` (Streamlit's browser session)
- No database needed - lives in browser memory

**Session Lifecycle:**
```python
Page load → Session created → Stored in st.session_state
   ↓
User uploads docs, queries → Session active
   ↓
User closes tab → st.session_state cleared → Session gone
```

**Session Metadata (In-Memory Only):**
```python
st.session_state = {
    "session_id": "abc123...",
    "document_count": 2,
    "messages": [...],  # Chat history
}
```

### Feature 2: Isolated Document Upload
**Document Tagging:**
- All documents tagged with session_id
- Document ID format: `{session_id}_{filename}`
- No persistent metadata database needed

**Vector Store Payload:**
```python
{
  "session_id": "abc123",  # ← Isolation key
  "document_id": "abc123_aapl-10k.pdf",
  "filename": "aapl-10k.pdf",
  "text": "...",
  "page_numbers": [1],
  "embedding": [...]
}
```

**File System Storage (Simple):**
```
data/uploads/sessions/
├── abc123/
│   ├── aapl-10k.pdf
│   └── msft-10k.pdf
└── def456/
    └── googl-10k.pdf

# Note: These accumulate until manual/weekly cleanup
# Not a problem for demo - storage is cheap
```

### Feature 3: Isolated Queries
**Automatic Filtering:**
- All vector searches filtered by session_id
- No user action required
- Transparent to user

**Query Example:**
```python
# User asks: "What was revenue?"
# Backend automatically adds session filter:

results = qdrant.search(
    collection_name="financial_docs",
    query_vector=embedding,
    query_filter={
        "must": [
            {"key": "session_id", "match": {"value": "abc123"}}
        ]
    }
)
```

### Feature 4: Simple Cleanup (Optional)
**No Real-Time Cleanup Needed!**

Since sessions are browser-only:
- Most docs will be "orphaned" (user closed tab, but files remain)
- This is fine! Storage is cheap for a demo
- Run manual cleanup weekly/monthly if needed

**Optional Weekly Cleanup Script:**
```bash
# Optional: Clean up old files once a week
# Not critical - just housekeeping

python scripts/cleanup_old_sessions.py
# Deletes files older than 7 days
# Deletes Qdrant vectors with no active session
```

### Feature 5: User Communication
**Session Status UI:**
```
┌─────────────────────────────────────────────────┐
│ 🔒 Private Session                               │
├─────────────────────────────────────────────────┤
│ Documents: 2                                     │
│ ⚠ Cleared when you close this tab              │
└─────────────────────────────────────────────────┘
```

**Upload Confirmation:**
```
✅ Document uploaded successfully
   • Stored in your private session
   • Only visible to you in this tab
   • Cleared when you close this tab
```

**Query Scope Indicator:**
```
💬 Ask Questions

Searching: 2 documents in your session
[Ask a question about your documents...]
```

## User Interface

### Main App Layout
```
┌────────────────────────────────────────────────────┐
│ FinanceIQ - Financial Document Analysis            │
├────────────────────────────────────────────────────┤
│ 🔒 Private Session | 2 docs | Tab-only             │
└────────────────────────────────────────────────────┘

┌── Tab: 📄 Upload Documents ────────────────────────┐
│                                                     │
│ Upload your financial documents (PDFs)             │
│ ⚠ Session cleared when you close this tab         │
│                                                     │
│ [Drag and drop or click to upload]                 │
│                                                     │
│ Your Documents (2):                                 │
│ • aapl-10k.pdf                                     │
│ • msft-10k.pdf                                     │
└────────────────────────────────────────────────────┘

┌── Tab: 💬 Ask Questions ───────────────────────────┐
│                                                     │
│ Query Scope: 2 documents in your session           │
│                                                     │
│ [Ask a question about your documents...]           │
└────────────────────────────────────────────────────┘
```

### Session Info Sidebar
```
┌─────────────────────────────┐
│ 📊 System Status             │
├─────────────────────────────┤
│ ✓ RAG System Ready          │
│ ✓ Vector DB Connected       │
│                              │
│ ─────────────────────────── │
│                              │
│ 🔒 Your Session              │
│ Status: Active               │
│ Documents: 2                 │
│ Type: Browser session        │
│                              │
│ ⚠ Privacy Notice            │
│ Your documents are:          │
│ • Isolated to this tab      │
│ • Not visible to others     │
│ • Cleared when tab closes   │
└─────────────────────────────┘
```

## Success Criteria

### Must Have
- ✅ Each browser tab gets unique session ID
- ✅ Documents tagged with session ID
- ✅ Queries filtered by session ID (no leakage)
- ✅ Session persists across page refreshes
- ✅ Session cleared when tab closes
- ✅ Clear privacy messaging in UI

### Should Have
- ✅ Session status display
- ✅ Document list per session
- ✅ Warning about tab-only session
- ✅ Multi-tab isolation tested

### Nice to Have
- Download all documents button
- "Share session" feature (advanced)
- Session statistics
- Optional manual cleanup script

## Out of Scope
- ❌ 24-hour persistent sessions
- ❌ Background cleanup jobs
- ❌ Session database
- ❌ User authentication
- ❌ Session expiration timers
- ❌ Email notifications

## Security Requirements

### Isolation Guarantees
- ✅ User A (tab 1) cannot query User B's (tab 2) documents
- ✅ User A cannot list User B's documents
- ✅ User A cannot access User B's files
- ✅ Session IDs are cryptographically random (UUIDs)
- ✅ No session ID sharing between tabs

### Data Protection
- ✅ Documents stored in isolated directories
- ✅ Vector payloads include session filter
- ✅ No session ID leakage in URLs or logs
- ✅ Each tab completely isolated

### Testing Isolation
```python
# Test scenario
# Open 2 browser tabs

# Tab 1
session_a = "abc123"
upload_document(session_a, "apple.pdf")
result = query(session_a, "What was Apple's revenue?")
assert "Apple" in result  # ✅ Works

result = query(session_a, "What was Google's revenue?")
assert "don't have" in result  # ✅ Can't see Google doc

# Tab 2
session_b = "def456"
upload_document(session_b, "google.pdf")
result = query(session_b, "What was Google's revenue?")
assert "Google" in result  # ✅ Works

result = query(session_b, "What was Apple's revenue?")
assert "don't have" in result  # ✅ Can't see Apple doc
```

## Performance Requirements

- **Session creation**: <10ms (just UUID generation)
- **Document upload with isolation**: Same as before (no overhead)
- **Query with session filter**: <5% overhead vs. non-filtered
- **No cleanup overhead**: No background jobs!

## Error Handling

### Lost Session (User Cleared Browser Data)
```
"Session not found. This may happen if you cleared your browser data.

Please start a new session by uploading documents."

[Start Over]
```

### Storage Full
```
"Upload failed: Session storage limit reached (max 100MB per session).

Please delete some documents or open a new tab for a fresh session."
```

## Privacy & Legal

### Privacy Notice (in app)
```
📋 Privacy & Data Handling

• Your documents are stored in an isolated browser session
• Each browser tab has its own private workspace
• Other users cannot see your documents
• Documents cleared when you close this tab
• No personal information is collected
• No user accounts or authentication required

This is a demonstration application for portfolio purposes.
Do not upload highly confidential information.
```

### Recommended Disclaimer
```
⚠ Demo System Notice

This is a demonstration application.
• Browser session only - data cleared when you close tab
• Do not upload highly confidential documents
• No guarantees of availability
• Use at your own risk
```

## Comparison: Browser Session vs. Time-Limited

| Feature | Browser Session (✅ Chosen) | Time-Limited |
|---------|---------------------------|--------------|
| **Complexity** | Very Simple | Complex |
| **Build Time** | 2-3 days | 5+ days |
| **Database** | None needed | SQLite required |
| **Cleanup** | Automatic (tab close) | Background jobs |
| **Storage** | Minimal | Higher |
| **User Convenience** | Good for demos | Better for returning |
| **Deployment** | Super easy | More complex |
| **Maintenance** | Zero | Weekly monitoring |

## Example User Journey

### First-Time User
```
1. User visits https://financeiq-demo.streamlit.app
2. App creates session ID: abc123 (stored in browser memory)
3. User sees: "🔒 Private session. Cleared when you close this tab."
4. User uploads: Apple 10-K, Microsoft 10-K
5. UI shows: "2 documents in your session"
6. User queries: "Compare revenue of Apple and Microsoft"
7. Answer provided from ONLY their 2 documents
8. User closes tab → Session cleared (automatic)
```

### User Refreshes Page
```
1. User uploads documents
2. User refreshes page
3. Session ID retrieved from st.session_state
4. Documents still available (same session)
5. Can continue querying ✅
```

### User Opens New Tab
```
1. User closes first tab
2. User opens new tab to same URL
3. NEW session ID created
4. Previous documents NOT available
5. Must upload again
6. This is expected behavior ✅
```

## Launch Checklist

**Before Public Deployment:**
- [ ] Session isolation tested with multiple browser tabs
- [ ] Privacy notice displayed prominently
- [ ] Storage limits enforced
- [ ] Error handling tested
- [ ] Performance acceptable
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Test on multiple browsers (Chrome, Firefox, Safari)

**After Deployment:**
- [ ] Monitor storage usage (weekly)
- [ ] Optional: Run cleanup script monthly
- [ ] Track user feedback
- [ ] Update resume/portfolio with live demo link

## Implementation Timeline

**Day 1: Core Session Logic**
- Session ID generation in app.py
- Pass session_id to all RAG operations
- Basic testing

**Day 2: Vector Store Isolation**
- Add session_id to Qdrant payloads
- Implement session filtering in queries
- Test isolation between tabs

**Day 3: UI Polish**
- Session status display
- Privacy notices
- Error handling
- Final testing

**Total: 2-3 days** → Ready to deploy!

Much faster than 5+ days for time-limited approach ✅
