# ingestion.py (updated robust chunking)
import os
import fitz  # PyMuPDF
import re
from dotenv import load_dotenv
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# ---------- PDF extraction ----------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using PyMuPDF (fitz)."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    doc.close()
    return text.strip()

# ---------- Preprocessing ----------
def preprocess_contract_text(text: str) -> str:
    """Normalize text and promote headings to clear section markers."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    patterns = [
        (r'\n\s*(\d+)\.\s*([A-Z][A-Z\s]{5,})', r'\n\n--- SECTION \1: \2 ---\n'),
        (r'\n\s*(ARTICLE\s+[IVX]+)', r'\n\n--- \1 ---\n'),
        (r'\n\s*(WHEREAS,)', r'\n\n--- RECITAL ---\n\1'),
        (r'\n\s*(NOW THEREFORE,)', r'\n\n--- AGREEMENT ---\n\1'),
        (r'\n\s*(IN WITNESS WHEREOF)', r'\n\n--- EXECUTION ---\n\1'),
        (r'\n\s*(TERMINATION|TERM & TERMINATION|TERM AND TERMINATION)\b', r'\n\n--- TERMINATION ---\n\1'),
        (r'\n\s*(FEES & PAYMENTS|PAYMENT|FEES)\b', r'\n\n--- PAYMENT ---\n\1'),
        (r'\n\s*(CONFIDENTIALITY|CONFIDENTIAL)\b', r'\n\n--- CONFIDENTIALITY ---\n\1'),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.MULTILINE)
    return text

# ---------- Classification ----------
def classify_chunk_content(chunk_text: str) -> dict:
    """Classify chunk content for primary type and regulatory relevance."""
    chunk_lower = chunk_text.lower()
    classifications = {
        'definitions': ['definition', 'means', 'shall mean', 'defined as', 'refers to'],
        'payment': ['payment', 'pay', 'invoice', 'fee', 'cost', 'price', 'compensation', 'salary'],
        'termination': ['terminate', 'termination', 'end', 'expiry', 'expire', 'dissolution'],
        'liability': ['liable', 'liability', 'damages', 'loss', 'harm', 'injury', 'responsible for'],
        'confidentiality': ['confidential', 'non-disclosure', 'proprietary', 'trade secret'],
        'intellectual_property': ['intellectual property', 'copyright', 'patent', 'trademark', 'ip'],
        'data_protection': ['data', 'privacy', 'personal information', 'gdpr', 'hipaa', 'data protection'],
        'performance': ['performance', 'deliver', 'service', 'obligation', 'duty', 'responsibility'],
        'compliance': ['comply', 'compliance', 'regulation', 'law', 'legal', 'regulatory', 'audit'],
        'dispute': ['dispute', 'disagreement', 'arbitration', 'mediation', 'litigation', 'court'],
        'force_majeure': ['force majeure', 'act of god', 'unforeseeable', 'beyond control'],
        'assignment': ['assign', 'assignment', 'transfer', 'delegate'],
        'amendment': ['amend', 'amendment', 'modify', 'change', 'alter'],
        'governing_law': ['governing law', 'jurisdiction', 'governed by', 'applicable law']
    }

    scores = {cat: sum(1 for kw in kws if kw in chunk_lower) for cat, kws in classifications.items()}
    primary_type = max(scores.keys(), key=scores.get) if scores else 'general'

    regulatory_indicators = {
        'high': ['gdpr', 'hipaa', 'sox', 'pci', 'regulation', 'compliance', 'audit', 'export control', 'sanction'],
        'medium': ['law', 'legal', 'jurisdiction', 'court', 'penalty', 'fine'],
        'low': ['policy', 'procedure', 'guideline', 'standard']
    }

    regulatory_relevance = 'minimal'
    for level, indicators in regulatory_indicators.items():
        if any(ind in chunk_lower for ind in indicators):
            regulatory_relevance = level
            break

    return {
        'primary_type': primary_type,
        'secondary_types': [k for k in scores.keys() if k != primary_type],
        'regulatory_relevance': regulatory_relevance,
        'word_count': len(chunk_text.split()),
        'has_legal_terms': any(term in chunk_lower for term in ['shall', 'hereby', 'whereas', 'therefore', 'pursuant'])
    }

# ---------- Semantic chunking ----------
def create_semantic_chunks(text: str, breakpoint_threshold_type: str = "percentile", breakpoint_threshold_amount: float | None = None):
    """Robust semantic chunking for contracts."""
    print("🧠 Initializing semantic embeddings model...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    if breakpoint_threshold_amount is None and breakpoint_threshold_type == "percentile":
        breakpoint_threshold_amount = 0.95

    print("🔍 Creating semantic chunker...")
    semantic_chunker = SemanticChunker(
        embeddings=embeddings,
        buffer_size=2,
        breakpoint_threshold_type=breakpoint_threshold_type,
        breakpoint_threshold_amount=breakpoint_threshold_amount,
        min_chunk_size=200
    )

    processed_text = preprocess_contract_text(text)

    # ---------- Split by headings first ----------
    sections = re.split(r'--- [A-Z ]+ ---', processed_text)
    all_chunks = []

    MAX_CHARS = 2500
    MIN_CHARS = 200
    sentence_regex = re.compile(r'(?<=[.?!])\s+')

    for sec in sections:
        if not sec.strip():
            continue

        # Semantic chunking within section
        try:
            docs = semantic_chunker.create_documents([sec])
            raw_chunks = [doc.page_content.strip() for doc in docs if doc.page_content.strip()]
        except Exception:
            raw_chunks = [sec.strip()]

        # Merge tiny chunks and split large chunks
        merged = []
        for piece in raw_chunks:
            if not merged:
                merged.append(piece)
                continue
            if len(piece) < MIN_CHARS:
                merged[-1] = (merged[-1] + "\n\n" + piece).strip()
            else:
                merged.append(piece)

        # Split oversized chunks by sentences
        for piece in merged:
            if len(piece) > MAX_CHARS:
                sentences = sentence_regex.split(piece)
                current = ""
                for s in sentences:
                    if not current:
                        current = s
                    elif len(current) + len(s) + 1 <= MAX_CHARS:
                        current += " " + s
                    else:
                        all_chunks.append(current.strip())
                        current = s
                if current:
                    all_chunks.append(current.strip())
            else:
                all_chunks.append(piece.strip())

    # ---------- Add metadata ----------
    semantic_chunks = []
    for i, chunk_text in enumerate(all_chunks):
        if len(chunk_text.strip()) < 50:
            continue
        classification = classify_chunk_content(chunk_text)
        semantic_chunks.append({
            'chunk_id': i + 1,
            'content': chunk_text,
            'length': len(chunk_text),
            'primary_type': classification['primary_type'],
            'secondary_types': classification['secondary_types'],
            'regulatory_relevance': classification['regulatory_relevance'],
            'word_count': classification['word_count'],
            'has_legal_terms': classification['has_legal_terms'],
            'preview': chunk_text[:300] + ('...' if len(chunk_text) > 300 else '')
        })

    print(f"   🔹 Final semantic chunks: {len(semantic_chunks)}")
    return semantic_chunks

# ---------- Simple fallback ----------
def simple_fallback_chunking(text: str):
    """Paragraph-based fallback chunking."""
    print("🔄 Using simple paragraph-based chunking as fallback")
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    for i, paragraph in enumerate(paragraphs):
        if len(paragraph) > 3000:
            sentences = re.split(r'(?<=[.?!])\s+', paragraph)
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 > 2000:
                    if current_chunk:
                        classification = classify_chunk_content(current_chunk)
                        chunks.append({
                            'chunk_id': len(chunks) + 1,
                            'content': current_chunk.strip(),
                            'length': len(current_chunk),
                            'primary_type': classification['primary_type'],
                            'secondary_types': classification['secondary_types'],
                            'regulatory_relevance': classification['regulatory_relevance'],
                            'word_count': classification['word_count'],
                            'has_legal_terms': classification['has_legal_terms'],
                            'preview': current_chunk[:300] + '...'
                        })
                    current_chunk = sentence
                else:
                    current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
            if current_chunk:
                classification = classify_chunk_content(current_chunk)
                chunks.append({
                    'chunk_id': len(chunks) + 1,
                    'content': current_chunk.strip(),
                    'length': len(current_chunk),
                    'primary_type': classification['primary_type'],
                    'secondary_types': classification['secondary_types'],
                    'regulatory_relevance': classification['regulatory_relevance'],
                    'word_count': classification['word_count'],
                    'has_legal_terms': classification['has_legal_terms'],
                    'preview': current_chunk[:300] + '...'
                })
        else:
            classification = classify_chunk_content(paragraph)
            chunks.append({
                'chunk_id': i + 1,
                'content': paragraph,
                'length': len(paragraph),
                'primary_type': classification['primary_type'],
                'secondary_types': classification['secondary_types'],
                'regulatory_relevance': classification['regulatory_relevance'],
                'word_count': classification['word_count'],
                'has_legal_terms': classification['has_legal_terms'],
                'preview': paragraph[:300] + ('...' if len(paragraph) > 300 else '')
            })
    return chunks

# ---------- Ingest function ----------
def ingest_contract(pdf_path: str, chunking_method: str = "percentile"):
    """Main entry: extract clauses from contract."""
    print(f"📄 Processing PDF: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        raise ValueError("No text could be extracted from the PDF")
    print(f"📝 Extracted {len(raw_text):,} characters from PDF")
    try:
        semantic_chunks = create_semantic_chunks(raw_text, breakpoint_threshold_type=chunking_method)
    except Exception as e:
        print(f"❌ Semantic chunking failed: {e}")
        print("🔄 Falling back to simple chunking...")
        return simple_fallback_chunking(raw_text)

    if not semantic_chunks:
        print("⚠️ No semantic chunks created, using fallback")
        return simple_fallback_chunking(raw_text)

    print(f"🎯 Semantic Chunking Results: {len(semantic_chunks)} chunks")
    return semantic_chunks
