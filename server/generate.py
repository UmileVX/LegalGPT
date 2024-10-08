import os

from dotenv import load_dotenv

load_dotenv()

import logging

from app.engine.loader import get_documents
from app.engine.utils import init_pg_vector_store_from_env
from app.settings import init_settings
from llama_index.core import (SimpleDirectoryReader, StorageContext,
                              VectorStoreIndex)
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.storage import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore

# set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def generate_datasource_milvus(embed_model):
    try:
        milvus_uri = os.getenv("MILVUS_URI")
        milvus_api_key = os.getenv("MILVUS_API_KEY")
        milvus_collection = os.getenv("MILVUS_COLLECTION")
        milvus_dimension = int(os.getenv("MILVUS_DIMENSION"))

        if not all([milvus_uri, milvus_api_key, milvus_collection, milvus_dimension]):
            raise ValueError("Missing required environment variables.")

        # Create MilvusVectorStore 
        vector_store = MilvusVectorStore(
            uri=milvus_uri,
            token=milvus_api_key,
            collection_name=milvus_collection,
            dim=milvus_dimension, # mandatory for new collection creation
            overwrite=True, # mandatory for new collection creation 
        )

        # Create StorageContext
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # create the sentence window node parser
        node_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )

        documents = SimpleDirectoryReader("data").load_data()
        nodes = node_parser.get_nodes_from_documents(documents)
        index = VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)  # noqa: E501

        return index
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid environment variables: {e}")
    except ConnectionError as e:
        raise ConnectionError(f"Failed to connect to Milvus: {e}")


def generate_datasource():
    logger.info("Creating new index")
    # load the documents and create the index
    documents = get_documents()
    store = init_pg_vector_store_from_env()
    storage_context = StorageContext.from_defaults(vector_store=store)
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,  # this will show you a progress bar as the embeddings are created  # noqa: E501
    )
    logger.info(f"Successfully created embeddings in the PG vector store, schema={store.schema_name} table={store.table_name}")  # noqa: E501


if __name__ == "__main__":
    init_settings()

    use_milvus = os.getenv("USE_MILVUS", "false").lower() == "true"
    if use_milvus:
        embed_model=OpenAIEmbedding(model="text-embedding-3-large", embed_batch_size=100)  # noqa: E501
        generate_datasource_milvus(embed_model)
    else:
        generate_datasource()
