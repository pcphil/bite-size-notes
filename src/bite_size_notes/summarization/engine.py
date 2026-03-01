"""Qwen2.5 3B Instruct GGUF summarization engine."""

import logging

from huggingface_hub import hf_hub_download, try_to_load_from_cache
from llama_cpp import Llama

logger = logging.getLogger(__name__)

REPO_ID = "Qwen/Qwen2.5-3B-Instruct-GGUF"
FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"

SYSTEM_PROMPT = (
    "You are a professional meeting-minutes writer. "
    "Given a raw meeting transcript, produce structured meeting notes in this format:\n"
    "\n"
    "## Meeting Summary\n"
    "A concise 2-3 sentence overview of the meeting's purpose and outcome.\n"
    "\n"
    "## Key Discussion Points\n"
    "- Bullet each major topic discussed, with the speaker(s) noted where relevant.\n"
    "\n"
    "## Decisions Made\n"
    "- Bullet each decision reached during the meeting.\n"
    "\n"
    "## Action Items\n"
    "- [ ] Task description — Owner (if identifiable), deadline (if mentioned)\n"
    "\n"
    "Rules:\n"
    "- Use the speakers' names as they appear in the transcript.\n"
    "- Omit filler, off-topic chatter, and redundant back-and-forth.\n"
    "- Keep the entire output under 300 words.\n"
    "- If a section has no content, omit that section entirely."
)


def is_summarizer_cached() -> bool:
    """Check whether the GGUF model file is already in the HF cache."""
    result = try_to_load_from_cache(REPO_ID, FILENAME)
    cached = isinstance(result, str)
    logger.info("Summarizer model cached: %s", cached)
    return cached


def download_summarizer_sync() -> str:
    """Download the GGUF model file and return the cached path."""
    logger.info("Downloading summarizer model %s/%s", REPO_ID, FILENAME)
    path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
    logger.info("Summarizer model path: %s", path)
    return path


N_CTX = 4096
MAX_TOKENS = 512
TOKEN_MARGIN = 64

REDUCE_SYSTEM_PROMPT = (
    "You are a professional meeting-minutes writer. "
    "Given these partial meeting summaries, merge them into one cohesive set "
    "of meeting notes in this format:\n"
    "\n"
    "## Meeting Summary\n"
    "A concise 2-3 sentence overview of the meeting's purpose and outcome.\n"
    "\n"
    "## Key Discussion Points\n"
    "- Bullet each major topic discussed, with the speaker(s) noted where relevant.\n"
    "\n"
    "## Decisions Made\n"
    "- Bullet each decision reached during the meeting.\n"
    "\n"
    "## Action Items\n"
    "- [ ] Task description — Owner (if identifiable), deadline (if mentioned)\n"
    "\n"
    "Rules:\n"
    "- Deduplicate and merge overlapping points.\n"
    "- If a section has no content, omit that section entirely."
)


def load_summarizer() -> Llama:
    """Load the Qwen2.5 3B Instruct GGUF model, downloading if necessary."""
    path = download_summarizer_sync()
    logger.info("Loading Llama model from %s", path)
    llm = Llama(
        model_path=path,
        n_ctx=N_CTX,
        n_threads=4,
        use_mlock=False,
        verbose=False,
        chat_format="chatml",
    )
    logger.info("Llama model loaded")
    return llm


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters."""
    return len(text) // 4


def _chunk_transcript(text: str, token_budget: int) -> list[str]:
    """Split transcript into line-aligned chunks within token_budget."""
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = _estimate_tokens(line)
        if current and current_tokens + line_tokens > token_budget:
            chunks.append("".join(current))
            current = [line]
            current_tokens = line_tokens
        else:
            current.append(line)
            current_tokens += line_tokens

    if current:
        chunks.append("".join(current))

    return chunks


def _summarize_single(
    llm: Llama, system_prompt: str, user_content: str
) -> str:
    """Run a single summarization call."""
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"].strip()


def summarize(llm: Llama, transcript_text: str) -> str:
    """Run summarization on the given transcript text.

    Uses map-reduce chunking when the transcript exceeds the token budget.
    """
    token_budget = N_CTX - _estimate_tokens(SYSTEM_PROMPT) - MAX_TOKENS - TOKEN_MARGIN
    transcript_tokens = _estimate_tokens(transcript_text)

    if transcript_tokens <= token_budget:
        logger.info("Single-pass summarization (%d est. tokens)", transcript_tokens)
        return _summarize_single(llm, SYSTEM_PROMPT, transcript_text)

    # Map phase: summarize each chunk independently
    chunks = _chunk_transcript(transcript_text, token_budget)
    logger.info(
        "Chunking transcript into %d parts (%d est. tokens, budget %d)",
        len(chunks),
        transcript_tokens,
        token_budget,
    )
    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        logger.info("Summarizing chunk %d/%d", i + 1, len(chunks))
        summary = _summarize_single(llm, SYSTEM_PROMPT, chunk)
        chunk_summaries.append(summary)

    # Reduce phase: merge chunk summaries
    combined = "\n\n---\n\n".join(chunk_summaries)
    combined_tokens = _estimate_tokens(combined)

    if combined_tokens > token_budget:
        # If combined summaries still exceed budget, recurse
        logger.info("Combined summaries exceed budget, recursing reduce phase")
        return summarize(llm, combined)

    logger.info("Reduce pass: merging %d chunk summaries", len(chunk_summaries))
    return _summarize_single(llm, REDUCE_SYSTEM_PROMPT, combined)
