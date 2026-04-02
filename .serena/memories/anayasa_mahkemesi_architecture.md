# Constitutional Court (Anayasa Mahkemesi) Implementation - Architecture Analysis

## Overview
The Anayasa Mahkemesi module provides comprehensive access to Turkish Constitutional Court decisions through two separate systems:
1. **Norm Denetimi** (Norm Control) - Judicial review of laws
2. **Bireysel Başvuru** (Individual Applications) - Individual constitutional complaints

Both systems have been **unified** into a single MCP interface (Phase 6 optimization - 361 tokens saved).

## Current Architecture

### 1. Module Structure
```
anayasa_mcp_module/
├── __init__.py           # Empty
├── models.py             # Pydantic data models (230 lines)
├── client.py             # Norm Denetimi client (356 lines)
├── bireysel_client.py    # Bireysel Başvuru client (355 lines)
└── unified_client.py     # Unified routing logic (122 lines)
```

### 2. API Endpoints

**Norm Denetimi API:**
- Base: `https://normkararlarbilgibankasi.anayasa.gov.tr`
- Search: GET `/Ara` (with query parameters)
- Document: Dynamic URLs from search results

**Bireysel Başvuru API:**
- Base: `https://kararlarbilgibankasi.anayasa.gov.tr`
- Search: GET `/Ara?KararBulteni=1` (with query parameters for report-style results)
- Document: Dynamic paths like `/BB/YYYY/NNNN`

### 3. Current Search Implementation (Keyword-Based)

**Norm Denetimi Search Parameters (19 parameters):**
- Keyword logic: `keywords_all[]`, `keywords_any[]`, `keywords_exclude[]` (AND/OR/NOT)
- Identifiers: case_number_esas, decision_number_karar
- Dates: first_review_date_start/end, decision_date_start/end, official_gazette_date_start/end
- Structural filters: period, application_type, rapporteur_name, norm_type, review_outcomes, reason_for_final_outcome
- Boolean filters: has_press_release, has_dissenting_opinion, has_different_reasoning
- Other: basis_constitution_article_numbers, attending_members_names
- Pagination: results_per_page (1-10), page_to_fetch, sort_by_criteria

**Bireysel Başvuru Search Parameters (simple):**
- keywords[] (AND logic only)
- page_to_fetch for pagination

**Search Architecture (client.py):**
- `_build_search_query_params_for_aym()`: Converts Pydantic model to URL query parameters (tuples list)
- `search_norm_denetimi_decisions()`: Makes HTTP GET request with params, parses HTML response
- Uses BeautifulSoup to find:
  - Decision count: div.bulunankararsayisi (regex: "(\d+)\s*Karar Bulundu")
  - Individual decisions: div.birkarar (contains reference number, metadata, keyword count)
  - Decision details: Next sibling div.col-sm-12 with table containing norm information
- Returns AnayasaSearchResult with parsed decisions list

### 4. Document Retrieval (Full Text Conversion)

**HTML to Markdown Conversion Process:**
1. Fetch document from URL
2. Parse HTML with BeautifulSoup
3. Extract main content:
   - Find div#Karar (decision tab) or fallback to div.KararMetni or div.WordSection1
   - Remove: scripts, styles, .item.col-sm-12 divs, .modal.fade divs
4. Convert to Markdown using MarkItDown with BytesIO stream (no temp files)
5. Extract metadata during fetch:
   - Esas No./Karar No.: Find bold text in <p> tags containing "Esas No.:" and "Karar No.:"
   - Karar Tarihi: Find bold text containing "Karar tarihi:" or regex "Karar Tarihi\s*:\s*([\d\.]+)"
   - Resmi Gazete: Find text containing "Resmî Gazete tarih ve sayısı:" or "Resmi Gazete tarih/sayı:"

**Pagination & Chunking:**
- Split markdown into 5,000 character chunks
- Calculate: total_pages = ceil(len(markdown) / 5000)
- Return current_page_clamped (max 1, min total_pages)
- Include pagination metadata: current_page, total_pages, is_paginated flag

### 5. Data Models (models.py - 230 lines)

**Norm Denetimi Models:**
- `AnayasaNormDenetimiSearchRequest`: 19 search parameters
- `AnayasaReviewedNormInfo`: norm_name_or_number, article_number, review_type_and_outcome, outcome_reason, basis_constitution_articles_cited[], postponement_period
- `AnayasaDecisionSummary`: decision_reference_no, decision_page_url, keywords_found_count, application_type_summary, applicant_summary, decision_outcome_summary, decision_date_summary, reviewed_norms[]
- `AnayasaSearchResult`: decisions[], total_records_found, retrieved_page_number
- `AnayasaDocumentMarkdown`: source_url, decision_reference_no_from_page, decision_date_from_page, official_gazette_info_from_page, markdown_chunk, current_page, total_pages, is_paginated

**Bireysel Başvuru Models:**
- `AnayasaBireyselReportSearchRequest`: keywords[], page_to_fetch
- `AnayasaBireyselReportDecisionDetail`: hak, mudahale_iddiası, sonuç, giderim (4 fields per right examined)
- `AnayasaBireyselReportDecisionSummary`: title, decision_reference_no, decision_page_url, decision_type_summary, decision_making_body, application_date_summary, decision_date_summary, application_subject_summary, details[]
- `AnayasaBireyselReportSearchResult`: decisions[], total_records_found, retrieved_page_number
- `AnayasaBireyselBasvuruDocumentMarkdown`: source_url, basvuru_no_from_page, karar_tarihi_from_page, basvuru_tarihi_from_page, karari_veren_birim_from_page, karar_turu_from_page, resmi_gazete_info_from_page, markdown_chunk, current_page, total_pages, is_paginated

**Unified Models:**
- `AnayasaUnifiedSearchRequest`: decision_type (norm_denetimi|bireysel_basvuru), keywords[], page_to_fetch, results_per_page, + type-specific parameters
- `AnayasaUnifiedSearchResult`: decision_type, decisions[] (Dict[str, Any]), total_records_found, retrieved_page_number
- `AnayasaUnifiedDocumentMarkdown`: decision_type, source_url, document_data (Dict), markdown_chunk, current_page, total_pages, is_paginated

### 6. Unified Client Routing (unified_client.py - 122 lines)

**AnayasaUnifiedClient class:**
- Maintains instances of both norm_client and bireysel_client
- `search_unified()`: Routes based on decision_type parameter
  - norm_denetimi: Converts to AnayasaNormDenetimiSearchRequest, calls norm_client.search_norm_denetimi_decisions()
  - bireysel_basvuru: Converts to AnayasaBireyselReportSearchRequest, calls bireysel_client.search_bireysel_basvuru_report()
  - Returns unified AnayasaUnifiedSearchResult
- `get_document_unified()`: Auto-detects decision type from URL
  - Checks for "normkararlarbilgibankasi" in netloc or "/ND/" in path → norm_denetimi
  - Checks for "kararlarbilgibankasi" in netloc or "/BB/" in path → bireysel_basvuru
  - Calls appropriate client, wraps result in unified model

### 7. MCP Tool Integration (mcp_server_main.py)

**Active Tools (2 tools - Phase 6 optimization):**

```python
@app.tool(
    description="Search Constitutional Court decisions from either Norm Control or Individual Applications",
    annotations={"readOnlyHint": True, "openWorldHint": True, "idempotentHint": True}
)
async def search_anayasa_unified(
    decision_type: Literal["norm_denetimi", "bireysel_basvuru"],
    keywords: List[str],
    page_to_fetch: int (1-100),
    # Norm Denetimi specific (ignored for bireysel_basvuru)
    keywords_all: List[str],
    keywords_any: List[str],
    decision_type_norm: Literal["ALL", "1", "2", "3"],
    application_date_start: str,
    application_date_end: str,
    # Bireysel Başvuru specific (ignored for norm_denetimi)
    decision_start_date: str,
    decision_end_date: str,
    norm_type: Literal["ALL", "1", "2", ...],
    subject_category: str
) -> str (JSON)
```

```python
@app.tool(
    description="Retrieve full text of Constitutional Court decision. Auto-detects decision type from URL",
    annotations={"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True}
)
async def get_anayasa_document_unified(
    document_url: str,
    page_number: int (1-indexed)
) -> str (JSON)
```

**Deactivated Tools (4 tools - Phase 6 optimization, marked with DEACTIVATED):**
- search_anayasa_norm_denetimi_decisions
- get_anayasa_norm_denetimi_document_markdown
- search_anayasa_bireysel_basvuru_report
- get_anayasa_bireysel_basvuru_document_markdown

## Search Capabilities Analysis

### Current Keyword-Based Search Strengths

**Norm Denetimi - Rich Structural Filtering:**
1. Multi-keyword logic with AND/OR/NOT operators
2. Case/decision number search (exact matching)
3. Date range filtering (review, decision, gazette dates)
4. Norm categorization (14 norm types)
5. Application type filtering (3 categories)
6. Constitutional period selection (1961 vs 1982 constitutions)
7. Decision outcome filtering (8 outcome types)
8. Reasoning/grounds filtering (30 different grounds)
9. Member/rapporteur filtering
10. Constitutional articles cited filtering

**Bireysel Başvuru - Report Format:**
1. Simple keyword search
2. Rights/claims detailed in structured table format
3. Remedy/solution tracking

### Limitations of Current Keyword Search

1. **No semantic understanding**: Different words for same concept ("mülkiyet hakkı" vs "property rights")
2. **No concept hierarchy**: Can't find related legal principles
3. **No cross-language**: Turkish-only, no English queries
4. **No abbreviation matching**: "HADD" vs "Hukuk Alanında Değerli Dosya Denetimi"
5. **No synonym support**: Formal vs informal terminology
6. **No semantic similarity**: Can't find similar cases with different terminology
7. **No legal concept graph**: Can't traverse related principles or doctrines
8. **No fuzzy matching**: Typos or spelling variations fail completely
9. **No legal reasoning search**: Can't query by legal arguments or doctrinal approaches
10. **No cross-system semantic linking**: Norm Denetimi and Bireysel Başvuru not semantically linked
11. **Order dependency**: Query order may affect results
12. **No ranking by relevance**: Just keyword presence/absence
13. **No query expansion**: No automatic synonym/related term expansion

### HTML Document Structure

**Norm Denetimi Search Results HTML:**
```
div.birkarar (repeated for each decision)
├── div.bkararbaslik (header with E./K. numbers)
│   └── div.BulunanKelimeSayisi (keyword count)
└── div.kararbilgileri (metadata with | separators: application_type|applicant|outcome|date)

Next sibling:
div.col-sm-12
└── table.table > tbody > tr (one row per reviewed norm with 6 columns)
    ├── td: norm name/number
    ├── td: article number
    ├── td: review type and outcome
    ├── td: outcome reason
    ├── td: constitutional articles cited (comma-separated)
    └── td: postponement period
```

**Full Decision Content (both types):**
```
div#Karar (decision tab)
└── div.KararMetni or div.WordSection1
    └── HTML content in MS Word format (many nested divs with styles)

Metadata extracted from:
<p><b>Esas No.:</b> [number]</p>
<p><b>Karar No.:</b> [number]</p>
<p><b>Karar tarihi:</b> [date]</p>
<p>Resmî Gazete tarih ve sayısı: [info]</p>
```

### Document Content Characteristics

- **Language**: Turkish legal language (specialized terminology)
- **Format**: Microsoft Word-generated HTML (nested divs, complex styles)
- **Content types**: 
  - Norm Denetimi: Constitutional principle analysis, legal reasoning, comparison with challenged norm
  - Bireysel Başvuru: Right violated, remedy granted, procedural requirements
- **Typical length**: 5,000-50,000+ characters
- **Citations**: Internal cross-references to constitutional articles
- **Structure**: Formal legal document with sections, subsections, reasoning

## Key Technical Insights for Semantic Search

### Content Encoding
- Currently: HTML → BeautifulSoup parsing → MarkItDown → Markdown
- Extraction: Specific div/class/id selectors
- Metadata: Regex patterns and text parsing

### Search Query Flow
1. User provides keywords/filters
2. Convert Pydantic model to URL query parameters
3. HTTP GET request to Constitutional Court API
4. HTML response parsed with BeautifulSoup
5. Decision summaries extracted and validated
6. Results returned as JSON

### Document Retrieval Flow
1. Get document URL from search results
2. HTTP GET request to URL
3. Parse HTML for metadata extraction
4. MarkItDown converts HTML to Markdown
5. Chunk by 5,000 characters
6. Return paginated Markdown with metadata

## Performance Baseline

- **Search**: ~1-5 seconds (HTML parsing + regex extraction)
- **Document**: ~2-10 seconds (fetch + parse + MarkItDown + chunking)
- **Memory**: Minimal (5,000 char chunks, no full document in memory)
- **API Response Size**: Typically 50-500 KB HTML for search, 100-1000 KB for full decision

## Next Steps for Semantic Search Integration

1. **Vector Embeddings**: Embed decisions using Turkish legal model
2. **Concept Extraction**: Identify and tag legal concepts (rights, procedures, principles)
3. **Semantic Queries**: Convert natural language questions to embeddings
4. **Hybrid Search**: Combine keyword + semantic similarity
5. **Legal Ontology**: Map Turkish Constitutional Court concepts and relationships
6. **Cross-system Linking**: Semantically link Norm Denetimi and Bireysel Başvuru decisions
7. **Precedent Graph**: Extract citations and create legal precedent relationships
8. **Fine-tuned Embeddings**: Train embeddings specifically on Turkish Constitutional law
9. **Ranking**: Re-rank results by semantic relevance to user's legal intent
10. **Explanation**: Provide semantic reasoning for why result is relevant
