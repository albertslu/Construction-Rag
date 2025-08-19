from pinecone import Pinecone, ServerlessSpec
from ..config import settings


def main() -> None:
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_index_name

    if index_name not in [idx["name"] for idx in pc.list_indexes()]:
        pc.create_index(
            name=index_name,
            dimension=settings.openai_embedding_dim,
            metric=settings.pinecone_metric,
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )
        print(f"Created Pinecone index: {index_name}")
    else:
        print(f"Pinecone index already exists: {index_name}")


if __name__ == "__main__":
    main()

