from dataclasses import dataclass
from typing import Optional
import json
import asyncio

from engine.src.chunker import CodeChunk


def _get_litellm():
    """
    Lazy-import litellm and suppress debug output.

    Returns: module — The litellm module.
    Raises: ImportError — If litellm is not installed.
    """
    import os
    import litellm

    os.environ.setdefault("LITELLM_LOG", "ERROR")
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    return litellm


@dataclass(frozen=True, slots=True)
class ChunkDescription:
    """
    Generated description and keywords for a code chunk.

    Args:
        chunk_id: Chunk identifier
        description: Natural language description (1-3 sentences)
        keywords: Extracted keywords for ranking/relevancy
        token_count: Tokens used for generation (cost tracking)
        cost_usd: Cost in USD for this generation
    """
    chunk_id: str
    description: str
    keywords: list[str]
    token_count: int
    cost_usd: float = 0.0


class DescriptionGenerator:
    """
    Generates tiny NL descriptions and keywords for code chunks using LLM.

    Uses configured LLM (OpenRouter gpt-oss-20b) to generate:
    - 1-3 sentence description of what the code does
    - 3-7 keywords for semantic ranking
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        api_base: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.0,
        openrouter_provider: Optional[str] = None,
    ):
        """
        Args:
            model: LiteLLM model string (e.g., "openrouter/openai/gpt-oss-20b")
            api_key: API key for provider
            api_base: Optional API base URL
            max_tokens: Max tokens for description generation
            temperature: Sampling temperature (0.0 for deterministic)
            openrouter_provider: Force specific OpenRouter upstream (e.g., "Groq", "DeepInfra")
        """
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._openrouter_provider = openrouter_provider

    def generate(self, chunk: CodeChunk) -> ChunkDescription:
        """
        Generate description and keywords for a code chunk.

        Args:
            chunk: Code chunk to describe

        Returns:
            ChunkDescription with generated content
        """
        prompt = self._build_prompt(chunk)

        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "api_key": self._api_key,
        }

        if self._api_base:
            kwargs["api_base"] = self._api_base

        if self._openrouter_provider:
            kwargs["extra_body"] = {
                "provider": {
                    "order": [self._openrouter_provider]
                }
            }

        try:
            response = _get_litellm().completion(**kwargs)
            content = response.choices[0].message.content.strip()
            token_count = response.usage.total_tokens
            parsed = self._parse_response(content)

            return ChunkDescription(
                chunk_id=chunk.chunk_id,
                description=parsed["description"],
                keywords=parsed["keywords"],
                token_count=token_count,
            )
        except Exception as e:
            fallback_desc = f"{chunk.symbol_kind} {chunk.symbol_name}"
            if chunk.docstring:
                fallback_desc = chunk.docstring[:200]

            fallback_keywords = [chunk.language, chunk.symbol_kind]
            if chunk.parent:
                fallback_keywords.append(chunk.parent)

            return ChunkDescription(
                chunk_id=chunk.chunk_id,
                description=fallback_desc,
                keywords=fallback_keywords,
                token_count=0,
            )

    def generate_batch(self, chunks: list[CodeChunk], batch_size: int = 10) -> list[ChunkDescription]:
        """
        Generate descriptions for multiple chunks in batches using async concurrency.

        Args:
            chunks: List of code chunks
            batch_size: Number of concurrent requests (default: 10)

        Returns:
            List of chunk descriptions
        """
        return asyncio.run(self._generate_batch_async(chunks, batch_size))

    async def _generate_batch_async(self, chunks: list[CodeChunk], batch_size: int) -> list[ChunkDescription]:
        """
        Async implementation of batch generation with concurrency control.

        Args:
            chunks: List of code chunks
            batch_size: Number of concurrent requests

        Returns:
            List of chunk descriptions
        """
        semaphore = asyncio.Semaphore(batch_size)
        tasks = [self._generate_async(chunk, semaphore) for chunk in chunks]
        return await asyncio.gather(*tasks)

    async def _generate_async(self, chunk: CodeChunk, semaphore: asyncio.Semaphore) -> ChunkDescription:
        """
        Async description generation for a single chunk with semaphore control.

        Args:
            chunk: Code chunk to describe
            semaphore: Semaphore for concurrency control

        Returns:
            ChunkDescription with generated content
        """
        async with semaphore:
            prompt = self._build_prompt(chunk)

            kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "api_key": self._api_key,
            }

            if self._api_base:
                kwargs["api_base"] = self._api_base

            if self._openrouter_provider:
                kwargs["extra_body"] = {
                    "provider": {
                        "order": [self._openrouter_provider]
                    }
                }

            try:
                response = await _get_litellm().acompletion(**kwargs)
                content = response.choices[0].message.content.strip()
                token_count = response.usage.total_tokens
                cost = _get_litellm().completion_cost(completion_response=response)
                parsed = self._parse_response(content)

                return ChunkDescription(
                    chunk_id=chunk.chunk_id,
                    description=parsed["description"],
                    keywords=parsed["keywords"],
                    token_count=token_count,
                    cost_usd=cost,
                )
            except Exception as e:
                fallback_desc = f"{chunk.symbol_kind} {chunk.symbol_name}"
                if chunk.docstring:
                    fallback_desc = chunk.docstring[:200]

                fallback_keywords = [chunk.language, chunk.symbol_kind]
                if chunk.parent:
                    fallback_keywords.append(chunk.parent)

                return ChunkDescription(
                    chunk_id=chunk.chunk_id,
                    description=fallback_desc,
                    keywords=fallback_keywords,
                    token_count=0,
                    cost_usd=0.0,
                )

    def _system_prompt(self) -> str:
        """
        System prompt for description generation.

        Returns:
            System prompt text
        """
        return """You are a code documentation assistant. Generate concise descriptions and keywords for code snippets.

Output format (JSON):
{
  "description": "1-3 sentence description of what the code does",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}

Rules:
- Description: 1-3 sentences max, focus on WHAT and WHY, not HOW
- Keywords: 3-7 relevant terms for semantic search (language, domain, patterns, concepts)
- Keep it minimal to save tokens
- Output ONLY valid JSON, no markdown fences"""

    def _build_prompt(self, chunk: CodeChunk) -> str:
        """
        Build user prompt for a code chunk.

        Args:
            chunk: Code chunk to describe

        Returns:
            Formatted prompt
        """
        context_parts = []

        context_parts.append(f"Language: {chunk.language}")
        context_parts.append(f"File: {chunk.file_path}")
        context_parts.append(f"Symbol: {chunk.symbol_name} ({chunk.symbol_kind})")

        if chunk.parent:
            context_parts.append(f"Parent: {chunk.parent}")

        if chunk.signature:
            context_parts.append(f"Signature: {chunk.signature}")

        if chunk.docstring:
            context_parts.append(f"Docstring: {chunk.docstring}")

        context = "\n".join(context_parts)

        source_preview = chunk.source
        if len(source_preview) > 2000:
            source_preview = source_preview[:2000] + "\n... [truncated]"

        return f"""{context}

Code:
```{chunk.language}
{source_preview}
```

Generate description and keywords."""

    def _parse_response(self, content: str) -> dict[str, any]:
        """
        Parse LLM response into structured data.

        Args:
            content: Raw LLM response

        Returns:
            Dict with description and keywords
        """
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            parsed = json.loads(content)
            return {
                "description": parsed.get("description", ""),
                "keywords": parsed.get("keywords", []),
            }
        except json.JSONDecodeError:
            lines = content.split('\n')
            description = ""
            keywords = []

            for line in lines:
                line = line.strip()
                if line.startswith('"description"'):
                    description = line.split(':', 1)[1].strip(' ",')
                elif line.startswith('"keywords"'):
                    kw_part = line.split(':', 1)[1].strip(' []')
                    keywords = [k.strip(' "') for k in kw_part.split(',') if k.strip()]

            return {
                "description": description or "No description available",
                "keywords": keywords,
            }
