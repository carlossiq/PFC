"""
RAG (Retrieval-Augmented Generation) service using ChromaDB.

Manages indexing and retrieval of documents for context-aware generation.
"""

import hashlib
from pathlib import Path
from typing import Optional

import chromadb

from core.logging import get_logger
from services.ollama_service import OllamaService

logger = get_logger(__name__)

# ChromaDB configuration
CHROMA_DB_DIR = Path(".chroma_db")
CHUNK_SIZE = 1000  # Characters
CHUNK_OVERLAP = 200
MIN_CHUNK_LENGTH = 100


class RAGService:
    """Service for RAG using ChromaDB and Ollama embeddings."""

    def __init__(
        self,
        ollama_service: OllamaService,
        db_path: str = str(CHROMA_DB_DIR),
        collection_name: str = "research_documents",
    ):
        """
        Initialize RAG service.

        Args:
            ollama_service: OllamaService instance for embeddings
            db_path: Path to ChromaDB directory
            collection_name: Name of ChromaDB collection
        """
        self.ollama_service = ollama_service
        self.db_path = db_path
        self.collection_name = collection_name

        # Initialize ChromaDB using new API
        try:
            # Use persistent client with new ChromaDB API
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("rag_service_initialized", db_path=db_path)
        except Exception as exc:
            logger.error("rag_service_init_failed", error=str(exc))
            raise

    def chunk_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text
            chunk_size: Chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()

            if len(chunk) >= MIN_CHUNK_LENGTH:
                chunks.append(chunk)

            start = end - overlap

        logger.info("text_chunked", chunks_count=len(chunks), text_length=len(text))
        return chunks

    async def index_documents(
        self,
        documents: list[dict],
        metadata_key: str = "source",
    ) -> int:
        """
        Index documents in ChromaDB.

        Args:
            documents: List of dicts with 'text' and optional metadata keys
            metadata_key: Key for document source/identifier

        Returns:
            Number of chunks indexed
        """
        try:
            chunk_count = 0
            all_chunks = []
            all_metadatas = []
            all_ids = []

            for doc_idx, doc in enumerate(documents):
                text = doc.get("text", "")
                if not text:
                    logger.warning("document_missing_text", doc_index=doc_idx)
                    continue

                # Extract metadata
                metadata = {k: v for k, v in doc.items() if k != "text"}
                metadata["source_index"] = str(doc_idx)

                # Chunk text
                chunks = self.chunk_text(text)

                for chunk_idx, chunk in enumerate(chunks):
                    # Create unique ID
                    chunk_id = hashlib.md5(
                        f"{doc_idx}_{chunk_idx}_{chunk}".encode()
                    ).hexdigest()

                    all_chunks.append(chunk)
                    all_metadatas.append(metadata)
                    all_ids.append(chunk_id)
                    chunk_count += 1

            if not all_chunks:
                logger.warning("no_chunks_to_index")
                return 0

            # Add to ChromaDB with auto-generated embeddings
            # ChromaDB can use custom embedding function or generate using defaults
            self.collection.add(
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids,
            )

            logger.info("documents_indexed", chunks_count=chunk_count, docs_count=len(documents))
            return chunk_count

        except Exception as exc:
            logger.error("index_documents_failed", error=str(exc))
            raise

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Query ChromaDB for relevant documents.

        Args:
            query_text: Query text
            top_k: Number of top results
            filter_metadata: Optional metadata filter

        Returns:
            List of relevant chunks with metadata and distance
        """
        try:
            where = filter_metadata if filter_metadata else None

            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where,
            )

            if not results["documents"] or not results["documents"][0]:
                logger.warning("no_results_found", query_length=len(query_text))
                return []

            # Format results
            formatted_results = []
            for idx, (doc, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                formatted_results.append(
                    {
                        "rank": idx + 1,
                        "text": doc,
                        "metadata": metadata,
                        "relevance_score": 1 - distance,  # Convert distance to similarity
                    }
                )

            logger.info("query_executed", results_count=len(formatted_results))
            return formatted_results

        except Exception as exc:
            logger.error("query_failed", error=str(exc))
            raise

    async def get_context_for_section(
        self,
        section_name: str,
        section_description: str,
        top_k: int = 5,
    ) -> str:
        """
        Retrieve context for a specific report section.

        Args:
            section_name: Section name (e.g., "Introdução", "Metodologia")
            section_description: Description of what context is needed
            top_k: Number of relevant chunks to retrieve

        Returns:
            Formatted context string
        """
        query_text = f"{section_name}: {section_description}"

        try:
            results = await self.query(query_text, top_k=top_k)

            if not results:
                logger.warning("no_context_found", section=section_name)
                return ""

            # Format context
            context_parts = []
            context_parts.append(f"## Contexto para {section_name}\n")

            for result in results:
                context_parts.append(f"**Relevância: {result['relevance_score']:.1%}**")
                context_parts.append(f"Fonte: {result['metadata'].get('source', 'N/A')}")
                context_parts.append(result["text"])
                context_parts.append("")

            context = "\n".join(context_parts)

            logger.info(
                "section_context_retrieved",
                section=section_name,
                chunks=len(results),
            )

            return context

        except Exception as exc:
            logger.error(
                "get_context_failed",
                section=section_name,
                error=str(exc),
            )
            return ""

    async def clear_collection(self) -> bool:
        """
        Clear all documents from collection.

        Returns:
            True if successful
        """
        try:
            # Delete and recreate collection
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("collection_cleared", collection=self.collection_name)
            return True
        except Exception as exc:
            logger.error("clear_collection_failed", error=str(exc))
            return False

    def get_stats(self) -> dict:
        """
        Get collection statistics.

        Returns:
            Dict with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "db_path": self.db_path,
                "status": "healthy" if count >= 0 else "unknown",
            }
        except Exception as exc:
            logger.error("get_stats_failed", error=str(exc))
            return {"status": "error", "error": str(exc)}
