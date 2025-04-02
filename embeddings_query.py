import pinecone
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def initialize_pinecone():
    """Initialize Pinecone connection"""
    pinecone_api_key = os.getenv("pinecone_api_key") or "pcsk_5j5943_Sc7B63x4vFjwtX7X4b5PoF7sDUiwG3uPHqjQMKNphUdhPm6VpGcMTzayYS7S5Km"
    pc = pinecone.Pinecone(api_key=pinecone_api_key)
    index_name = "utd-bot"
    return pc.Index(index_name)


def fetch_all_embeddings(index):
    """Fetch all embeddings from Pinecone index"""
    try:
        # Get index stats to determine dimension
        stats = index.describe_index_stats()
        dimension = stats.dimension
        total_vectors = stats.total_vector_count

        # Create empty vector to query all vectors
        dummy_vector = [0] * dimension

        # Fetch all vectors (adjust top_k based on your total vectors)
        results = index.query(
            vector=dummy_vector,
            top_k=total_vectors,
            include_values=True,
            include_metadata=True
        )

        logger.info(f"Fetched {len(results['matches'])} embeddings from Pinecone")
        return results['matches']
    except Exception as e:
        logger.error(f"Error fetching embeddings: {e}")
        raise


def query_embeddings(index, query_embedding, top_k=5):
    """Query similar embeddings from Pinecone"""
    try:
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return results
    except Exception as e:
        logger.error(f"Error querying Pinecone: {e}")
        raise


def main():
    # Initialize Pinecone
    index = initialize_pinecone()

    # Option 1: Fetch all embeddings
    all_embeddings = fetch_all_embeddings(index)
    for embedding in all_embeddings[:3]:  # Print first 3 as example
        logger.info(f"ID: {embedding['id']}")
        logger.info(f"Vector length: {len(embedding['values'])}")
        if 'metadata' in embedding:
            logger.info(f"Metadata: {embedding['metadata']}")
        logger.info("---")

    # Option 2: Query with a new embedding (example)
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch

        # Initialize model (you would normally do this once at startup)
        tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        model = AutoModel.from_pretrained('bert-base-uncased')

        # Generate query embedding
        text = "Your search query here"
        inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        query_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

        # Query Pinecone
        results = query_embeddings(index, query_embedding)
        logger.info("Query results:")
        for match in results['matches']:
            logger.info(f"ID: {match['id']} | Score: {match['score']:.3f}")
            if 'metadata' in match and 'text' in match['metadata']:
                logger.info(f"Text: {match['metadata']['text'][:100]}...")
            logger.info("---")

    except ImportError:
        logger.warning("Transformers not installed, using random query vector")
        # Fallback random query
        query_embedding = [0.5] * 768  # Example vector matching your dimension
        results = query_embeddings(index, query_embedding)
        logger.info("Query results with random vector:")
        for match in results['matches']:
            logger.info(f"ID: {match['id']} | Score: {match['score']:.3f}")
            if 'metadata' in match:
                logger.info(f"Metadata: {match['metadata']}")
            logger.info("---")


if __name__ == "__main__":
    main()