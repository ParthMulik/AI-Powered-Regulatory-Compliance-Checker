"""
LLM Configuration Module
Centralized configuration for all LLM models, API settings, and safety configurations
"""

import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

# ==========================================
# API KEYS & CREDENTIALS
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==========================================
# API ENDPOINTS
# ==========================================
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==========================================
# MODEL CONFIGURATIONS
# ==========================================

class ModelConfig:
    """Model configuration presets"""
    
    # Groq Models
    GROQ_MODELS = {
        "quality": "llama-3.3-70b-versatile",      # Best quality (default)
        "balanced": "llama-3.1-70b-versatile",     # Good balance
        "fast": "llama-3.1-8b-instant",            # Fastest, lower quality
        "mixtral": "mixtral-8x7b-32768",           # Alternative quality model
    }
    
    # Gemini Models
    GEMINI_MODELS = {
        "primary": "gemini-2.5-pro",                # Best for compliance (default)
        "experimental": "gemini-2.0-flash-exp",     # Backup/experimental
        "pro": "gemini-2.5-flash",                  # Alternative quality model
        "lite": "gemini-2.5-flash-lite",            # Fastest, simple tasks
        "thinking": "gemini-2.5-flash-thinking-exp", # Advanced reasoning
    }
    
    # Default selections
    DEFAULT_GROQ = GROQ_MODELS["quality"]
    DEFAULT_GEMINI = GEMINI_MODELS["primary"]
    BACKUP_GEMINI = GEMINI_MODELS["experimental"]


# ==========================================
# FALLBACK CHAIN CONFIGURATION
# ==========================================

class FallbackChain:
    """Define fallback order for different scenarios"""
    
    # Standard fallback: Groq → Gemini Primary → Gemini Backup
    STANDARD = [
        ("groq", ModelConfig.DEFAULT_GROQ),
        ("gemini", ModelConfig.DEFAULT_GEMINI),
        ("gemini", ModelConfig.BACKUP_GEMINI),
    ]
    
    # Quality-focused: Groq Quality → Gemini Pro
    QUALITY_FIRST = [
        ("groq", ModelConfig.GROQ_MODELS["quality"]),
        ("gemini", ModelConfig.GEMINI_MODELS["primary"]),
    ]
    
    # Speed-focused: Fast models only
    SPEED_FIRST = [
        ("groq", ModelConfig.GROQ_MODELS["fast"]),
        ("gemini", ModelConfig.GEMINI_MODELS["lite"]),
    ]
    
    # Gemini-only: For when Groq is unavailable
    GEMINI_ONLY = [
        ("gemini", ModelConfig.DEFAULT_GEMINI),
        ("gemini", ModelConfig.BACKUP_GEMINI),
        ("gemini", ModelConfig.GEMINI_MODELS["experimental"]),
    ]


# ==========================================
# API SETTINGS
# ==========================================

class APISettings:
    """API call settings and limits"""
    
    # Timeout settings (seconds)
    GROQ_TIMEOUT = 30
    GEMINI_TIMEOUT = 45
    
    # Retry settings
    MAX_RETRIES = 1  # Optimized for speed
    RETRY_BACKOFF_BASE = 2  # Exponential backoff base
    MAX_BACKOFF = 3  # Cap backoff at 3 seconds
    
    # Rate limit settings
    RATE_LIMIT_WAIT = 2
    
    # Generation settings
    TEMPERATURE = 0.1  # Low for consistent compliance analysis
    MAX_TOKENS = 4000
    
    # Parallel processing
    DEFAULT_MAX_WORKERS = 3  # Balanced performance
    MAX_WORKERS_LIMIT = 10   # Hard limit


# ==========================================
# GEMINI SAFETY SETTINGS
# ==========================================

class SafetyConfig:
    """Gemini safety filter configurations"""
    
    # Permissive settings for compliance/legal content
    COMPLIANCE_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        },
    ]
    
    # Moderate settings (if permissive causes issues)
    MODERATE_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
    ]
    
    # Default for compliance analysis
    DEFAULT = COMPLIANCE_SETTINGS


# ==========================================
# PROMPT TEMPLATES
# ==========================================

class PromptTemplates:
    """Reusable prompt templates"""
    
    # Compliance context wrapper
    COMPLIANCE_CONTEXT = """You are a professional regulatory compliance assistant analyzing legal documents for a business compliance system. This is a legitimate legal analysis task for compliance purposes.

{prompt}"""
    
    # JSON response template
    JSON_RESPONSE = """Return your response in valid JSON format only, without markdown code blocks.
Follow this structure:
{structure}

{prompt}"""


# ==========================================
# BATCHING CONFIGURATION
# ==========================================

class BatchConfig:
    """Settings for batch processing"""
    
    MAX_BATCH_SIZE = 3000  # Characters
    BATCH_SEPARATOR = "\n\n---CLAUSE SEPARATOR---\n\n"
    MIN_CHUNK_SIZE_FOR_BATCHING = 500  # Only batch if chunks < 500 chars


# ==========================================
# LOGGING & MONITORING
# ==========================================

class LogConfig:
    """Logging configuration"""
    
    SHOW_PROGRESS = True
    VERBOSE_ERRORS = True
    LOG_API_CALLS = True
    LOG_RETRIES = True


# ==========================================
# ENVIRONMENT VALIDATION
# ==========================================

def validate_environment() -> Dict[str, bool]:
    """Check if API keys are configured"""
    return {
        "groq_configured": bool(GROQ_API_KEY),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


def get_available_providers() -> List[str]:
    """Get list of configured providers"""
    providers = []
    if GROQ_API_KEY:
        providers.append("groq")
    if GEMINI_API_KEY:
        providers.append("gemini")
    return providers


# ==========================================
# USAGE PRESETS
# ==========================================

class UsagePresets:
    """Common configuration presets for different use cases"""
    
    @staticmethod
    def compliance_analysis():
        """Standard compliance document analysis"""
        return {
            "groq_model": ModelConfig.DEFAULT_GROQ,
            "gemini_model": ModelConfig.DEFAULT_GEMINI,
            "safety_settings": SafetyConfig.COMPLIANCE_SETTINGS,
            "temperature": 0.1,
            "max_workers": 3,
        }
    
    @staticmethod
    def high_quality_legal():
        """High-stakes legal analysis"""
        return {
            "groq_model": ModelConfig.GROQ_MODELS["quality"],
            "gemini_model": ModelConfig.GEMINI_MODELS["primary"],
        }
    
    @staticmethod
    def fast_categorization():
        """Quick categorization/classification"""
        return {
            "groq_model": ModelConfig.GROQ_MODELS["fast"],
            "gemini_model": ModelConfig.GEMINI_MODELS["lite"],
            "safety_settings": SafetyConfig.MODERATE_SETTINGS,
            "temperature": 0.2,
            "max_workers": 5,  # High throughput
        }


# ==========================================
# EXPORT DEFAULTS
# ==========================================

# Quick access to defaults
DEFAULT_GROQ_MODEL = ModelConfig.DEFAULT_GROQ
DEFAULT_GEMINI_MODEL = ModelConfig.DEFAULT_GEMINI
DEFAULT_SAFETY_SETTINGS = SafetyConfig.DEFAULT
DEFAULT_TIMEOUT = APISettings.GROQ_TIMEOUT
DEFAULT_MAX_RETRIES = APISettings.MAX_RETRIES
DEFAULT_MAX_WORKERS = APISettings.DEFAULT_MAX_WORKERS

if __name__ == "__main__":
    # Print configuration summary
    print("🔧 LLM Configuration Summary")
    print("=" * 60)
    
    env = validate_environment()
    print(f"\n📡 API Keys Configured:")
    print(f"  • Groq: {'✅' if env['groq_configured'] else '❌'}")
    print(f"  • Gemini: {'✅' if env['gemini_configured'] else '❌'}")
    
    print(f"\n🤖 Default Models:")
    print(f"  • Groq: {ModelConfig.DEFAULT_GROQ}")
    print(f"  • Gemini: {ModelConfig.DEFAULT_GEMINI}")
    
    print(f"\n🔄 Fallback Chain:")
    for idx, (provider, model) in enumerate(FallbackChain.STANDARD, 1):
        print(f"  {idx}. {provider.upper()}: {model}")
    
    print(f"\n⚙ API Settings:")
    print(f"  • Max Retries: {APISettings.MAX_RETRIES}")
    print(f"  • Timeout: {APISettings.GROQ_TIMEOUT}s")
    print(f"  • Temperature: {APISettings.TEMPERATURE}")
    print(f"  • Parallel Workers: {APISettings.DEFAULT_MAX_WORKERS}")
    
    print("\n" + "=" * 60)