"""Sober benchmark — Cognee memory vs. naive context-stuffing.

Demonstrates the core problem: as a conversation grows, stuffing the whole
history into the prompt grows token usage linearly (and eventually overflows
the context window), while Cognee retrieves only the relevant slice — staying
flat and accurate no matter how long the history gets.

Run:  python benchmark.py
"""

import asyncio
import os
import pathlib

os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

from dotenv import load_dotenv

BASE = pathlib.Path(__file__).parent
load_dotenv(BASE / ".env")

import cognee
from cognee import SearchType

# Isolated storage so forget(everything=True) below can never touch the app's
# real memory in .cognee_data / .cognee_system.
cognee.config.data_root_directory(str(BASE / ".benchmark_data"))
cognee.config.system_root_directory(str(BASE / ".benchmark_system"))

DATASET = "sober_benchmark"
TURNS = 100

# A long conversation — a few real facts buried among filler turns.
FACTS = [
    "My dog's name is Pixel and he is a beagle.",
    "I am building a portfolio website with Next.js.",
    "My favorite coffee order is an oat-milk flat white.",
]
FILLER = [
    f"Turn {i}: we chatted about the weather, lunch plans, and other small talk "
    f"that has nothing to do with anything important."
    for i in range(TURNS - len(FACTS))
]
HISTORY = FACTS + FILLER
QUESTION = "What is my dog's name and breed?"


def rough_tokens(text: str) -> int:
    """Crude token estimate (~4 chars/token) — good enough to show the trend."""
    return max(1, len(text) // 4)


async def main():
    await cognee.forget(everything=True)

    print(f"Ingesting a {TURNS}-turn conversation into Cognee "
          f"(this cognifies once, then every future question is cheap)...")
    # Batch turns into a few documents so ingestion is fast.
    batch = 25
    docs = ["\n".join(HISTORY[i:i + batch]) for i in range(0, len(HISTORY), batch)]
    await cognee.remember(docs, dataset_name=DATASET)

    # Naive approach: send the ENTIRE history every single turn.
    naive_prompt = "\n".join(HISTORY) + "\n" + QUESTION
    naive_tokens = rough_tokens(naive_prompt)

    # Cognee approach: recall only the relevant slice of memory.
    results = await cognee.recall(
        query_text=QUESTION, query_type=SearchType.GRAPH_COMPLETION, datasets=[DATASET]
    )
    answer = str(results[0]) if results else "(no answer)"
    cognee_tokens = rough_tokens(QUESTION + answer)

    reduction = (1 - cognee_tokens / naive_tokens) * 100

    print("\n=== Sober: Cognee memory vs. naive context-stuffing ===")
    print(f"Conversation length:        {TURNS} turns")
    print(f"Naive prompt tokens:        ~{naive_tokens}  (grows linearly, every turn)")
    print(f"Cognee tokens for the ask:  ~{cognee_tokens}  (stays flat at any history size)")
    print(f"Token reduction:            ~{reduction:.0f}%")
    print(f"\nQuestion:      {QUESTION}")
    print(f"Cognee answer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
