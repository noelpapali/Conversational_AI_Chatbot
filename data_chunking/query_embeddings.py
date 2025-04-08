import logging
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone
from spacy.lang.en import English

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PineconeQuerySystem:
    def __init__(self):
        # Initialize models and connections
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.nlp = English()  # Lightweight for keyword extraction
        self.nlp.add_pipe("sentencizer")

        # Pinecone connection
        self.pc = Pinecone(api_key="pcsk_6R2ucq_J4vEtoSvYHs21aTArmsRzqRpE6SSgYvV6DKtm3kDZCe6Bei8nVK8jUZoJmbL9f4")
        self.index = self.pc.Index("chatbotv1")

        # Query configuration
        self.default_top_k = 5
        self.similarity_threshold = 0.7

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords using rule-based approach"""
        doc = self.nlp(text)
        return [
            chunk.text.lower()
            for chunk in doc.noun_chunks
            if len(chunk.text) > 2
        ]

    def expand_query(self, query: str) -> List[str]:
        """Generate query variations using heuristic rules"""
        base_queries = [query]

        # Question reformulations
        if "?" in query:
            base_queries.append(query.replace("?", ""))
            base_queries.append("explain " + query.lower())

        # Add keyword-focused queries
        keywords = self.extract_keywords(query)
        if keywords:
            base_queries.extend([
                " ".join(keywords),
                "details about " + " ".join(keywords[:2])
            ])

        return list(set(base_queries))[:4]  # Return max 4 unique variations

    def hybrid_search(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Perform vector + keyword hybrid search"""
        # Vector search
        vector_results = self.vector_search(query, filters)

        # Keyword search (using metadata)
        keyword_results = self.keyword_search(query, filters)

        # Combine and deduplicate results
        combined = {r['id']: r for r in vector_results}
        for r in keyword_results:
            if r['id'] not in combined:
                combined[r['id']] = r

        return sorted(
            combined.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:self.default_top_k]

    def vector_search(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Pure vector similarity search"""
        embedding = self.embedding_model.encode(query).tolist()
        response = self.index.query(
            vector=embedding,
            top_k=self.default_top_k,
            filter=filters,
            include_metadata=True
        )
        return [
            {
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "metadata": match.metadata
            }
            for match in response.matches
            if match.score >= self.similarity_threshold
        ]

    def keyword_search(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Search using keywords in metadata"""
        keywords = self.extract_keywords(query)
        if not keywords:
            return []

        keyword_filter = {
            "keywords": {"$in": keywords}
        }
        if filters:
            keyword_filter = {"$and": [filters, keyword_filter]}

        return self.vector_search(
            " ".join(keywords),
            filters=keyword_filter
        )

    def query_with_fallback(self, query: str) -> List[Dict]:
        """Intelligent query with multiple fallback strategies"""
        # Try exact query first
        results = self.hybrid_search(query)

        # If poor results, try expanded queries
        if not results or all(r['score'] < 0.6 for r in results):
            for variant in self.expand_query(query):
                new_results = self.hybrid_search(variant)
                results.extend(new_results)

            # Deduplicate and re-sort
            results = sorted(
                {r['id']: r for r in results}.values(),
                key=lambda x: x['score'],
                reverse=True
            )[:self.default_top_k]

        return results

    def get_contextual_response(self, query: str, chat_history: List[str] = None) -> str:
        """Full RAG pipeline with context"""
        # Retrieve relevant chunks
        results = self.query_with_fallback(query)

        if not results:
            return "I couldn't find relevant information for your query."

        # Format context for LLM
        context = "\n\n".join(
            f"Source {i + 1} (Score: {res['score']:.2f}):\n{res['text']}"
            for i, res in enumerate(results)
        )

        # Generate response (replace with your actual LLM call)
        prompt = f"""Answer the question using ONLY the provided context.
        If the answer isn't in the context, say you don't know.

        Question: {query}
        Chat History: {chat_history or "None"}
        Context:\n{context}

        Answer:"""

        # Simulated LLM response
        if any(keyword in query.lower() for keyword in ["admission", "apply"]):
            return "Admission requirements include... [simulated response based on context]"
        elif "course" in query.lower():
            return "Related courses include... [simulated response]"
        else:
            return "Here's what I found: [simulated summary of top results]"


class QueryTester:
    """Class to test various query scenarios"""

    @staticmethod
    def get_test_queries() -> List[Tuple[str, Optional[Dict]]]:
        return [
            # Basic information retrieval
            ("What are the admission requirements?", None),
            ("When is the application deadline?", None),

            # Advanced semantic search
            ("Which engineering programs don't require physics?", None),
            ("Find research opportunities in renewable energy", None),

            # Query expansion tests
            ("CS degree reqs", None),
            ("dorms info", None),

            # Metadata filtered queries
            ("What's the refund policy?", {"source": "financial_policies"}),
            ("Who is the CS department chair?", {"department": "computer_science"}),

            # Stress tests
            ("student", None),  # Single vague term
            ("", None)  # Empty query
        ]

    @staticmethod
    def run_tests(query_system: PineconeQuerySystem):
        """Run all test queries and log results"""
        logger.info("Starting query tests...")
        tests = QueryTester.get_test_queries()

        for i, (query, filters) in enumerate(tests, 1):
            logger.info(f"\nTest {i}: '{query}' {f'[Filters: {filters}]' if filters else ''}")

            try:
                results = query_system.hybrid_search(query, filters)
                logger.info(f"Found {len(results)} results")

                if results:
                    for j, res in enumerate(results[:3], 1):  # Show top 3 results
                        logger.info(
                            f"Result {j} (Score: {res['score']:.2f}): "
                            f"{res['text'][:100]}..."
                        )

                # Test contextual response
                response = query_system.get_contextual_response(query)
                logger.info(f"Generated Response: {response[:200]}...")

            except Exception as e:
                logger.error(f"Test failed: {str(e)}")

        logger.info("All tests completed")


def main():
    """Main execution flow"""
    try:
        # Initialize the query system
        query_system = PineconeQuerySystem()

        # Run automated tests
        QueryTester.run_tests(query_system)

        # Interactive query mode
        print("\nInteractive Query Mode (type 'exit' to quit)")
        while True:
            try:
                query = input("\nEnter your question: ").strip()
                if query.lower() in ('exit', 'quit'):
                    break
                if not query:
                    continue

                # Get and display results
                results = query_system.query_with_fallback(query)
                print(f"\nFound {len(results)} results:")
                for i, res in enumerate(results, 1):
                    print(f"\nResult {i} (Score: {res['score']:.2f}):")
                    print(res['text'][:500] + ("..." if len(res['text']) > 500 else ""))

                # Show generated response
                print("\nGenerated Answer:")
                print(query_system.get_contextual_response(query))

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Query failed: {e}")
                print("Sorry, something went wrong. Please try again.")

    except Exception as e:
        logger.critical(f"System failed to initialize: {e}")
        print("System initialization failed. Check logs for details.")


if __name__ == "__main__":
    main()