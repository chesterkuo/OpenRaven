from __future__ import annotations

from pathlib import Path
from typing import Literal

try:
    from lightrag import LightRAG, QueryParam
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

QueryMode = Literal["local", "global", "hybrid", "mix", "naive", "bypass"]


class RavenGraph:
    """Wrapper around LightRAG for knowledge graph operations."""

    def __init__(self, working_dir: Path, rag=None) -> None:
        self.working_dir = Path(working_dir)
        self._rag = rag
        self._initialized = False

    @classmethod
    async def create(
        cls,
        working_dir: Path,
        llm_model: str = "gemini-2.5-flash",
        llm_api_key: str | None = None,
        embedding_model: str = "text-embedding-004",
    ) -> RavenGraph:
        if not LIGHTRAG_AVAILABLE:
            raise ImportError("lightrag-hku is not installed")
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        llm_func = cls._make_llm_func(llm_model, llm_api_key)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key)
        rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=llm_func,
            llm_model_name=llm_model,
            embedding_func=embed_func,
        )
        await rag.initialize_storages()
        instance = cls(working_dir, rag)
        instance._initialized = True
        return instance

    @classmethod
    def create_lazy(
        cls,
        working_dir: Path,
        llm_model: str = "gemini-2.5-flash",
        llm_api_key: str | None = None,
        embedding_model: str = "text-embedding-004",
    ) -> RavenGraph:
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        if not LIGHTRAG_AVAILABLE:
            return cls(working_dir, rag=None)
        llm_func = cls._make_llm_func(llm_model, llm_api_key)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key)
        try:
            rag = LightRAG(
                working_dir=str(working_dir),
                llm_model_func=llm_func,
                llm_model_name=llm_model,
                embedding_func=embed_func,
            )
        except Exception:
            rag = None
        return cls(working_dir, rag)

    async def ensure_initialized(self) -> None:
        if not self._initialized and self._rag is not None:
            await self._rag.initialize_storages()
            self._initialized = True

    @staticmethod
    def _make_llm_func(model, api_key):
        """Create LLM function for LightRAG.

        LightRAG calls use_llm_func(prompt, system_prompt=...) — the model
        must be pre-bound as the first positional arg in the partial.
        """
        import os
        from functools import partial

        from lightrag.llm.openai import openai_complete_if_cache

        if "gemini" in model:
            key = api_key or os.environ.get("GEMINI_API_KEY", "")
            return partial(
                openai_complete_if_cache,
                model,  # first positional arg
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        return partial(openai_complete_if_cache, model, api_key=key)

    @staticmethod
    def _make_embedding_func(model, api_key):
        import os
        from functools import partial

        from lightrag.utils import EmbeddingFunc

        key = api_key or os.environ.get("GEMINI_API_KEY", "")

        if "gemini" in model or "text-embedding" in model:
            # Use LightRAG's native Gemini embedding (not OpenAI-compatible)
            from lightrag.llm.gemini import gemini_embed

            embed_model = "gemini-embedding-001"
            return EmbeddingFunc(
                embedding_dim=768,
                func=partial(gemini_embed, model=embed_model, api_key=key),
                model_name=embed_model,
            )

        from lightrag.llm.openai import openai_embed

        return EmbeddingFunc(
            embedding_dim=1536,
            func=partial(openai_embed, model=model),
            model_name=model,
        )

    async def insert(self, text: str, source: str = "") -> None:
        await self.ensure_initialized()
        if self._rag:
            await self._rag.ainsert(text)

    async def query(self, question: str, mode: QueryMode = "mix") -> str:
        await self.ensure_initialized()
        if self._rag:
            result = await self._rag.aquery(question, param=QueryParam(mode=mode))
            return result
        return ""

    def export_graphml(self, output_path: Path) -> None:
        import networkx as nx

        output_path = Path(output_path)
        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if graph_file.exists():
            graph = nx.read_graphml(str(graph_file))
            nx.write_graphml(graph, str(output_path))
        else:
            graph = nx.Graph()
            nx.write_graphml(graph, str(output_path))

    def get_stats(self) -> dict:
        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {"nodes": 0, "edges": 0, "topics": []}
        graph = nx.read_graphml(str(graph_file))
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "topics": list(graph.nodes())[:20],
        }
