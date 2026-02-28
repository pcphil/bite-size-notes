"""Qwen3 4B GGUF summarization engine."""

from huggingface_hub import hf_hub_download, try_to_load_from_cache
from llama_cpp import Llama

REPO_ID = "unsloth/Qwen3-4B-GGUF"
FILENAME = "Qwen3-4B-Q4_K_M.gguf"

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
    return isinstance(result, str)


def download_summarizer_sync() -> str:
    """Download the GGUF model file and return the cached path."""
    return hf_hub_download(repo_id=REPO_ID, filename=FILENAME)


def load_summarizer() -> Llama:
    """Load the Qwen3 4B GGUF model, downloading if necessary."""
    path = download_summarizer_sync()
    return Llama(model_path=path, n_ctx=2048, verbose=False)


def summarize(llm: Llama, transcript_text: str) -> str:
    """Run summarization on the given transcript text."""
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
        max_tokens=512,
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"]
