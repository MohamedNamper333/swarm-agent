"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - all confirmed working free models
COUNCIL_MODELS = [
    "openrouter/owl-alpha",                              # confirmed always works
    "openai/gpt-oss-120b:free",                          # confirmed works
    "nvidia/nemotron-3-ultra-550b-a55b:free",            # 550B reasoning (may rate-limit)
    "nvidia/nemotron-3-super-120b-a12b:free",            # 120B MoE (may rate-limit)
    "nvidia/nemotron-3-nano-30b-a3b:free",               # fast small model (may rate-limit)
    "qwen/qwen3-coder:free",                             # coding expert (may rate-limit)
    "meta-llama/llama-3.3-70b-instruct:free",            # 70B creative (may rate-limit)
    "nousresearch/hermes-3-llama-3.1-405b:free",         # 405B general (may rate-limit)
]

# Chairman model
CHAIRMAN_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Timeout per model in seconds
MODEL_TIMEOUT = 60.0

# Data directory
DATA_DIR = "data/conversations"
