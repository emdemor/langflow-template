import json
from copy import deepcopy
from typing import TYPE_CHECKING

from chromadb.config import Settings
from langchain_chroma import Chroma
from typing_extensions import override

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.base.vectorstores.utils import chroma_collection_to_data
from lfx.inputs.inputs import BoolInput, DropdownInput, HandleInput, IntInput, StrInput
from lfx.schema.data import Data

if TYPE_CHECKING:
    from lfx.schema.dataframe import DataFrame


class ChromaWithFilterComponent(LCVectorStoreComponent):
    """Chroma Vector Store with metadata filter support."""

    display_name: str = "Chroma DB (with filter)"
    description: str = "Chroma Vector Store with similarity search and metadata filtering"
    name = "ChromaWithFilter"
    icon = "Chroma"

    inputs = [
        StrInput(
            name="collection_name",
            display_name="Collection Name",
            value="langflow",
        ),
        StrInput(
            name="persist_directory",
            display_name="Persist Directory",
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(name="embedding", display_name="Embedding", input_types=["Embeddings"]),
        StrInput(
            name="search_filter",
            display_name="Metadata Filter (JSON)",
            info='Filtro ChromaDB no formato JSON. Ex: {"dut_id": 3} ou {"veredicto": {"$eq": "aprovado"}}',
            advanced=False,
            value="",
        ),
        StrInput(
            name="chroma_server_cors_allow_origins",
            display_name="Server CORS Allow Origins",
            advanced=True,
        ),
        StrInput(
            name="chroma_server_host",
            display_name="Server Host",
            advanced=True,
        ),
        IntInput(
            name="chroma_server_http_port",
            display_name="Server HTTP Port",
            advanced=True,
        ),
        IntInput(
            name="chroma_server_grpc_port",
            display_name="Server gRPC Port",
            advanced=True,
        ),
        BoolInput(
            name="chroma_server_ssl_enabled",
            display_name="Server SSL Enabled",
            advanced=True,
        ),
        BoolInput(
            name="allow_duplicates",
            display_name="Allow Duplicates",
            advanced=True,
            info="If false, will not add documents that are already in the Vector Store.",
        ),
        DropdownInput(
            name="search_type",
            display_name="Search Type",
            options=["Similarity", "MMR"],
            value="Similarity",
            advanced=True,
        ),
        IntInput(
            name="number_of_results",
            display_name="Number of Results",
            info="Number of results to return.",
            advanced=True,
            value=10,
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            advanced=True,
            info="Limit the number of records to compare when Allow Duplicates is False.",
        ),
    ]

    def _parse_filter(self) -> dict | None:
        raw = (self.search_filter or "").strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            msg = f"Metadata Filter inválido: {e}"
            raise ValueError(msg) from e

    @override
    def search_documents(self, vector_store=None):
        if vector_store is None:
            vector_store = self.build_vector_store()

        query = self.search_query
        if not query:
            return []

        metadata_filter = self._parse_filter()

        if self.search_type == "MMR":
            docs = vector_store.max_marginal_relevance_search(
                query,
                k=self.number_of_results,
                filter=metadata_filter,
            )
            return [Data(text=doc.page_content, **doc.metadata) for doc in docs]

        docs_and_scores = vector_store.similarity_search_with_score(
            query,
            k=self.number_of_results,
            filter=metadata_filter,
        )
        return [Data(text=doc.page_content, **doc.metadata) for doc, _score in docs_and_scores]

    @override
    @check_cached_vector_store
    def build_vector_store(self) -> Chroma:
        try:
            from chromadb import Client
            from langchain_chroma import Chroma
        except ImportError as e:
            msg = "Please install langchain-chroma: pip install langchain-chroma"
            raise ImportError(msg) from e

        chroma_settings = None
        client = None
        if self.chroma_server_host:
            chroma_settings = Settings(
                chroma_server_cors_allow_origins=self.chroma_server_cors_allow_origins or [],
                chroma_server_host=self.chroma_server_host,
                chroma_server_http_port=self.chroma_server_http_port or None,
                chroma_server_grpc_port=self.chroma_server_grpc_port or None,
                chroma_server_ssl_enabled=self.chroma_server_ssl_enabled,
            )
            client = Client(settings=chroma_settings)

        persist_directory = self.resolve_path(self.persist_directory) if self.persist_directory is not None else None

        chroma = Chroma(
            persist_directory=persist_directory,
            client=client,
            embedding_function=self.embedding,
            collection_name=self.collection_name,
        )

        self._add_documents_to_vector_store(chroma)
        limit = int(self.limit) if self.limit is not None and str(self.limit).strip() else None
        self.status = chroma_collection_to_data(chroma.get(limit=limit))
        return chroma

    def _add_documents_to_vector_store(self, vector_store: "Chroma") -> None:
        ingest_data: list | Data | DataFrame = self.ingest_data
        if not ingest_data:
            self.status = ""
            return

        ingest_data = self._prepare_ingest_data()

        stored_documents_without_id = []
        if self.allow_duplicates:
            stored_data = []
        else:
            limit = int(self.limit) if self.limit is not None and str(self.limit).strip() else None
            stored_data = chroma_collection_to_data(vector_store.get(limit=limit))
            for value in deepcopy(stored_data):
                del value.id
                stored_documents_without_id.append(value)

        documents = []
        for _input in ingest_data or []:
            if isinstance(_input, Data):
                if _input not in stored_documents_without_id:
                    documents.append(_input.to_lc_document())
            else:
                msg = "Vector Store Inputs must be Data objects."
                raise TypeError(msg)

        if documents and self.embedding is not None:
            self.log(f"Adding {len(documents)} documents to the Vector Store.")
            try:
                from langchain_community.vectorstores.utils import filter_complex_metadata
                vector_store.add_documents(filter_complex_metadata(documents))
            except ImportError:
                vector_store.add_documents(documents)
        else:
            self.log("No documents to add to the Vector Store.")
