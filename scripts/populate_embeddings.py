"""
DEPRECATED: This script is no longer active.
Embedding functionality has been disabled to avoid large model dependency (~500MB).
The agent now uses recency-based and metadata-based retrieval instead of semantic similarity.
See agent_components.py for the updated retrieval logic.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from app import create_app, supabase_extension
from sentence_transformers import SentenceTransformer
import time
import threading
from typing import List, Dict, Any
import json

# Global variables for lazy loading
_embedding_model = None
_model_lock = threading.Lock()

def get_embedding_model():
    """Get the embedding model with lazy loading and thread safety"""
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            # Double-check pattern to prevent race conditions
            if _embedding_model is None:
                _embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")
    return _embedding_model


def generate_embedding(text: str) -> List[float] | None:
    """Generate embedding for text using Sentence Transformers intfloat/multilingual-e5-base model"""
    try:
        # Get model with lazy loading
        model = get_embedding_model()
        
        # E5 models require a "query: " prefix for optimal performance
        prefixed_text = f"query: {text}"

        # Generate embedding using sentence transformers (much faster, no rate limits)
        embedding = model.encode(prefixed_text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def process_batch(items: List[Dict], table_name: str) -> int:
    """Process a batch of items to update their embeddings"""
    updated_count = 0

    for item in items:
        try:
            # Generate text for embedding based on table type
            if table_name == "memory_stream":
                text = (
                    f"{item.get('user_message', '')} {item.get('agent_response', '')}"
                )
            else:  # saved_conversations table
                # Extract text from conversation_data JSONB array
                conversation_data = item.get("conversation_data", [])
                if isinstance(conversation_data, list):
                    text_parts = []
                    for msg in conversation_data:
                        if isinstance(msg, dict):
                            text_parts.append(msg.get("text", ""))
                    text = " ".join(text_parts)
                else:
                    text = str(conversation_data)

            # Generate embedding
            embedding = generate_embedding(text)
            if embedding is None:
                print(
                    f"Skipping {table_name} item {item['id']}: Failed to generate embedding"
                )
                continue

            # Update the item with the embedding
            supabase_extension.client.table(table_name).update(
                {"embedding": embedding}
            ).eq("id", item["id"]).execute()

            updated_count += 1
            print(f"Updated {table_name} item {item['id']} with embedding")

            # No delay needed for local Sentence Transformers model

        except Exception as e:
            print(f"Error processing {table_name} item {item['id']}: {e}")
            continue

    return updated_count


def main():
    """Main function to populate embeddings"""
    try:
        print("Starting embedding population process...")

        # Create Flask app and push context
        app = create_app()
        with app.app_context():
            # Get all memories without embeddings from both tables
            memory_response = (
                supabase_extension.client.table("memory_stream")
                .select("*")
                .is_("embedding", "null")
                .execute()
            )

            saved_conversations_response = (
                supabase_extension.client.table("saved_conversations")
                .select("*")
                .is_("embedding", "null")
                .execute()
            )

            total_updated = 0

            # Process memory_stream in batches
            if memory_response.data:
                print(
                    f"\nProcessing {len(memory_response.data)} memory stream items..."
                )
                batch_size = 50  # Larger batch size since local model is faster
                for i in range(0, len(memory_response.data), batch_size):
                    batch = memory_response.data[i : i + batch_size]
                    updated = process_batch(batch, "memory_stream")
                    total_updated += updated
                    print(
                        f"Completed batch {i//batch_size + 1} of {(len(memory_response.data) + batch_size - 1)//batch_size}"
                    )
                    # No delay needed for local model

            # Process saved conversations in batches
            if saved_conversations_response.data:
                print(
                    f"\nProcessing {len(saved_conversations_response.data)} saved conversations..."
                )
                batch_size = 50  # Larger batch size since local model is faster
                for i in range(0, len(saved_conversations_response.data), batch_size):
                    batch = saved_conversations_response.data[i : i + batch_size]
                    updated = process_batch(batch, "saved_conversations")
                    total_updated += updated
                    print(
                        f"Completed batch {i//batch_size + 1} of {(len(saved_conversations_response.data) + batch_size - 1)//batch_size}"
                    )
                    # No delay needed for local model

            print(
                f"\nPopulation complete! Updated {total_updated} items with embeddings"
            )

    except Exception as e:
        print(f"Error in main process: {e}")
        raise


if __name__ == "__main__":
    main()
