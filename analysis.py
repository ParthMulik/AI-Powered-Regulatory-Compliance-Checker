# analysis.py (updated)
import json
import time
import re
import os
from dotenv import load_dotenv
from llm_helper import call_llm_with_fallback

load_dotenv()

# Configurable token budget (set in .env); default conservative 6000 tokens
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "6000"))
# Heuristic: approx 1 token ~ 4 characters (adjustable). Add a safety margin of 0.8 to allow prompt overhead.
CHARS_PER_TOKEN = 4
SAFETY_MARGIN = 0.8
BATCH_CHAR_LIMIT = int(LLM_MAX_TOKENS * CHARS_PER_TOKEN * SAFETY_MARGIN)

def _estimate_chars(text: str) -> int:
    return len(text)

def _make_batches_from_clauses(clauses, char_limit=BATCH_CHAR_LIMIT):
    """
    Group clause dicts/strings into batches without exceeding the char_limit
    """
    batches = []
    current = []
    current_chars = 0
    for item in clauses:
        if isinstance(item, dict):
            content = item.get('content') or item.get('clause') or ''
        else:
            content = str(item)
        size = _estimate_chars(content)
        # If single clause exceeds limit, put it alone (it will be split by LLM responsibility or flagged)
        if size >= char_limit and current:
            batches.append(current)
            current = [item]
            current_chars = size
            batches.append(current)
            current = []
            current_chars = 0
            continue
        if current_chars + size <= char_limit:
            current.append(item)
            current_chars += size
        else:
            if current:
                batches.append(current)
            current = [item]
            current_chars = size
    if current:
        batches.append(current)
    return batches

def _extract_json_from_response(response_text: str):
    """
    Try several strategies to extract JSON array/object from response.
    """
    text = response_text.strip()
    # Remove triple backticks wrappers
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text, flags=re.IGNORECASE).rstrip('```').strip()

    # Try direct json.loads
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to find the first JSON array in the text
    m = re.search(r'(\[.*\])', text, flags=re.DOTALL)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Try to find multiple JSON objects and wrap them into array
    objs = re.findall(r'(\{(?:[^{}]|\{[^}]*\})*\})', text, flags=re.DOTALL)
    if objs:
        joined = "[" + ",".join(objs) + "]"
        try:
            return json.loads(joined)
        except Exception:
            pass

    return None

def analyze_clauses(clauses, sleep_time=2):
    """
    Analyze contract clauses with batching and stronger JSON-output prompting.
    Accepts list of dicts (with 'chunk_id' and 'content') or list of strings.
    Returns a list of analysis dicts.
    """

    if not clauses:
        print("⚠️ No clauses to analyze")
        return []

    # Normalize clauses into dicts with chunk_id & content
    normalized = []
    for i, c in enumerate(clauses):
        if isinstance(c, dict):
            content = c.get('content') or c.get('clause') or ''
            cid = c.get('chunk_id', i + 1)
        else:
            content = str(c)
            cid = i + 1
        normalized.append({'chunk_id': int(cid), 'content': content})

    print(f"🔍 Preparing to analyze {len(normalized)} clauses using batched requests (char batch limit ~{BATCH_CHAR_LIMIT})")
    batches = _make_batches_from_clauses(normalized, char_limit=BATCH_CHAR_LIMIT)
    results = []

    # prompt template pieces
    regulation_choices = ["GDPR", "HIPAA", "SOX", "PCI-DSS", "FDA", "EMA", "CCPA", "Export Controls", "Employment Law", "Tax", "General Legal"]
    regulation_list_str = ", ".join(regulation_choices)

    for batch_num, batch in enumerate(batches, start=1):
        print(f"📊 Processing analysis batch {batch_num}/{len(batches)} (clauses: {len(batch)})")
        prompt = f"""
You are a concise legal compliance analyst and an expert in regulatory compliance.

Your task: read each clause provided and strictly identify if it refers to ANY regulatory frameworks,
including but not limited to: GDPR, HIPAA, PCI-DSS, SOC2, CCPA, ISO standards, and other national or international regulations.

Instructions:
1. If a regulation is explicitly named, extract it (e.g., GDPR, HIPAA).
2. If a regulation is implied (e.g., 'data protection laws in the EU'), infer the closest known framework (e.g., GDPR).
3. If no regulation is found, use 'General Legal'.
4. For each clause, return JSON with fields:
   - clause_id (integer)
   - regulation (one of: {regulation_list_str})
   - risk (short description of the primary compliance or legal risk)
   - severity (Low|Medium|High)

Be exhaustive and conservative:
- Do NOT skip any possible regulations.
- If multiple regulations apply, list them all (comma separated).

Return ONLY valid JSON (an array). No explanations, no markdown, no extra keys.

Example output for two clauses:
[{{"clause_id": 1, "regulation": "GDPR", "risk": "Personal data transfer without adequate safeguards", "severity": "High"}}, 
{{"clause_id": 2, "regulation": "General Legal", "risk": "Ambiguous termination notice period", "severity": "Medium"}}]

Now analyze the clauses below:
{{clauses}}
"""

        for c in batch:
            brief = c['content'][:900].replace("\n", " ")
            prompt += f"\nClause {c['chunk_id']}: {brief}{'...' if len(c['content']) > 900 else ''}\n"

        # Call LLM (Groq primary, Gemini fallback)
        try:
            response = call_llm_with_fallback(prompt)
        except Exception as e:
            print(f"❌ Analysis batch {batch_num} failed LLM call: {e}")
            # create error entries for this batch
            for c in batch:
                results.append({
                    "clause_id": c['chunk_id'],
                    "regulation": "Analysis Error",
                    "risk": f"LLM call failed: {str(e)[:200]}",
                    "severity": "Unknown",
                    "clause": c['content']
                })
            continue

        # Try to extract JSON
        parsed = _extract_json_from_response(response)

        if parsed is None:
            print(f"❌ JSON parsing error in batch {batch_num}; raw preview:\n{response[:800]}...")
            for c in batch:
                results.append({
                    "clause_id": c['chunk_id'],
                    "regulation": "Analysis Error",
                    "risk": "JSON parsing failed for LLM response",
                    "severity": "Unknown",
                    "clause": c['content']
                })
            # small wait before next batch
            if batch_num < len(batches):
                time.sleep(sleep_time)
            continue

        # parsed should be a list of objects
        if isinstance(parsed, dict):
            # if a single object returned, wrap it
            parsed = [parsed]

        # associate results back to clause_id (prefer explicit id from model, else by order)
        for idx, item in enumerate(parsed):
            # if there is a clause_id provided, use it; otherwise map to batch order
            cid = item.get('clause_id')
            if cid is None:
                # map by position to actual clause id
                if idx < len(batch):
                    cid = batch[idx]['chunk_id']
                else:
                    cid = batch[0]['chunk_id']  # fallback
            regulation = item.get('regulation', 'General Legal')
            risk = item.get('risk', item.get('risk_description', 'Risk analysis incomplete'))
            severity = item.get('severity', item.get('risk_severity', 'Medium'))
            # Append
            matching_clause = next((c for c in batch if c['chunk_id'] == int(cid)), None)
            clause_text = matching_clause['content'] if matching_clause else (item.get('clause', ''))
            results.append({
                "clause_id": int(cid),
                "regulation": regulation,
                "risk": risk,
                "severity": severity,
                "clause": clause_text
            })

        # wait between batches (if applicable)
        if batch_num < len(batches):
            print(f"⏱️ Waiting {sleep_time}s before next batch...")
            time.sleep(sleep_time)

    print(f"✅ Analysis complete: {len(results)} results generated")
    return results
