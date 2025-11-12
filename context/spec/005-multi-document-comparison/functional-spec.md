# Phase 3: Multi-Document Comparison - Functional Specification

## Overview

Enable users to query and compare information across multiple documents simultaneously, supporting cross-company analysis, time-series tracking, and aggregated insights.

## User Stories

### Story 1: Cross-Company Comparison
**As a** financial analyst
**I want to** compare metrics across multiple companies
**So that** I can quickly identify which company performs best

**Example:**
- Upload: Apple 10-K, Microsoft 10-K, Google 10-K
- Query: "Compare the revenue growth of these three companies"
- Result: Synthesized answer with comparative analysis and sources from all three documents

### Story 2: Time-Series Analysis
**As a** financial analyst
**I want to** track how metrics change over time for a single company
**So that** I can identify trends and patterns

**Example:**
- Upload: Apple 10-K 2021, 2022, 2023, 2024
- Query: "How has Apple's R&D spending changed over the last 4 years?"
- Result: Timeline showing R&D spending by year with trend analysis

### Story 3: Document Collections
**As a** user managing many documents
**I want to** organize documents into collections
**So that** I can quickly query related documents together

**Example:**
- Create collection: "Tech Giants 2024"
- Add: Apple, Microsoft, Google, Amazon, Meta 10-Ks
- Query collection: "What are common risk factors across these companies?"

### Story 4: Aggregation & Ranking
**As a** financial analyst
**I want to** aggregate metrics across multiple documents
**So that** I can identify patterns and outliers

**Example:**
- Query: "Which company has the highest profit margin?"
- Result: Ranked list with profit margins from all documents

## Features

### Feature 1: Multi-Document Upload & Management
- **Bulk upload**: Upload multiple PDFs at once
- **Document metadata**:
  - Company name (extracted or manual)
  - Year/quarter (extracted or manual)
  - Document type (10-K, 10-Q, earnings report, etc.)
  - Custom tags
- **Document list view**: See all uploaded documents with metadata
- **Delete multiple**: Select and delete multiple documents
- **Document search**: Filter documents by metadata

### Feature 2: Document Collections
- **Create collections**: Group related documents
- **Add/remove documents**: Manage collection membership
- **Collection queries**: Query all documents in a collection
- **Pre-defined collections**:
  - "All Documents"
  - "Recent Uploads"
  - Custom user-created collections

### Feature 3: Multi-Document Query Interface
- **Document selector**: Choose which documents/collections to include in query
- **Query scope indicator**: Show how many documents are being searched
- **Per-document source attribution**: Clearly show which document each fact came from

### Feature 4: Comparison Query Types
Support these query patterns:
- **Direct comparison**: "Compare X across [companies]"
- **Ranking**: "Which company has the highest/lowest X?"
- **Time-series**: "How has X changed from [year] to [year]?"
- **Aggregation**: "What's the average X across these companies?"
- **Common factors**: "What do all these companies mention about X?"
- **Differences**: "What's unique about [company] compared to others?"

### Feature 5: Comparative Answer Display
- **Structured comparison tables**: Side-by-side metrics
- **Timeline views**: For time-series queries
- **Ranked lists**: For ranking queries
- **Source attribution per company/document**: Clear citations
- **Visual indicators**: Highlight high/low values, trends

## User Interface

### Document Management Tab (New)
```
┌─────────────────────────────────────────────────────┐
│ 📚 Document Library                                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Collections:  [All Documents ▼]  [+ New Collection] │
│                                                      │
│ ┌──────────────────────────────────────────────┐   │
│ │ Document Name        │ Company  │ Year │ Type │   │
│ ├──────────────────────────────────────────────┤   │
│ │ ☑ aapl-10k-2024.pdf │ Apple    │ 2024 │ 10-K │   │
│ │ ☑ msft-10k-2024.pdf │ Microsoft│ 2024 │ 10-K │   │
│ │ ☐ googl-10k-2024.pdf│ Google   │ 2024 │ 10-K │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ [Upload Multiple] [Delete Selected] [Add to Collection]│
└─────────────────────────────────────────────────────┘
```

### Enhanced Chat Interface
```
┌─────────────────────────────────────────────────────┐
│ 💬 Ask Questions                                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Query Scope: 📁 Tech Giants 2024 (3 documents)      │
│              [Change Collection ▼]                   │
│                                                      │
│ 👤 User: Compare revenue growth across companies    │
│                                                      │
│ 🤖 Assistant:                                        │
│    Based on the 2024 10-K filings:                  │
│                                                      │
│    Revenue Growth Comparison:                        │
│    1. Microsoft: 12.3% YoY growth                   │
│       📄 Source: msft-10k-2024.pdf, page 45         │
│    2. Google: 10.1% YoY growth                      │
│       📄 Source: googl-10k-2024.pdf, page 38        │
│    3. Apple: 8.7% YoY growth                        │
│       📄 Source: aapl-10k-2024.pdf, page 42         │
│                                                      │
│    [View Detailed Comparison Table]                 │
└─────────────────────────────────────────────────────┘
```

## Success Criteria

### Must Have
- ✅ Upload and manage multiple documents with metadata
- ✅ Create and manage document collections
- ✅ Query multiple documents in a single request
- ✅ Compare metrics across documents with source attribution
- ✅ Display comparative results clearly

### Should Have
- ✅ Bulk document upload
- ✅ Automatic metadata extraction (company name, year)
- ✅ Document filtering and search
- ✅ Structured comparison views (tables, timelines)

### Nice to Have
- Visual charts for comparisons
- Export comparison results
- Document versioning (track updates to same document)
- Smart collection suggestions ("Documents similar to...")

## Out of Scope (Future)
- Real-time data feeds
- Financial metric calculations (ratios, formulas)
- Document editing or annotation
- Multi-user collaboration
- API access

## Performance Requirements

- **Multi-doc query response time**: <30s for 5 documents
- **Document upload**: Support up to 10 documents at once
- **Collection size**: Support collections with up to 100 documents
- **Query across collection**: Handle queries across up to 20 documents

## Error Handling

### No Results Across Documents
```
"I couldn't find information about [query] in any of the selected documents.
Try:
- Checking if the documents contain this information
- Rephrasing your question
- Selecting different documents"
```

### Partial Results
```
"I found information in 2 of 3 documents:
- Found in: Apple 10-K, Microsoft 10-K
- Not found in: Google 10-K

[Shows results from documents that had information]"
```

### Conflicting Information
```
"I found conflicting information:
- Apple 10-K states revenue was $X
- Microsoft 10-K states Apple revenue was $Y
Please verify the sources."
```

## Example Queries

### Cross-Company
- "Compare the revenue of Apple and Microsoft"
- "Which company mentions AI more frequently?"
- "What are the key differences in their risk factors?"

### Time-Series
- "How has Apple's revenue changed from 2020 to 2024?"
- "Show me the trend in R&D spending over the last 3 years"
- "Did the risk factors change between 2023 and 2024?"

### Aggregation
- "What's the average profit margin across all tech companies?"
- "Which companies mention supply chain as a risk?"
- "What are the common themes in management discussions?"

### Ranking
- "Which company has the highest revenue?"
- "Rank these companies by R&D spending"
- "Which company grew fastest?"
