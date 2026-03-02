from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

import networkx as nx
import requests
import streamlit as st
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi

# Import centralized logging configuration
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from logger_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ

QDRANT_URL = env.get("QDRANT_URL")
DEFAULT_COLLECTION = env.get("DEFAULT_COLLECTION")
OPENAI_API_URL = env.get("OPENAI_API_URL")
OPENAI_EMBED_MODEL = env.get("OPENAI_EMBED_MODEL")
ROOT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
APP_DIR = Path(__file__).resolve().parent


def load_root_env_file():
    """Load simple KEY=VALUE pairs from repo-root .env into os.environ."""
    if not ROOT_ENV_PATH.exists():
        return

    for line in ROOT_ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_pdf_path(pdf_path: str) -> Path:
    """Resolve PDF path across common launch directories."""
    candidate = Path(pdf_path)
    if candidate.exists():
        return candidate

    candidates = [
        APP_DIR / candidate,  # launched from repo root, given relative module path
        APP_DIR / "sample_expense_policy.pdf",  # launched from module dir with default sample
        ROOT_ENV_PATH.parent / candidate,  # normalize against repo root
    ]
    for path in candidates:
        if path.exists():
            return path

    return candidate


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    section_number: str
    section_title: str
    parent_section: Optional[str]
    page_number: int
    hierarchy_path: List[str]
    chunk_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "parent_section": self.parent_section,
            "page_number": self.page_number,
            "hierarchy_path": self.hierarchy_path,
            "chunk_type": self.chunk_type,
        }


class DocumentIngestionPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.chunks: List[DocumentChunk] = []
        logger.info(f"Initializing DocumentIngestionPipeline for PDF: {pdf_path}")

    def load_pdf(self) -> List[Tuple[int, str]]:
        logger.info(f"Loading PDF: {self.pdf_path}")
        try:
            reader = PdfReader(self.pdf_path)
            pages = []
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                pages.append((page_num, text))
            logger.info(f"Successfully loaded {len(pages)} pages from PDF")
            return pages
        except Exception as e:
            logger.error(f"Failed to load PDF {self.pdf_path}: {e}")
            raise

    def _create_section_chunk(self, section_num: str, section_title: str, page_num: int, chunk_counter: int) -> DocumentChunk:
        """Create a section-level chunk."""
        return DocumentChunk(
            chunk_id=f"chunk_{chunk_counter}",
            text=f"Section {section_num}: {section_title}",
            section_number=section_num,
            section_title=section_title,
            parent_section=None,
            page_number=page_num,
            hierarchy_path=[f"Section {section_num}"],
            chunk_type="section"
        )

    def _create_subsection_chunk(self, subsection_num: str, subsection_title: str, current_section: str, page_num: int, chunk_counter: int) -> DocumentChunk:
        """Create a subsection-level chunk."""
        return DocumentChunk(
            chunk_id=f"chunk_{chunk_counter}",
            text=f"{subsection_num} {subsection_title}",
            section_number=subsection_num,
            section_title=subsection_title,
            parent_section=current_section,
            page_number=page_num,
            hierarchy_path=[f"Section {current_section}", subsection_num],
            chunk_type="subsection"
        )

    def _create_subsubsection_chunk(self, subsubsection_num: str, subsubsection_title: str, current_subsection: str, page_num: int, chunk_counter: int) -> DocumentChunk:
        """Create a sub-subsection-level chunk."""
        return DocumentChunk(
            chunk_id=f"chunk_{chunk_counter}",
            text=f"{subsubsection_num} {subsubsection_title}",
            section_number=subsubsection_num,
            section_title=subsubsection_title,
            parent_section=current_subsection,
            page_number=page_num,
            hierarchy_path=[f"Section {current_subsection.split('.')[0]}", current_subsection, subsubsection_num],
            chunk_type="subsubsection"
        )

    def _create_paragraph_chunk(self, para: str, current_section: str, current_subsection: str, page_num: int, chunk_counter: int) -> DocumentChunk:
        """Create a paragraph-level chunk."""
        parent = current_subsection or current_section
        hierarchy = []
        if current_section:
            hierarchy.append(f"Section {current_section}")
        if current_subsection:
            hierarchy.append(current_subsection)

        return DocumentChunk(
            chunk_id=f"chunk_{chunk_counter}",
            text=para,
            section_number=parent or "0",
            section_title="",
            parent_section=parent,
            page_number=page_num,
            hierarchy_path=hierarchy,
            chunk_type="paragraph"
        )

    def _process_paragraph(self, para: str, current_section: str, current_subsection: str, page_num: int, chunk_counter: int, chunks: List[DocumentChunk]) -> Tuple[str, str, int]:
        """Process a single paragraph and update tracking variables."""
        import re

        # Patterns for section detection
        section_pattern = re.compile(r'^Section (\d+):\s*(.+)$', re.MULTILINE)
        subsection_pattern = re.compile(r'^(\d+\.\d+)\s+(.+)$', re.MULTILINE)
        subsubsection_pattern = re.compile(r'^(\d+\.\d+\.\d+)\s+(.+)$', re.MULTILINE)

        # Check for main section
        section_match = section_pattern.search(para)
        if section_match:
            section_num = section_match.group(1)
            section_title = section_match.group(2).strip()
            chunks.append(self._create_section_chunk(section_num, section_title, page_num, chunk_counter))
            return section_num, None, chunk_counter + 1

        # Check for subsection (e.g., 4.1)
        subsection_match = subsection_pattern.search(para)
        if subsection_match and current_section:
            subsection_num = subsection_match.group(1)
            subsection_title = subsection_match.group(2).strip()
            chunks.append(self._create_subsection_chunk(subsection_num, subsection_title, current_section, page_num, chunk_counter))
            return current_section, subsection_num, chunk_counter + 1

        # Check for sub-subsection (e.g., 4.1.1)
        subsubsection_match = subsubsection_pattern.search(para)
        if subsubsection_match and current_subsection:
            subsubsection_num = subsubsection_match.group(1)
            subsubsection_title = subsubsection_match.group(2).strip()
            chunks.append(self._create_subsubsection_chunk(subsubsection_num, subsubsection_title, current_subsection, page_num, chunk_counter))
            return current_section, current_subsection, chunk_counter + 1

        # Regular paragraph - attach to current subsection or section
        if len(para) > 50:  # Only chunk substantial paragraphs
            chunks.append(self._create_paragraph_chunk(para, current_section, current_subsection, page_num, chunk_counter))
            return current_section, current_subsection, chunk_counter + 1

        return current_section, current_subsection, chunk_counter

    def detect_sections(self, pages: List[Tuple[int, str]]) -> List[DocumentChunk]:
        """Detect hierarchical sections and create chunks."""
        logger.info(f"Starting section detection for {len(pages)} pages")
        chunks: List[DocumentChunk] = []
        current_section = None
        current_subsection = None
        chunk_counter = 0

        for page_num, page_text in pages:
            # Skip title page and TOC (first 3 pages)
            if page_num <= 3:
                continue

            # Split into paragraphs
            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]

            for para in paragraphs:
                current_section, current_subsection, chunk_counter = self._process_paragraph(
                    para, current_section, current_subsection, page_num, chunk_counter, chunks
                )

        logger.info(f"Section detection completed. Created {len(chunks)} chunks")
        return chunks

    def ingest(self) -> List[DocumentChunk]:
        logger.info("Starting document ingestion pipeline")
        try:
            pages = self.load_pdf()
            self.chunks = self.detect_sections(pages)
            logger.info(f"Document ingestion completed successfully. Processed {len(self.chunks)} chunks")
            return self.chunks
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            raise


class DenseVectorRetriever:
    def __init__(
        self,
        collection_name: str,
        embed_model: str = OPENAI_EMBED_MODEL,
        qdrant_url: str = QDRANT_URL,
    ):
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.client = QdrantClient(url=qdrant_url)
        self.embedding_dim = 1536
        logger.info(f"Initialized DenseVectorRetriever with collection '{collection_name}' and model '{embed_model}'")

    def _embed(self, text: str) -> List[float]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY is not set")
            raise ValueError("OPENAI_API_KEY is not set.")

        try:
            response = requests.post(
                f"{OPENAI_API_URL}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": self.embed_model, "input": text},
                timeout=60,
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            logger.debug(f"Successfully generated embedding for text (length: {len(text)})")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def create_collection(self):
        logger.info(f"Creating Qdrant collection '{self.collection_name}' with embedding dimension {self.embedding_dim}")
        try:
            self.client.delete_collection(self.collection_name)
            logger.debug(f"Deleted existing collection '{self.collection_name}'")
        except Exception:
            pass

        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
            )
            logger.info(f"Successfully created collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to create collection '{self.collection_name}': {e}")
            raise

    def index_chunks(self, chunks: List[DocumentChunk]):
        logger.info(f"Starting indexing of {len(chunks)} chunks")
        points = []
        for i, chunk in enumerate(chunks):
            embedding = self._embed(chunk.text)
            points.append(PointStruct(id=i, vector=embedding, payload=chunk.to_dict()))
            
            if (i + 1) % 10 == 0:
                logger.debug(f"Processed {i + 1}/{len(chunks)} chunks")

        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Successfully indexed {len(chunks)} chunks in collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to index chunks: {e}")
            raise

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        logger.debug(f"Searching for query: '{query}' with top_k={top_k}")
        try:
            query_embedding = self._embed(query)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=top_k,
            ).points

            retrieved = []
            for result in results:
                chunk = DocumentChunk(**result.payload)
                score = result.score
                retrieved.append((chunk, score))

            logger.info(f"Dense search returned {len(retrieved)} results for query: '{query}'")
            return retrieved
        except Exception as e:
            logger.error(f"Dense search failed for query '{query}': {e}")
            raise


class SparseBM25Retriever:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.bm25: Optional[BM25Okapi] = None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return text.lower().split()

    def index_chunks(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        tokenized_corpus = [self._tokenize(chunk.text) for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        if not self.bm25:
            raise ValueError("BM25 index not built. Call index_chunks() first.")

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_indices]


class HybridRetriever:
    def __init__(
        self,
        dense_retriever: DenseVectorRetriever,
        sparse_retriever: SparseBM25Retriever,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
    ):
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[DocumentChunk, float]],
        sparse_results: List[Tuple[DocumentChunk, float]],
        k: int = 60,
    ) -> List[Tuple[DocumentChunk, float]]:
        scores = defaultdict(float)
        chunk_map = {}

        for rank, (chunk, _) in enumerate(dense_results, start=1):
            scores[chunk.chunk_id] += self.dense_weight / (k + rank)
            chunk_map[chunk.chunk_id] = chunk

        for rank, (chunk, _) in enumerate(sparse_results, start=1):
            scores[chunk.chunk_id] += self.sparse_weight / (k + rank)
            chunk_map[chunk.chunk_id] = chunk

        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(chunk_map[chunk_id], score) for chunk_id, score in sorted_chunks]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        dense_results = self.dense_retriever.search(query, top_k=top_k * 2)
        sparse_results = self.sparse_retriever.search(query, top_k=top_k * 2)
        fused = self.reciprocal_rank_fusion(dense_results, sparse_results)
        return fused[:top_k]


@dataclass
class PolicyEntity:
    entity_id: str
    entity_type: str
    name: str
    description: str
    source_section: str


@dataclass
class PolicyRelationship:
    from_entity: str
    to_entity: str
    relationship_type: str
    description: str


class PolicyKnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_entity(self, entity: PolicyEntity):
        self.graph.add_node(
            entity.entity_id,
            entity_type=entity.entity_type,
            name=entity.name,
            description=entity.description,
            source_section=entity.source_section,
        )

    def add_relationship(self, relationship: PolicyRelationship):
        self.graph.add_edge(
            relationship.from_entity,
            relationship.to_entity,
            relationship_type=relationship.relationship_type,
            description=relationship.description,
        )

    def find_exceptions(self, role: str) -> List[Dict[str, str]]:
        normalized = role.strip().lower()
        role_aliases = {
            "vp": "role_vp",
            "vice president": "role_vp",
            "manager": "role_manager",
            "employee": "role_employee",
        }
        role_id = role_aliases.get(normalized, f"role_{normalized.replace(' ', '_')}")
        if role_id not in self.graph:
            return []

        exceptions = []
        for neighbor in self.graph.successors(role_id):
            edge_data = self.graph.get_edge_data(role_id, neighbor)
            if edge_data and edge_data.get("relationship_type") == "has_exception":
                node = self.graph.nodes[neighbor]
                exceptions.append(
                    {
                        "name": node.get("name", ""),
                        "description": node.get("description", ""),
                        "source_section": node.get("source_section", ""),
                    }
                )
        return exceptions


def build_policy_graph() -> PolicyKnowledgeGraph:
    kg = PolicyKnowledgeGraph()

    kg.add_entity(
        PolicyEntity(
            entity_id="role_vp",
            entity_type="role",
            name="Vice President",
            description="VP level and above",
            source_section="9.1",
        )
    )
    kg.add_entity(
        PolicyEntity(
            entity_id="role_manager",
            entity_type="role",
            name="Manager",
            description="Manager and Director level",
            source_section="General",
        )
    )
    kg.add_entity(
        PolicyEntity(
            entity_id="role_employee",
            entity_type="role",
            name="Employee",
            description="Standard employee",
            source_section="General",
        )
    )

    exceptions = [
        PolicyEntity(
            entity_id="exception_vp_first_class",
            entity_type="exception",
            name="VP First Class Exception",
            description="VPs and above may book Business or First Class for domestic flights",
            source_section="9.1.1",
        ),
        PolicyEntity(
            entity_id="exception_vp_meal_50",
            entity_type="exception",
            name="VP $50 Meal Limit",
            description="VPs and above have an individual meal limit of $50",
            source_section="9.2.1",
        ),
        PolicyEntity(
            entity_id="exception_vp_client_dinner_250",
            entity_type="exception",
            name="VP $250 Client Dinner Limit",
            description="VPs and above have a client dinner limit of $250 per person",
            source_section="9.2.2",
        ),
        PolicyEntity(
            entity_id="exception_vp_no_attendee_limit",
            entity_type="exception",
            name="VP No Attendee Limit",
            description="The max attendee limit of 4 does not apply to executive-hosted events",
            source_section="9.2.2",
        ),
    ]
    for entity in exceptions:
        kg.add_entity(entity)

    for exception_id, description in [
        ("exception_vp_first_class", "VPs can fly first class"),
        ("exception_vp_meal_50", "VPs have higher meal limit"),
        ("exception_vp_client_dinner_250", "VPs have higher client dinner limit"),
        ("exception_vp_no_attendee_limit", "VPs have no attendee limit"),
    ]:
        kg.add_relationship(
            PolicyRelationship(
                from_entity="role_vp",
                to_entity=exception_id,
                relationship_type="has_exception",
                description=description,
            )
        )

    return kg


@st.cache_resource(show_spinner=False)
def initialize_retrievers(pdf_path: str, collection_name: str):
    logger.info(f"Initializing retrievers for PDF: {pdf_path}, collection: {collection_name}")
    try:
        pipeline = DocumentIngestionPipeline(pdf_path)
        chunks = pipeline.ingest()

        dense = DenseVectorRetriever(collection_name=collection_name)
        dense.create_collection()
        dense.index_chunks(chunks)

        sparse = SparseBM25Retriever()
        sparse.index_chunks(chunks)

        hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse)
        logger.info(f"Successfully initialized all retrievers with {len(chunks)} chunks")
        return chunks, dense, sparse, hybrid
    except Exception as e:
        logger.error(f"Failed to initialize retrievers: {e}")
        raise


def render_results(results: List[Tuple[DocumentChunk, float]], score_label: str):
    if not results:
        logger.warning("No results found to render")
        st.warning("No results found.")
        return

    logger.info(f"Rendering {len(results)} results with score label: {score_label}")
    for i, (chunk, score) in enumerate(results, start=1):
        title = f"Result {i} | {score_label}: {score:.4f}"
        with st.expander(title, expanded=(i == 1)):
            st.markdown(f"**Section:** {chunk.section_number} - {chunk.section_title or '(paragraph)'}")
            st.markdown(f"**Page:** {chunk.page_number}")
            st.markdown(f"**Type:** {chunk.chunk_type}")
            hierarchy = " > ".join(chunk.hierarchy_path) if chunk.hierarchy_path else "N/A"
            st.markdown(f"**Hierarchy:** {hierarchy}")
            st.write(chunk.text)


def _render_sidebar() -> Tuple[str, str, int]:
    """Render sidebar configuration and return user inputs."""
    logger.debug("Rendering sidebar configuration")
    with st.sidebar:
        st.header("Configuration")
        pdf_path = st.text_input("Policy PDF path", value="sample_expense_policy.pdf")
        collection_name = st.text_input("Qdrant collection", value=DEFAULT_COLLECTION)
        top_k = st.slider("Top K", min_value=1, max_value=10, value=5)

        st.markdown("### Services required")
        st.markdown("- OpenAI API key in `OPENAI_API_KEY`")
        st.markdown("- Qdrant on `http://localhost:6333`")
    
    logger.debug(f"Sidebar configuration - PDF: {pdf_path}, Collection: {collection_name}, Top K: {top_k}")
    return pdf_path, collection_name, top_k

def _validate_pdf_path(pdf_path: str) -> Optional[Path]:
    """Validate and resolve PDF path."""
    logger.debug(f"Validating PDF path: {pdf_path}")
    resolved_pdf_path = resolve_pdf_path(pdf_path)
    if not resolved_pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        st.error(f"PDF not found: {pdf_path}")
        st.stop()
    
    # Validate PDF file integrity
    try:
        from pypdf import PdfReader
        reader = PdfReader(resolved_pdf_path)
        # Try to access first page to validate PDF structure
        if len(reader.pages) > 0:
            _ = reader.pages[0].extract_text() or ""
        logger.info(f"✓ PDF validated: {len(reader.pages)} pages found")
    except Exception as pdf_error:
        logger.error(f"❌ PDF file is corrupted or invalid: {pdf_error}")
        st.error(f"❌ PDF file is corrupted or invalid: {pdf_error}")
        st.error("Please try regenerating the PDF or using a different file.")
        st.stop()
    
    return resolved_pdf_path

def _initialize_retrievers(pdf_path: str, collection_name: str) -> Tuple[List[DocumentChunk], Any, Any, Any]:
    """Initialize all retriever systems with enhanced error handling."""
    logger.info(f"Starting retriever initialization for PDF: {pdf_path}")
    with st.spinner("Building indexes (PDF ingestion + embeddings + BM25)..."):
        try:
            chunks, dense, sparse, hybrid = initialize_retrievers(pdf_path, collection_name)
            logger.info(f"✓ Indexed {len(chunks)} chunks successfully.")
            st.success(f"✓ Indexed {len(chunks)} chunks successfully.")
            return chunks, dense, sparse, hybrid
        except Exception as exc:
            logger.error(f"❌ Failed to initialize retrievers: {exc}")
            st.error(f"❌ Failed to initialize retrievers: {exc}")
            
            # Provide specific guidance based on error type
            if "timed out" in str(exc).lower():
                logger.warning("Initialization timeout detected")
                st.error("⏰ Initialization timed out. This could be due to:")
                st.error("  • Large PDF file size")
                st.error("  • Network connectivity issues")
                st.error("  • Service unavailability")
                st.info("💡 Try using a smaller PDF or check your network connections.")
            elif "pdf" in str(exc).lower() or "startxref" in str(exc).lower():
                logger.warning("PDF parsing error detected")
                st.error("📄 PDF parsing error detected:")
                st.error("  • Corrupted PDF file")
                st.error("  • Invalid PDF format")
                st.info("💡 Please regenerate the PDF file and try again.")
            else:
                logger.error("Unexpected error during retriever initialization")
                st.error("🔧 Unexpected error occurred.")
                st.info("💡 Check your environment variables and service connections.")
            
            st.stop()

def _render_dense_tab(dense_retriever: Any, top_k: int, tab_dense: Any):
    """Render dense search tab."""
    logger.debug("Rendering dense search tab")
    with tab_dense:
        query = st.text_input("Dense query", value="What is the meal limit for individual employees?")
        if st.button("Run dense search", type="primary"):
            logger.info(f"Running dense search for query: '{query}'")
            try:
                results = dense_retriever.search(query=query, top_k=top_k)
                render_results(results, "Dense score")
            except Exception as exc:
                logger.error(f"Dense search failed: {exc}")
                st.error(f"Dense search failed: {exc}")

def _render_sparse_tab(sparse_retriever: Any, top_k: int, tab_sparse: Any):
    """Render BM25 search tab."""
    logger.debug("Rendering BM25 search tab")
    with tab_sparse:
        query = st.text_input("BM25 query", value="PROJ-2024-001")
        if st.button("Run BM25 search", type="primary"):
            logger.info(f"Running BM25 search for query: '{query}'")
            try:
                results = sparse_retriever.search(query=query, top_k=top_k)
                render_results(results, "BM25 score")
            except Exception as exc:
                logger.error(f"BM25 search failed: {exc}")
                st.error(f"BM25 search failed: {exc}")

def _render_hybrid_tab(hybrid_retriever: Any, top_k: int, tab_hybrid: Any):
    """Render hybrid search tab."""
    logger.debug("Rendering hybrid search tab")
    with tab_hybrid:
        query = st.text_input("Hybrid query", value="Can VP fly first class?")
        if st.button("Run hybrid search", type="primary"):
            logger.info(f"Running hybrid search for query: '{query}'")
            try:
                results = hybrid_retriever.search(query=query, top_k=top_k)
                render_results(results, "RRF score")
            except Exception as exc:
                logger.error(f"Hybrid search failed: {exc}")
                st.error(f"Hybrid search failed: {exc}")

def _render_graph_tab(tab_graph: Any):
    """Render GraphRAG exceptions tab."""
    logger.debug("Rendering GraphRAG exceptions tab")
    with tab_graph:
        kg = build_policy_graph()
        role = st.selectbox("Role", options=["Vice President", "Manager", "Employee"])
        if st.button("Find role exceptions", type="primary"):
            logger.info(f"Finding exceptions for role: '{role}'")
            exceptions = kg.find_exceptions(role)
            if not exceptions:
                logger.info(f"No exceptions found for role: {role}")
                st.info("No exceptions found for this role.")
            else:
                logger.info(f"Found {len(exceptions)} exceptions for role: {role}")
                for item in exceptions:
                    st.markdown(f"**{item['name']}**")
                    st.write(item["description"])
                    st.caption(f"Source Section: {item['source_section']}")

def main():
    """Entry point for Streamlit UI, orchestrating initialization and UI rendering."""
    logger.info("Starting Streamlit application")
    load_root_env_file()

    st.set_page_config(page_title="Module 3 RAG Systems", layout="wide")
    st.title("Module 3: RAG Systems UI")
    st.caption("Hierarchical chunking + Dense retrieval + BM25 + Hybrid fusion + GraphRAG exceptions")

    # Get configuration from sidebar
    pdf_path, collection_name, top_k = _render_sidebar()
    
    # Validate PDF path
    resolved_pdf_path = _validate_pdf_path(pdf_path)
    if not resolved_pdf_path:
        return
    
    # Initialize retrievers
    chunks, dense, sparse, hybrid = _initialize_retrievers(str(resolved_pdf_path), collection_name)
    
    # Create tabs
    tab_dense, tab_sparse, tab_hybrid, tab_graph = st.tabs(
        ["Dense", "BM25", "Hybrid", "GraphRAG Exceptions"]
    )

    # Render tab content
    _render_dense_tab(dense, top_k, tab_dense)
    _render_sparse_tab(sparse, top_k, tab_sparse)
    _render_hybrid_tab(hybrid, top_k, tab_hybrid)
    _render_graph_tab(tab_graph)
    
    logger.info("Streamlit application initialized successfully")


if __name__ == "__main__":
    main()
