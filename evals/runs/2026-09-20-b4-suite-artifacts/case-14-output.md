**No retrieval tool was available this run. Everything below is training knowledge, not cited evidence. Nothing was looked up, and nothing here should be read as live-sourced.** My knowledge cutoff is January 2026 and today is 2026-09-20, so anything published in the last ~8 months is missing. I can re-run this once web or search access is available.

---

## Question

What are the current best practices for chunking documents in a RAG pipeline?

**Narrowing:** I assume text-heavy documents (reports, manuals, contracts, web pages) and an embedding-plus-vector-search retriever, with an LLM generating the answer. I don't cover multimodal or tabular chunking in depth.

## Answer

The most defensible position from what I recall is that there is no single best chunking strategy, and the field has moved away from "pick the perfect chunk size."

1. **Start with a simple baseline.** Use recursive, structure-respecting splitting at roughly 200–500 tokens. Add 0–20% overlap only if you can show it helps.
2. **Respect document structure first.** Split on headings, sections, paragraphs, and tables before falling back to size limits. Attach structural metadata (title, heading path, document type) to every chunk.
3. **Decouple the unit you retrieve from the unit you hand to the LLM.** Small-to-big, parent-document, and sentence-window retrieval do this. It sidesteps the tension between precise matching and sufficient context.
4. **Restore lost context at index time.** Contextual retrieval (a short LLM-written situating blurb per chunk), late chunking, or heading-path prefixes each address chunks that are ambiguous in isolation.
5. **Combine retrieval methods.** Hybrid search (dense plus BM25) and reranking often move results more than fine-tuning chunk boundaries.
6. **Tune chunking against your own evaluation set.** Published comparisons disagree, and the winner depends on corpus and query type.

Items 1–3 rest on consistent, widely repeated practice. Items 4–5 rest on specific published claims I recall but cannot re-verify. Item 6 is inference from the disagreement in the literature.

## By sub-question

### 1. What are the baseline strategies, and which hold up?

- **Fixed-size splitting** (by characters or tokens) is the simplest option. It is a reasonable baseline but cuts mid-sentence and mid-thought.
- **Recursive splitting** (paragraph, then sentence, then word, as in LangChain's `RecursiveCharacterTextSplitter`) is the common default. It respects natural boundaries where it can.
- **Structure-aware splitting** uses Markdown or HTML headings, page breaks, and table boundaries. Where documents have real structure, this is generally preferred over blind size-based splitting.
- **Semantic chunking** splits where embedding similarity between adjacent sentences drops.
  - **Disagreement:** I recall a Vectara-associated paper (Qu et al., 2024) finding that semantic chunking's extra compute did not deliver consistent gains over fixed-size chunking. I also recall Chroma's chunking evaluation (Smith and Troynikov, 2024) reporting that some embedding-based and LLM-based chunkers performed well while a simple recursive splitter at moderate sizes was a strong baseline. These are not contradictory, but they show the evidence doesn't support "semantic chunking is better" as a general claim.
- **Page-level chunking:** I recall an NVIDIA write-up reporting that page-level chunking scored best on their document set. I have low confidence in the details, and it likely depends on documents where pages are meaningful units (PDFs, filings).

### 2. What chunk size and overlap should I use?

- Common practice is a few hundred tokens (about 200–500) per chunk, with a wide accepted range.
- Smaller chunks give more precise matching but lose context. Larger chunks keep context but dilute the embedding and burn LLM context budget.
- Overlap is conventional (10–20% is often cited), but I recall the Chroma work finding overlap did not reliably help and could reduce efficiency. Treat overlap as a hypothesis to test, not a default to trust.
- **Inference:** the right size depends on query type. Factoid lookups favor small chunks, and questions needing multi-sentence reasoning favor larger ones.

### 3. How do I stop chunks from losing their context?

- **Contextual retrieval (Anthropic, Sept 2024):** an LLM prepends a short document-situating summary to each chunk before embedding and BM25 indexing. I recall reported reductions in failed retrievals of about 35% (contextual embeddings alone), 49% (with contextual BM25), and 67% (adding reranking). I'm reasonably confident of these figures but they are the vendor's own results on its own test sets, and I have not re-checked them.
- **Late chunking (Jina AI, Günther et al., 2024):** run a long-context embedding model over the whole document, then pool token embeddings per chunk, so each chunk embedding carries document-wide context. It needs a long-context embedding model and is not a drop-in change.
- **Heading-path or title prefixes** are a cheap, non-LLM version of the same idea.
- **Propositional chunking** ("Dense X Retrieval," Chen et al., 2023) rewrites text into atomic, self-contained propositions. I recall reported retrieval gains but with substantial preprocessing cost.
- **Hierarchical or tree summarization** (RAPTOR, Sarthi et al., 2024) builds summary layers over chunks, mainly for questions spanning a whole document.

### 4. How do I decouple retrieval units from generation units?

Small-to-big, parent-document, and sentence-window retrieval (all implemented in LangChain and LlamaIndex) embed small chunks for precise matching but return the surrounding parent section or window to the LLM. This is well-established practice rather than a contested research claim, and it is the most common way to escape the small-versus-large tradeoff.

### 5. What else matters as much as the chunk boundaries?

- **Metadata:** source, section path, date, and document type enable filtering and citation.
- **Hybrid search and reranking:** I recall these consistently appearing as high-impact additions in practitioner and vendor reports, including the Anthropic figures above.
- **Special content:** tables, code, and lists usually need their own handling (keep a table whole, or serialize it with its header). Naive text splitting often breaks them.
- **Evaluation:** measure retrieval directly (recall@k or MRR on a labeled question set) before judging end-to-end answer quality, so you can separate chunking effects from generation effects.

### Inference for structured governing documents

For documents with hierarchical structure and cross-references (statutes, bylaws, contracts), I infer that heading-path metadata and parent-document retrieval matter more than boundary tuning. No source I recall tests this directly.

## Confidence & gaps

| Claim | Confidence | Why |
|---|---|---|
| Recursive/structure-aware splitting is a sound baseline | High | Widely repeated, matches common tooling defaults |
| Small-to-big / parent retrieval helps the size tradeoff | Medium-high | Common practice, but I can't point to a decisive benchmark |
| Semantic chunking is not reliably better | Medium | Rests on a small number of studies I recall, with disagreement |
| Anthropic contextual retrieval percentages | Medium | Recalled figures, vendor-run evaluation, not re-checked |
| Overlap does or doesn't help | Low | Conventional practice and my recollection of Chroma's finding point in different directions |
| Page-level chunking wins | Low | Vague recollection, likely corpus-specific |

**Gaps:**
- Nothing after January 2026. Long-context models, cheaper contextual indexing, and agentic or iterative retrieval may have changed practice.
- I did not retrieve or re-read any paper, so every figure above may be misremembered.
- No head-to-head study I know of controls for corpus type, embedding model, and query type at once.

**Strongest counter-position:** with long-context models (hundreds of thousands to millions of tokens), some argue chunking matters less. You can retrieve whole documents, or skip retrieval for small corpora. This weakens the case for elaborate chunking in some settings, but cost, latency, and accuracy degradation over long contexts still favor retrieval for large corpora. I hold that latter view with only moderate confidence.

**Bias check:** I lean toward "hybrid plus reranking plus context restoration" because it appears in many vendor and practitioner posts. Those sources have an incentive to promote their own techniques, and I may be overweighting them.

## Sources

Every entry below is recalled from training data, was not retrieved this run, and is **unverified**. Search by title and check the actual text and numbers before relying on any of them.

- **Anthropic, "Introducing Contextual Retrieval" (Sept 2024)** — contextual embeddings and contextual BM25, with the recalled 35% / 49% / 67% failure-rate reductions.
- **Smith and Troynikov (Chroma), "Evaluating Chunking Strategies for Retrieval" (2024)** — comparison of chunkers on recall-style metrics; the source for my notes on overlap and recursive-splitter strength.
- **Qu et al., "Is Semantic Chunking Worth the Computational Cost?" (2024)** — the source for the claim that semantic chunking's gains are inconsistent.
- **Günther et al. (Jina AI), "Late Chunking" (2024)** — contextual chunk embeddings from long-context models.
- **Chen et al., "Dense X Retrieval: What Retrieval Granularity Should We Use?" (2023)** — propositional chunking.
- **Sarthi et al., "RAPTOR" (2024)** — tree-structured summarization for retrieval.
- **NVIDIA technical blog on chunking strategies (2024)** — page-level chunking result. Title and details are low-confidence recall.
- **LangChain and LlamaIndex documentation** — recursive splitters, parent-document retrievers, sentence-window retrieval. Cited as the source for what these tools implement.

**Next step:** if you give me a search or fetch tool, I'll re-run this with retrieved sources. If you have a specific corpus, I'd narrow the brief to that document type.