# Graph Report - .  (2026-04-25)

## Corpus Check
- 160 files · ~284,734 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1459 nodes · 2894 edges · 32 communities detected
- Extraction: 68% EXTRACTED · 32% INFERRED · 0% AMBIGUOUS · INFERRED: 915 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Clustering Engine|Clustering Engine]]
- [[_COMMUNITY_CLI Installation|CLI Installation]]
- [[_COMMUNITY_HTTPX Client|HTTPX Client]]
- [[_COMMUNITY_Language Extractors|Language Extractors]]
- [[_COMMUNITY_AST Extraction Core|AST Extraction Core]]
- [[_COMMUNITY_Graph Analysis|Graph Analysis]]
- [[_COMMUNITY_Ingest & Security|Ingest & Security]]
- [[_COMMUNITY_Worker & Cron|Worker & Cron]]
- [[_COMMUNITY_Graph Builder|Graph Builder]]
- [[_COMMUNITY_MCP Server|MCP Server]]
- [[_COMMUNITY_API Handlers|API Handlers]]
- [[_COMMUNITY_Validation & Exceptions|Validation & Exceptions]]
- [[_COMMUNITY_File Detection|File Detection]]
- [[_COMMUNITY_Cache Module|Cache Module]]
- [[_COMMUNITY_Python Extraction|Python Extraction]]
- [[_COMMUNITY_API Routes|API Routes]]
- [[_COMMUNITY_Video Transcription|Video Transcription]]
- [[_COMMUNITY_Wiki Generation|Wiki Generation]]
- [[_COMMUNITY_Report Generation|Report Generation]]
- [[_COMMUNITY_Authentication|Authentication]]
- [[_COMMUNITY_Benchmarking|Benchmarking]]
- [[_COMMUNITY_Analyzer Example|Analyzer Example]]
- [[_COMMUNITY_PHP Events Fixture|PHP Events Fixture]]
- [[_COMMUNITY_Objective-C Fixture|Objective-C Fixture]]
- [[_COMMUNITY_PHP Container Fixture|PHP Container Fixture]]
- [[_COMMUNITY_PHP Static Props Fixture|PHP Static Props Fixture]]
- [[_COMMUNITY_Python ML Fixture|Python ML Fixture]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Queue Connection|Queue Connection]]
- [[_COMMUNITY_Manifest|Manifest]]
- [[_COMMUNITY_Init|Init]]
- [[_COMMUNITY_TS Init|TS Init]]

## God Nodes (most connected - your core abstractions)
1. `build_from_json()` - 44 edges
2. `cluster()` - 39 edges
3. `main()` - 37 edges
4. `_labels()` - 34 edges
5. `_make_id()` - 32 edges
6. `detect()` - 31 edges
7. `Graph` - 26 edges
8. `to_wiki()` - 24 edges
9. `run_pipeline()` - 24 edges
10. `extract_swift()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `test_count_words_sample_md()` --calls--> `count_words()`  [INFERRED]
  C:\Users\palai\Documents\Projects\Zenvort\graphify\tests\test_detect.py → C:\Users\palai\Documents\Projects\Zenvort\graphify\graphify\detect.py
- `test_make_id_strips_dots_and_underscores()` --calls--> `_make_id()`  [INFERRED]
  C:\Users\palai\Documents\Projects\Zenvort\graphify\tests\test_extract.py → C:\Users\palai\Documents\Projects\Zenvort\graphify\graphify\extract.py
- `test_make_id_no_leading_trailing_underscores()` --calls--> `_make_id()`  [INFERRED]
  C:\Users\palai\Documents\Projects\Zenvort\graphify\tests\test_extract.py → C:\Users\palai\Documents\Projects\Zenvort\graphify\graphify\extract.py
- `processJob()` --calls--> `downloadFile()`  [INFERRED]
  C:\Users\palai\Documents\Projects\Zenvort\apps\worker\src\index.ts → C:\Users\palai\Documents\Projects\Zenvort\packages\storage\src\index.ts
- `processJob()` --calls--> `uploadFile()`  [INFERRED]
  C:\Users\palai\Documents\Projects\Zenvort\apps\worker\src\index.ts → C:\Users\palai\Documents\Projects\Zenvort\packages\storage\src\index.ts

## Communities

### Community 0 - "Clustering Engine"
Cohesion: 0.03
Nodes (127): _node_community_map(), Invert communities dict: node_id -> community_id., cluster(), cohesion_score(), _partition(), Leiden community detection on NetworkX graphs. Splits oversized communities. Ret, Run a second Leiden pass on a community subgraph to split it further., Context manager to suppress stdout/stderr during library calls.      graspolog (+119 more)

### Community 1 - "CLI Installation"
Cohesion: 0.02
Nodes (131): _agents_install(), _agents_uninstall(), _antigravity_install(), _antigravity_uninstall(), _check_skill_version(), claude_install(), claude_uninstall(), _clone_repo() (+123 more)

### Community 2 - "HTTPX Client"
Cohesion: 0.02
Nodes (50): AsyncClient, BaseClient, Client, Limits, The main Client and AsyncClient classes. BaseClient holds all shared logic. Cli, Asynchronous HTTP client., Shared implementation for Client and AsyncClient.     Handles auth, redirects,, Synchronous HTTP client. (+42 more)

### Community 3 - "Language Extractors"
Cohesion: 0.03
Nodes (116): extract_c(), extract_cpp(), extract_csharp(), extract_elixir(), extract_java(), extract_julia(), extract_kotlin(), extract_objc() (+108 more)

### Community 4 - "AST Extraction Core"
Cohesion: 0.04
Nodes (90): _check_tree_sitter_version(), _csharp_extra_walk(), extract(), extract_blade(), extract_dart(), _extract_generic(), extract_go(), extract_js() (+82 more)

### Community 5 - "Graph Analysis"
Cohesion: 0.05
Nodes (78): _cross_community_surprises(), _cross_file_surprises(), _file_category(), god_nodes(), graph_diff(), _is_concept_node(), _is_file_node(), Graph analysis: god nodes (most connected), surprising connections (cross-commun (+70 more)

### Community 6 - "Ingest & Security"
Cohesion: 0.05
Nodes (66): _detect_url_type(), _download_binary(), _fetch_arxiv(), _fetch_html(), _fetch_tweet(), _fetch_webpage(), _html_to_markdown(), ingest() (+58 more)

### Community 7 - "Worker & Cron"
Cohesion: 0.04
Nodes (24): convertWithFFmpeg(), convertWithLibreOffice(), processJob(), sendWebhook(), ApiClient, CacheManager, Config, createProcessor() (+16 more)

### Community 8 - "Graph Builder"
Cohesion: 0.05
Nodes (58): build(), build_from_json(), build_merge(), deduplicate_by_label(), _norm_label(), _normalize_id(), Merge multiple extraction results into one graph.      directed=True produces, Canonical dedup key — lowercase, alphanumeric only. (+50 more)

### Community 9 - "MCP Server"
Cohesion: 0.06
Nodes (50): Base, Server, LinearAlgebra, add(), area(), Circle, Color, describe() (+42 more)

### Community 10 - "API Handlers"
Cohesion: 0.05
Nodes (55): handle_delete(), handle_enrich(), handle_get(), handle_list(), handle_search(), handle_upload(), API module - exposes the document pipeline over HTTP. Thin layer over parser, v, Accept a list of file paths, run the full pipeline on each,     and return a su (+47 more)

### Community 11 - "Validation & Exceptions"
Cohesion: 0.05
Nodes (52): Exception, CloseError, ConnectError, ConnectTimeout, CookieConflict, DecodingError, HTTPError, HTTPStatusError (+44 more)

### Community 12 - "File Detection"
Cohesion: 0.06
Nodes (51): classify_file(), detect(), _is_noise_dir(), _is_sensitive(), _load_graphifyignore(), _looks_like_paper(), Return True if this directory name looks like a venv, cache, or dep dir., Read .graphifyignore from root **and ancestor directories**.      Returns a li (+43 more)

### Community 13 - "Cache Module"
Cohesion: 0.06
Nodes (47): _body_content(), cache_dir(), cached_files(), check_semantic_cache(), clear_cache(), file_hash(), load_cached(), Return set of file paths that have a valid cache entry (hash still matches). (+39 more)

### Community 14 - "Python Extraction"
Cohesion: 0.08
Nodes (42): collect_files(), extract_python(), Extract classes, functions, and imports from a .py file via tree-sitter AST., After merging multiple files, no internal edges should be dangling., Call-graph pass must produce INFERRED calls edges., AST-resolved call edges are deterministic and should be EXTRACTED/1.0., Same input always produces same output., run_analysis() calls compute_score() - must appear as a calls edge. (+34 more)

### Community 15 - "API Routes"
Cohesion: 0.09
Nodes (35): _git_root(), _hooks_dir(), install(), _install_hook(), Walk up to find .git directory., Return the git hooks directory, respecting core.hooksPath if set (e.g. Husky)., Install a single git hook, appending if an existing hook is present., Remove graphify section from a git hook using start/end markers. (+27 more)

### Community 16 - "Video Transcription"
Cohesion: 0.08
Nodes (34): Tests for graphify.transcribe — video/audio transcription support., ImportError propagates when faster_whisper is not installed., Empty input returns empty list without error., transcribe_all() returns cached paths for already-transcribed files., transcribe_all() warns and skips files that fail to transcribe., Empty god_nodes returns fallback prompt., GRAPHIFY_WHISPER_PROMPT env var short-circuits LLM call., Returns a topic-based prompt from god node labels — no LLM call. (+26 more)

### Community 17 - "Wiki Generation"
Cohesion: 0.15
Nodes (27): _make_graph(), Tests for graphify.wiki — Wikipedia-style article generation., God node with bad ID should not crash., Communities with more than 25 nodes show a truncation notice., test_article_navigation_footer(), test_community_article_has_audit_trail(), test_community_article_has_cross_links(), test_community_article_shows_cohesion() (+19 more)

### Community 18 - "Report Generation"
Cohesion: 0.14
Nodes (24): generate(), Mirrors export.safe_name so community hub filenames and report wikilinks always, _safe_community_name(), End-to-end pipeline test: detect → extract → build → cluster → analyze → report, Second run on unchanged corpus should produce identical node/edge counts., Run the full pipeline on the fixtures directory. Returns a dict of outputs., run_pipeline(), test_pipeline_all_nodes_have_community() (+16 more)

### Community 19 - "Authentication"
Cohesion: 0.1
Nodes (14): Auth, BasicAuth, BearerAuth, DigestAuth, NetRCAuth, Authentication handlers. Auth objects are callables that modify a request befor, Load credentials from ~/.netrc based on the request host., Base class for all authentication handlers. (+6 more)

### Community 20 - "Benchmarking"
Cohesion: 0.19
Nodes (22): _estimate_tokens(), print_benchmark(), _query_subgraph_tokens(), Token-reduction benchmark - measures how much context graphify saves vs naive fu, Print a human-readable benchmark report., Run BFS from best-matching nodes and return estimated tokens in the subgraph con, Measure token reduction: corpus tokens vs graphify query tokens.      Args:, run_benchmark() (+14 more)

### Community 21 - "Analyzer Example"
Cohesion: 0.39
Nodes (5): Analyzer, compute_score(), normalize(), Fixture: functions and methods that call each other - for call-graph extraction, run_analysis()

### Community 22 - "PHP Events Fixture"
Cohesion: 0.43
Nodes (6): EventServiceProvider, NotifyAdmins, OrderPlaced, SendWelcomeEmail, ShipOrder, UserRegistered

### Community 23 - "Objective-C Fixture"
Cohesion: 0.33
Nodes (5): Animal, -initWithName, -speak, Dog, -fetch

### Community 24 - "PHP Container Fixture"
Cohesion: 0.67
Nodes (4): AppServiceProvider, CashierGateway, PaymentGateway, StripeGateway

### Community 25 - "PHP Static Props Fixture"
Cohesion: 0.6
Nodes (2): ColorResolver, DefaultPalette

### Community 26 - "Python ML Fixture"
Cohesion: 0.5
Nodes (1): Transformer

### Community 27 - "Package Init"
Cohesion: 0.67
Nodes (1): graphify - extract · build · cluster · analyze · report.

### Community 28 - "Queue Connection"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Manifest"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Init"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "TS Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **400 isolated node(s):** `Invert communities dict: node_id -> community_id.`, `Return True if this node is a file-level hub node (e.g. 'client', 'models')`, `Return the top_n most-connected real entities - the core abstractions.      Fi`, `Find connections that are genuinely surprising - not obvious from file structure`, `Return True if this node is a manually-injected semantic concept node     rathe` (+395 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Queue Connection`** (2 nodes): `connection.ts`, `index.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Manifest`** (1 nodes): `manifest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TS Init`** (1 nodes): `index.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `CLI Installation` to `Clustering Engine`, `Graph Analysis`, `Graph Builder`, `MCP Server`, `Python Extraction`, `API Routes`, `Report Generation`, `Benchmarking`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `detect()` connect `File Detection` to `Clustering Engine`, `HTTPX Client`, `AST Extraction Core`, `MCP Server`, `Report Generation`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `add()` connect `MCP Server` to `AST Extraction Core`, `Graph Analysis`, `Worker & Cron`, `Graph Builder`, `API Handlers`, `File Detection`, `Benchmarking`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 82 inferred relationships involving `str` (e.g. with `file_hash()` and `to_html()`) actually correct?**
  _`str` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `build_from_json()` (e.g. with `.get()` and `validate_extraction()`) actually correct?**
  _`build_from_json()` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `cluster()` (e.g. with `.items()` and `_rebuild_code()`) actually correct?**
  _`cluster()` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `main()` (e.g. with `_score_nodes()` and `_subgraph_to_text()`) actually correct?**
  _`main()` has 18 INFERRED edges - model-reasoned connections that need verification._