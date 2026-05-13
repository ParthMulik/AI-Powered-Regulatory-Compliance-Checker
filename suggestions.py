# suggestions.py (updated)
import json
import time
import re
import os
from dotenv import load_dotenv
from llm_helper import call_llm_with_fallback

load_dotenv()

# Use same token char budget as analysis
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "6000"))
CHARS_PER_TOKEN = 4
SAFETY_MARGIN = 0.8
BATCH_CHAR_LIMIT = int(LLM_MAX_TOKENS * CHARS_PER_TOKEN * SAFETY_MARGIN)

def _estimate_chars(text: str) -> int:
    return len(text)

def _make_batches(items, char_limit=BATCH_CHAR_LIMIT):
    batches = []
    current = []
    current_chars = 0
    for it in items:
        content = it.get('clause', it.get('content', '')) if isinstance(it, dict) else str(it)
        size = _estimate_chars(content)
        if size >= char_limit and current:
            batches.append(current)
            batches.append([it])
            current = []
            current_chars = 0
            continue
        if current_chars + size <= char_limit:
            current.append(it)
            current_chars += size
        else:
            if current:
                batches.append(current)
            current = [it]
            current_chars = size
    if current:
        batches.append(current)
    return batches

def _extract_json_from_response(response_text: str):
    # same strategy as analysis
    text = response_text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text, flags=re.IGNORECASE).rstrip('```').strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'(\[.*\])', text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    objs = re.findall(r'(\{(?:[^{}]|\{[^}]*\})*\})', text, flags=re.DOTALL)
    if objs:
        try:
            return json.loads("[" + ",".join(objs) + "]")
        except Exception:
            pass
    return None

def generate_suggestions(analysis_results, sleep_time=2):
    """
    For each analysis result item (which should include clause_id and clause text),
    produce a 'suggestion' string. Batched to respect token limits.
    """
    if not analysis_results:
        print("⚠️ No analysis results to generate suggestions from")
        return []

    # Normalize: each entry should have clause_id and clause text
    normalized = []
    for r in analysis_results:
        cid = r.get('clause_id') or r.get('Clause_ID') or None
        clause_text = r.get('clause') or r.get('Clause_Text') or r.get('content') or ''
        normalized.append({'clause_id': int(cid) if cid else None, 'clause': clause_text, 'analysis': r})

    batches = _make_batches(normalized, char_limit=BATCH_CHAR_LIMIT)
    suggestions = []

    for batch_num, batch in enumerate(batches, start=1):
        print(f"🔧 Processing suggestion batch {batch_num}/{len(batches)} (items: {len(batch)})")
        prompt = (
            "You are a compliance advisor. For each clause provided, produce a concise, actionable suggestion that can reduce the identified risk.\n"
            "Return ONLY a JSON array where each object includes these fields:\n"
            " - clause_id (integer)\n"
            " - suggestion (string, reasonably short but actionable)\n\n"
            "Example:\n"
            '[{"clause_id": 5, "suggestion": "Limit force majeure to exclude negligence, and require notice within 10 days"}, '
            '{"clause_id": 6, "suggestion": "Add a 30-day cure period for payment defaults before termination"}]\n\n'
            "Now provide suggestions for the clauses below:\n"
        )
        for it in batch:
            brief = it['clause'][:900].replace("\n", " ")
            prompt += f"\nClause {it.get('clause_id')}: {brief}{'...' if len(it['clause']) > 900 else ''}\n"

        try:
            response = call_llm_with_fallback(prompt)
        except Exception as e:
            print(f"❌ Suggestion batch {batch_num} failed LLM call: {e}")
            for it in batch:
                suggestions.append({
                    "clause_id": it.get('clause_id'),
                    "suggestion": f"Suggestion generation failed: {str(e)[:200]}",
                    "clause": it.get('clause')
                })
            continue

        parsed = _extract_json_from_response(response)
        if parsed is None:
            print(f"❌ JSON parsing error in suggestion batch {batch_num}; raw preview:\n{response[:800]}...")
            for it in batch:
                suggestions.append({
                    "clause_id": it.get('clause_id'),
                    "suggestion": "Suggestion generation failed: JSON parsing error",
                    "clause": it.get('clause')
                })
            if batch_num < len(batches):
                time.sleep(sleep_time)
            continue

        if isinstance(parsed, dict):
            parsed = [parsed]

        for idx, obj in enumerate(parsed):
            cid = obj.get('clause_id')
            if cid is None and idx < len(batch):
                cid = batch[idx].get('clause_id')
            suggestion_text = obj.get('suggestion') or obj.get('advice') or 'No suggestion generated'
            clause_text = next((b['clause'] for b in batch if b.get('clause_id') == cid), batch[idx].get('clause') if idx < len(batch) else '')
            suggestions.append({
                "clause_id": cid,
                "suggestion": suggestion_text,
                "clause": clause_text
            })

        if batch_num < len(batches):
            print(f"⏱️ Waiting {sleep_time}s before next suggestion batch...")
            time.sleep(sleep_time)

    print(f"✅ Suggestion generation complete: {len(suggestions)} suggestions")
    return suggestions
