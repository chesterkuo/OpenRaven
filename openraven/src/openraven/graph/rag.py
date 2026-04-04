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
        provider: str = "gemini",
        ollama_base_url: str = "http://localhost:11434",
    ) -> RavenGraph:
        if not LIGHTRAG_AVAILABLE:
            raise ImportError("lightrag-hku is not installed")
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        llm_func = cls._make_llm_func(llm_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
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
        provider: str = "gemini",
        ollama_base_url: str = "http://localhost:11434",
    ) -> RavenGraph:
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        if not LIGHTRAG_AVAILABLE:
            return cls(working_dir, rag=None)
        llm_func = cls._make_llm_func(llm_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
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
    def _make_llm_func(model, api_key, provider="gemini", ollama_base_url="http://localhost:11434"):
        """Create LLM function for LightRAG.

        LightRAG calls use_llm_func(prompt, system_prompt=...) — the model
        must be pre-bound as the first positional arg in the partial.
        """
        import os
        from functools import partial

        if provider == "ollama":
            from lightrag.llm.ollama import ollama_model_complete
            return ollama_model_complete

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
    def _make_embedding_func(model, api_key, provider="gemini", ollama_base_url="http://localhost:11434"):
        import os
        from functools import partial

        from lightrag.utils import EmbeddingFunc

        if provider == "ollama":
            from lightrag.llm.ollama import ollama_embed

            # nomic-embed-text: 768 dims, bge-m3/mxbai-embed-large: 1024 dims
            dim = 768 if "nomic" in model else 1024
            raw_ollama_embed = ollama_embed.func  # bypass decorator's validator

            async def _ollama_embed(texts, **kwargs):
                return await raw_ollama_embed(texts, embed_model=model, host=ollama_base_url, **kwargs)

            return EmbeddingFunc(
                embedding_dim=dim,
                func=_ollama_embed,
                model_name=model,
            )

        key = api_key or os.environ.get("GEMINI_API_KEY", "")

        if "gemini" in model or "text-embedding" in model:
            from lightrag.llm.gemini import gemini_embed

            embed_model = "gemini-embedding-001"
            # Access the raw function underneath gemini_embed's
            # @wrap_embedding_func_with_attrs decorator. The decorator wraps
            # it in an EmbeddingFunc(dim=1536) with a count validator that
            # rejects Gemini's extra-vector responses. By using .func we
            # bypass that inner validator — our outer EmbeddingFunc(dim=768)
            # will handle validation after we truncate.
            raw_gemini_embed = gemini_embed.func
            base_func = partial(raw_gemini_embed, model=embed_model, api_key=key)

            async def _safe_gemini_embed(texts, **kwargs):
                """Call Gemini embed with correct dimension and truncate extra vectors.

                Two issues with raw gemini_embed:
                1. Without embedding_dim, Gemini returns 3072-dim vectors instead of 768,
                   causing LightRAG's validator to miscount vectors (3072/768 = 4x).
                2. Gemini sometimes returns more embeddings than input texts.
                We fix both by injecting embedding_dim and truncating excess vectors.
                """
                import numpy as np

                # Ensure embedding_dim is passed so Gemini returns 768-dim vectors
                kwargs.setdefault("embedding_dim", 768)
                result = await base_func(texts, **kwargs)
                expected = len(texts)
                if result.shape[0] > expected:
                    result = result[:expected]
                return result

            return EmbeddingFunc(
                embedding_dim=768,
                func=_safe_gemini_embed,
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

    def get_graph_data(self, max_nodes: int = 500) -> dict:
        """Return graph nodes and edges as a JSON-serializable dict.

        Returns the top nodes by degree, with all edges between them.
        Format matches LightRAG's KnowledgeGraph schema.

        Note: reads graph_chunk_entity_relation.graphml directly from working_dir.
        This assumes LightRAG was initialized without a custom workspace prefix
        (same assumption as get_stats() and export_graphml()).
        """
        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {"nodes": [], "edges": [], "is_truncated": False}

        try:
            graph = nx.read_graphml(str(graph_file))
        except Exception:
            # File may be partially written during concurrent ingestion
            return {"nodes": [], "edges": [], "is_truncated": False}

        total_nodes = graph.number_of_nodes()
        is_truncated = total_nodes > max_nodes

        # Take top nodes by degree
        if is_truncated:
            degrees = dict(graph.degree())
            sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
            limited = [n for n, _ in sorted_nodes[:max_nodes]]
            graph = graph.subgraph(limited)

        nodes = []
        for node_id, attrs in graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "labels": [attrs.get("entity_type", "unknown")],
                "properties": dict(attrs),
            })

        edges = []
        for source, target, attrs in graph.edges(data=True):
            edges.append({
                "id": f"{source}-{target}",
                "type": "DIRECTED",
                "source": source,
                "target": target,
                "properties": dict(attrs),
            })

        return {"nodes": nodes, "edges": edges, "is_truncated": is_truncated}

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
