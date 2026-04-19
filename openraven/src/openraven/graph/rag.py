from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from lightrag import LightRAG, QueryParam
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

QueryMode = Literal["local", "global", "hybrid", "mix", "naive", "bypass"]

LOCALE_NAMES = {
    "en": "English",
    "zh-TW": "Traditional Chinese (繁體中文)",
    "zh-CN": "Simplified Chinese (简体中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "nl": "Dutch (Nederlands)",
    "it": "Italian (Italiano)",
    "vi": "Vietnamese (Tiếng Việt)",
    "th": "Thai (ภาษาไทย)",
    "ru": "Russian (Русский)",
}


@dataclass
class QueryResult:
    answer: str
    sources: list[dict]


class RavenGraph:
    """Wrapper around LightRAG for knowledge graph operations."""

    def __init__(
        self,
        working_dir: Path,
        rag=None,
        graph_backend: str = "networkx",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
    ) -> None:
        self.working_dir = Path(working_dir)
        self._rag = rag
        self._initialized = False
        self._graph_backend = graph_backend
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password

    @classmethod
    async def create(
        cls,
        working_dir: Path,
        llm_model: str = "gemini-2.5-flash",
        llm_api_key: str | None = None,
        embedding_model: str = "text-embedding-004",
        provider: str = "gemini",
        ollama_base_url: str = "http://localhost:11434",
        graph_backend: str = "networkx",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
    ) -> RavenGraph:
        if not LIGHTRAG_AVAILABLE:
            raise ImportError("lightrag-hku is not installed")
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        llm_func = cls._make_llm_func(llm_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        if graph_backend == "neo4j":
            import os
            from lightrag.kg.neo4j_impl import Neo4JStorage  # noqa: F401 — ensure registered
            os.environ.setdefault("NEO4J_URI", neo4j_uri)
            os.environ.setdefault("NEO4J_USERNAME", neo4j_user)
            os.environ.setdefault("NEO4J_PASSWORD", neo4j_password)
            rag = LightRAG(
                working_dir=str(working_dir),
                llm_model_func=llm_func,
                llm_model_name=llm_model,
                embedding_func=embed_func,
                graph_storage="Neo4JStorage",
            )
        else:
            rag = LightRAG(
                working_dir=str(working_dir),
                llm_model_func=llm_func,
                llm_model_name=llm_model,
                embedding_func=embed_func,
            )
        await rag.initialize_storages()
        instance = cls(working_dir, rag, graph_backend=graph_backend,
                       neo4j_uri=neo4j_uri, neo4j_user=neo4j_user, neo4j_password=neo4j_password)
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
        graph_backend: str = "networkx",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
    ) -> RavenGraph:
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        if not LIGHTRAG_AVAILABLE:
            return cls(working_dir, rag=None, graph_backend=graph_backend,
                       neo4j_uri=neo4j_uri, neo4j_user=neo4j_user, neo4j_password=neo4j_password)
        llm_func = cls._make_llm_func(llm_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
        try:
            if graph_backend == "neo4j":
                import os
                from lightrag.kg.neo4j_impl import Neo4JStorage  # noqa: F401 — ensure registered
                os.environ.setdefault("NEO4J_URI", neo4j_uri)
                os.environ.setdefault("NEO4J_USERNAME", neo4j_user)
                os.environ.setdefault("NEO4J_PASSWORD", neo4j_password)
                rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=llm_func,
                    llm_model_name=llm_model,
                    embedding_func=embed_func,
                    graph_storage="Neo4JStorage",
                )
            else:
                rag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=llm_func,
                    llm_model_name=llm_model,
                    embedding_func=embed_func,
                )
        except Exception:
            rag = None
        return cls(working_dir, rag, graph_backend=graph_backend,
                   neo4j_uri=neo4j_uri, neo4j_user=neo4j_user, neo4j_password=neo4j_password)

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
            await self._rag.ainsert(text, file_paths=source or None)

    async def query(self, question: str, mode: QueryMode = "mix") -> str:
        await self.ensure_initialized()
        if self._rag:
            result = await self._rag.aquery(question, param=QueryParam(mode=mode))
            return result
        return ""

    async def query_with_sources(self, question: str, mode: QueryMode = "mix", locale: str = "en") -> QueryResult:
        await self.ensure_initialized()
        if not self._rag:
            return QueryResult(answer="", sources=[])
        localized_question = question
        if locale != "en":
            locale_name = LOCALE_NAMES.get(locale, "English")
            localized_question = f"{question}\n\n[IMPORTANT: Respond in {locale_name}. The user's interface language is {locale}.]"
        answer = await self._rag.aquery(localized_question, param=QueryParam(mode=mode))
        if not answer:
            return QueryResult(answer="", sources=[])
        sources = self._extract_sources_from_answer(answer)
        return QueryResult(answer=answer, sources=sources)

    def _extract_sources_from_answer(self, answer: str) -> list[dict]:
        if self._graph_backend == "neo4j":
            return self._extract_sources_neo4j(answer)

        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return []
        try:
            graph = nx.read_graphml(str(graph_file))
        except Exception:
            return []
        answer_lower = answer.lower()
        sources: list[dict] = []
        seen_docs: set[str] = set()
        for node_id, attrs in graph.nodes(data=True):
            if node_id.lower() in answer_lower:
                file_path = attrs.get("file_path", "")
                if not file_path or file_path in seen_docs:
                    continue
                seen_docs.add(file_path)
                sources.append({
                    "document": file_path,
                    "excerpt": attrs.get("description", "")[:100],
                    "char_start": 0,
                    "char_end": 0,
                })
        return sources

    def _extract_sources_neo4j(self, answer: str) -> list[dict]:
        from neo4j import GraphDatabase

        answer_lower = answer.lower()
        sources: list[dict] = []
        seen_docs: set[str] = set()
        try:
            driver = GraphDatabase.driver(self._neo4j_uri, auth=(self._neo4j_user, self._neo4j_password))
            with driver.session() as session:
                result = session.run(
                    "MATCH (n) WHERE toLower(n.id) IN $ids OR toLower(n.id) CONTAINS $answer "
                    "RETURN n.id AS id, n.file_path AS file_path, n.description AS description",
                    ids=[],
                    answer=answer_lower[:200],
                )
                for record in result:
                    file_path = record.get("file_path") or ""
                    node_id = record.get("id") or ""
                    if not file_path or file_path in seen_docs:
                        continue
                    if node_id.lower() not in answer_lower:
                        continue
                    seen_docs.add(file_path)
                    sources.append({
                        "document": file_path,
                        "excerpt": (record.get("description") or "")[:100],
                        "char_start": 0,
                        "char_end": 0,
                    })
            driver.close()
        except Exception:
            pass
        return sources

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

        Note: for networkx backend, reads graph_chunk_entity_relation.graphml
        directly from working_dir. For neo4j backend, queries Neo4j directly.
        """
        if self._graph_backend == "neo4j":
            return self._get_graph_data_neo4j(max_nodes)

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

    def get_subgraph(
        self,
        entities: list[str] | None = None,
        files: list[str] | None = None,
        max_nodes: int = 30,
    ) -> dict:
        """Return a subgraph centered on the given entities or files, with 1-hop neighbors."""
        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {"nodes": [], "edges": []}

        try:
            graph = nx.read_graphml(str(graph_file))
        except Exception:
            return {"nodes": [], "edges": []}

        seed_ids: set[str] = set()

        if entities:
            for eid in entities:
                if eid in graph:
                    seed_ids.add(eid)

        if files:
            file_suffixes = {f.split("/")[-1] for f in files}
            for node_id, attrs in graph.nodes(data=True):
                file_path = attrs.get("file_path", "")
                for part in file_path.split("<SEP>"):
                    fname = part.strip().split("/")[-1]
                    if fname in file_suffixes:
                        seed_ids.add(node_id)
                        break

        if not seed_ids:
            return {"nodes": [], "edges": []}

        # BFS 1-hop neighbors
        neighbor_ids: set[str] = set()
        for sid in seed_ids:
            if graph.has_node(sid):
                neighbor_ids.update(graph.predecessors(sid))
                neighbor_ids.update(graph.successors(sid))
        all_ids = seed_ids | neighbor_ids

        # Trim if exceeding max_nodes — keep seeds, sort neighbors by degree
        if len(all_ids) > max_nodes:
            extras = all_ids - seed_ids
            ranked = sorted(extras, key=lambda n: graph.degree(n), reverse=True)
            all_ids = seed_ids | set(ranked[: max_nodes - len(seed_ids)])

        nodes = []
        for node_id in all_ids:
            attrs = dict(graph.nodes[node_id])
            nodes.append({
                "id": node_id,
                "labels": [attrs.get("entity_type", "unknown")],
                "properties": attrs,
                "is_seed": node_id in seed_ids,
            })

        edges = []
        for source, target, attrs in graph.edges(data=True):
            if source in all_ids and target in all_ids:
                edges.append({
                    "id": f"{source}-{target}",
                    "type": "DIRECTED",
                    "source": source,
                    "target": target,
                    "properties": dict(attrs),
                })

        return {"nodes": nodes, "edges": edges}

    def _get_graph_data_neo4j(self, max_nodes: int = 500) -> dict:
        """Query Neo4j directly for graph data."""
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(self._neo4j_uri, auth=(self._neo4j_user, self._neo4j_password))
            with driver.session() as session:
                nodes_result = session.run(
                    "MATCH (n) RETURN n.id AS id, labels(n) AS labels, properties(n) AS props LIMIT $max",
                    max=max_nodes,
                )
                nodes = [
                    {"id": r["id"], "labels": r["labels"], "properties": r["props"]}
                    for r in nodes_result
                ]

                edges_result = session.run(
                    "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids "
                    "RETURN id(r) AS id, type(r) AS type, a.id AS source, b.id AS target, properties(r) AS props",
                    ids=[n["id"] for n in nodes],
                )
                edges = [
                    {
                        "id": str(r["id"]),
                        "type": r["type"],
                        "source": r["source"],
                        "target": r["target"],
                        "properties": r["props"],
                    }
                    for r in edges_result
                ]
            driver.close()
            return {"nodes": nodes, "edges": edges, "is_truncated": len(nodes) >= max_nodes}
        except Exception:
            return {"nodes": [], "edges": [], "is_truncated": False}

    def get_stats(self) -> dict:
        if self._graph_backend == "neo4j":
            return self._get_stats_neo4j()

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

    def _get_stats_neo4j(self) -> dict:
        """Query Neo4j for graph statistics."""
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(self._neo4j_uri, auth=(self._neo4j_user, self._neo4j_password))
            with driver.session() as session:
                node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
                edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
                topics_result = session.run("MATCH (n) RETURN n.id AS id LIMIT 20")
                topics = [r["id"] for r in topics_result if r["id"]]
            driver.close()
            return {"nodes": node_count, "edges": edge_count, "topics": topics}
        except Exception:
            return {"nodes": 0, "edges": 0, "topics": []}

    def get_detailed_stats(self) -> dict:
        """Return detailed graph statistics including entity types and clusters."""
        base = self.get_stats()

        if self._graph_backend == "neo4j":
            return self._get_detailed_stats_neo4j(base)

        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}

        try:
            graph = nx.read_graphml(str(graph_file))
        except Exception:
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}

        entity_types: dict[str, int] = {}
        for _, attrs in graph.nodes(data=True):
            etype = attrs.get("entity_type", "unknown")
            entity_types[etype] = entity_types.get(etype, 0) + 1

        degrees = dict(graph.degree())
        top_connected = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]

        if graph.is_directed():
            components = nx.number_weakly_connected_components(graph)
        else:
            components = nx.number_connected_components(graph)

        return {
            **base,
            "entity_types": entity_types,
            "top_connected": top_connected,
            "components": components,
        }

    def _get_detailed_stats_neo4j(self, base: dict) -> dict:
        """Detailed stats from Neo4j."""
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(self._neo4j_uri, auth=(self._neo4j_user, self._neo4j_password))
            with driver.session() as session:
                type_result = session.run(
                    "MATCH (n) RETURN n.entity_type AS etype, count(*) AS cnt"
                )
                entity_types = {r["etype"] or "unknown": r["cnt"] for r in type_result}

                degree_result = session.run(
                    "MATCH (n)-[r]-() RETURN n.id AS id, count(r) AS deg ORDER BY deg DESC LIMIT 10"
                )
                top_connected = [(r["id"], r["deg"]) for r in degree_result]

            driver.close()
            return {**base, "entity_types": entity_types, "top_connected": top_connected, "components": 0}
        except Exception:
            return {**base, "entity_types": {}, "top_connected": [], "components": 0}
