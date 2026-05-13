"""
LLM Helper Module
Handles API calls to Groq and Gemini with fallback support
Works with config.py for centralized configuration
"""

import requests
import google.generativeai as genai
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

# Import configuration
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROQ_BASE_URL,
    ModelConfig,
    FallbackChain,
    APISettings,
    SafetyConfig,
    PromptTemplates,
    BatchConfig,
    LogConfig,
)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ==========================================
# CORE API FUNCTIONS
# ==========================================

def call_groq(
    prompt: str, 
    model: str = ModelConfig.DEFAULT_GROQ, 
    max_retries: int = APISettings.MAX_RETRIES
) -> str:
    """
    Call Groq REST API.
    
    Args:
        prompt: The prompt to send
        model: Model to use (default from config)
        max_retries: Number of retries
    
    Returns:
        Model response text
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in environment variables")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": APISettings.TEMPERATURE,
        "max_tokens": APISettings.MAX_TOKENS,
    }
    
    for attempt in range(max_retries + 1):
        try:
            if LogConfig.LOG_API_CALLS:
                if attempt == 0:
                    print(f"🤖 Calling Groq: {model}")
                elif LogConfig.LOG_RETRIES:
                    print(f"🔄 Groq retry {attempt}")
            
            resp = requests.post(
                GROQ_BASE_URL, 
                headers=headers, 
                json=payload, 
                timeout=APISettings.GROQ_TIMEOUT
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
                    else:
                        raise ValueError("Empty response from Groq")
                else:
                    raise ValueError("Invalid response format from Groq")
                    
            elif resp.status_code == 429:
                wait_time = min(APISettings.RETRY_BACKOFF_BASE ** attempt, APISettings.MAX_BACKOFF)
                if LogConfig.LOG_RETRIES:
                    print(f"⏱ Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            else:
                if LogConfig.VERBOSE_ERRORS:
                    print(f"❌ Groq API Error: {resp.status_code}")
                if attempt == max_retries:
                    resp.raise_for_status()
                time.sleep(APISettings.RATE_LIMIT_WAIT / 4)
                
        except requests.exceptions.Timeout:
            if LogConfig.VERBOSE_ERRORS:
                print(f"⏱ Groq timeout (attempt {attempt + 1})")
            if attempt == max_retries:
                raise
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            if LogConfig.VERBOSE_ERRORS:
                print(f"❌ Groq request error: {e}")
            if attempt == max_retries:
                raise
            time.sleep(1)
    
    raise Exception("Groq API failed after all retries")


def call_gemini(
    prompt: str, 
    model: str = ModelConfig.DEFAULT_GEMINI, 
    max_retries: int = APISettings.MAX_RETRIES,
    safety_settings: List[dict] = None
) -> str:
    """
    Call Gemini API with safety settings.
    
    Args:
        prompt: The prompt to send
        model: Model to use (default from config)
        max_retries: Number of retries
        safety_settings: Custom safety settings (default from config)
    
    Returns:
        Model response text
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment variables")
    
    # Use default safety settings if not provided
    if safety_settings is None:
        safety_settings = SafetyConfig.DEFAULT
    
    # Wrap prompt with compliance context
    compliance_prompt = PromptTemplates.COMPLIANCE_CONTEXT.format(prompt=prompt)
    
    for attempt in range(max_retries + 1):
        try:
            if LogConfig.LOG_API_CALLS:
                if attempt == 0:
                    print(f"🔄 Calling Gemini: {model}")
                elif LogConfig.LOG_RETRIES:
                    print(f"🔄 Gemini retry {attempt}")
            
            generation_config = genai.types.GenerationConfig(
                temperature=APISettings.TEMPERATURE,
                max_output_tokens=APISettings.MAX_TOKENS,
            )
            
            gemini_model = genai.GenerativeModel(model)
            response = gemini_model.generate_content(
                compliance_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            if response and response.candidates:
                candidate = response.candidates[0]
                
                if not candidate.content.parts:
                    if LogConfig.VERBOSE_ERRORS:
                        print(f"⚠ Gemini blocked. Safety ratings: {candidate.safety_ratings}")
                    
                    # Auto-fallback to backup model
                    if attempt == 0 and model == ModelConfig.DEFAULT_GEMINI:
                        print(f"🔄 Switching to backup: {ModelConfig.BACKUP_GEMINI}")
                        return call_gemini(
                            prompt, 
                            model=ModelConfig.BACKUP_GEMINI, 
                            max_retries=0,
                            safety_settings=safety_settings
                        )
                    
                    return "[Gemini response blocked due to safety filters]"
                
                if response.text and response.text.strip():
                    return response.text.strip()
                else:
                    if LogConfig.VERBOSE_ERRORS:
                        print("⚠ Gemini returned no text")
                    return "[Gemini returned no usable text]"
            
            else:
                if LogConfig.VERBOSE_ERRORS:
                    print("⚠ Gemini returned no candidates")
                return "[Gemini returned empty response]"

        except Exception as e:
            error_msg = str(e).lower()
            
            # Auto-switch to backup on safety issues
            if ("blocked" in error_msg or "safety" in error_msg) and attempt == 0:
                if model == ModelConfig.DEFAULT_GEMINI:
                    print(f"🔄 Safety issue. Switching to backup: {ModelConfig.BACKUP_GEMINI}")
                    return call_gemini(
                        prompt, 
                        model=ModelConfig.BACKUP_GEMINI, 
                        max_retries=0,
                        safety_settings=safety_settings
                    )
            
            if LogConfig.VERBOSE_ERRORS:
                print(f"❌ Gemini error: {e}")
            
            if attempt == max_retries:
                raise Exception(f"Gemini API error: {str(e)}")
            
            time.sleep(min(APISettings.RETRY_BACKOFF_BASE ** attempt, APISettings.MAX_BACKOFF))
    
    raise Exception("Gemini API failed after all retries")


# ==========================================
# FALLBACK ORCHESTRATION
# ==========================================

def call_llm_with_fallback(
    prompt: str, 
    groq_model: str = ModelConfig.DEFAULT_GROQ, 
    gemini_model: str = ModelConfig.DEFAULT_GEMINI,
    fallback_chain: List[Tuple[str, str]] = None
) -> str:
    """
    Call LLM with configurable fallback chain.
    
    ✅ BACKWARD COMPATIBLE: Works exactly like your old code!
    
    Args:
        prompt: The prompt to send
        groq_model: Groq model to use
        gemini_model: Gemini model to use
        fallback_chain: Custom fallback chain (default: STANDARD)
    
    Returns:
        Model response text
    """
    if not prompt or not prompt.strip():
        raise ValueError("Empty prompt provided")
    
    # Use standard fallback chain if not specified
    if fallback_chain is None:
        fallback_chain = FallbackChain.STANDARD
    
    last_error = None
    
    for idx, (provider, model) in enumerate(fallback_chain):
        try:
            if provider == "groq":
                return call_groq(prompt, model)
            elif provider == "gemini":
                return call_gemini(prompt, model)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
        except Exception as e:
            last_error = e
            if LogConfig.VERBOSE_ERRORS:
                print(f"⚠ {provider.upper()} failed: {e}")
            
            # If this is the last provider, raise the error
            if idx == len(fallback_chain) - 1:
                raise Exception(f"All providers in fallback chain failed. Last error: {last_error}")
            
            # Otherwise, continue to next provider
            if LogConfig.LOG_API_CALLS:
                next_provider, next_model = fallback_chain[idx + 1]
                print(f"🔄 Trying next in chain: {next_provider.upper()} ({next_model})")
    
    raise Exception(f"Fallback chain exhausted. Last error: {last_error}")


# ==========================================
# PARALLEL PROCESSING
# ==========================================

def process_prompts_parallel(
    prompts: List[str],
    max_workers: int = APISettings.DEFAULT_MAX_WORKERS,
    groq_model: str = ModelConfig.DEFAULT_GROQ,
    gemini_model: str = ModelConfig.DEFAULT_GEMINI,
    show_progress: bool = LogConfig.SHOW_PROGRESS
) -> List[Tuple[int, Optional[str]]]:
    """
    Process multiple prompts in parallel (3x faster).
    
    Args:
        prompts: List of prompts to process
        max_workers: Number of parallel workers (default: 3)
        groq_model: Groq model to use
        gemini_model: Gemini model to use
        show_progress: Whether to show progress
    
    Returns:
        List of tuples (index, result) in original order
    """
    if not prompts:
        return []
    
    # Enforce max workers limit
    max_workers = min(max_workers, APISettings.MAX_WORKERS_LIMIT)
    
    results = []
    total = len(prompts)
    
    if show_progress:
        print(f"🚀 Processing {total} prompts with {max_workers} parallel workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                call_llm_with_fallback, 
                prompt, 
                groq_model, 
                gemini_model
            ): idx 
            for idx, prompt in enumerate(prompts)
        }
        
        completed = 0
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            completed += 1
            
            try:
                result = future.result()
                results.append((idx, result))
                if show_progress:
                    print(f"✅ Completed {completed}/{total} (prompt {idx})")
            except Exception as e:
                if LogConfig.VERBOSE_ERRORS:
                    print(f"❌ Prompt {idx} failed: {e}")
                results.append((idx, None))
    
    results.sort(key=lambda x: x[0])
    
    success_count = sum(1 for _, r in results if r is not None)
    if show_progress:
        print(f"✨ Parallel processing complete: {success_count}/{total} successful")
    
    return results


# ==========================================
# BATCHING UTILITIES
# ==========================================

def batch_small_prompts(
    prompts: List[str],
    max_batch_size: int = BatchConfig.MAX_BATCH_SIZE,
    separator: str = BatchConfig.BATCH_SEPARATOR
) -> List[str]:
    """
    Batch small prompts to reduce API calls (5-6x faster).
    
    Args:
        prompts: List of prompts to batch
        max_batch_size: Maximum characters per batch
        separator: String to separate prompts
    
    Returns:
        List of batched prompts
    """
    if not prompts:
        return []
    
    batches = []
    current_batch = []
    current_size = 0
    
    for prompt in prompts:
        prompt_size = len(prompt)
        
        if prompt_size > max_batch_size:
            if current_batch:
                batches.append(separator.join(current_batch))
                current_batch = []
                current_size = 0
            batches.append(prompt)
            continue
        
        if current_size + prompt_size + len(separator) > max_batch_size:
            if current_batch:
                batches.append(separator.join(current_batch))
            current_batch = [prompt]
            current_size = prompt_size
        else:
            current_batch.append(prompt)
            current_size += prompt_size + len(separator)
    
    if current_batch:
        batches.append(separator.join(current_batch))
    
    if LogConfig.LOG_API_CALLS:
        print(f"📦 Batched {len(prompts)} prompts into {len(batches)} batches")
    
    return batches


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def call_with_quality_preset(prompt: str) -> str:
    """Use quality-focused configuration (Groq Quality → Gemini Pro)"""
    return call_llm_with_fallback(
        prompt,
        fallback_chain=FallbackChain.QUALITY_FIRST
    )


def call_with_speed_preset(prompt: str) -> str:
    """Use speed-focused configuration (Fast models)"""
    return call_llm_with_fallback(
        prompt,
        fallback_chain=FallbackChain.SPEED_FIRST
    )


def call_gemini_only(prompt: str) -> str:
    """Use only Gemini models (bypass Groq)"""
    return call_llm_with_fallback(
        prompt,
        fallback_chain=FallbackChain.GEMINI_ONLY
    )