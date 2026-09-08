"""Probe Groq rate-limit headers."""

import json
import traceback

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)
out = []

for i in range(20):
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=10,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a structured data extractor. Return ONLY a valid JSON object matching the schema provided."},
                {"role": "user", "content": "Extract structured json from: hello world. Return json only."},
            ],
        )
        out.append(f"[{i}] OK")
    except Exception as e:
        out.append(f"\n=== HIT on attempt {i} ===")
        out.append(f"Type: {type(e).__name__}")
        out.append(f"Str: {str(e)[:800]}")

        # Dump ALL attributes
        out.append("\n--- Attributes ---")
        for attr in sorted(dir(e)):
            if not attr.startswith("_"):
                try:
                    val = getattr(e, attr)
                    if not callable(val):
                        out.append(f"  {attr}: {repr(val)[:300]}")
                except Exception:
                    pass
        break

with open("rate_limit_probe.txt", "w") as f:
    f.write("\n".join(out))
print("Wrote rate_limit_probe.txt")
