import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from app import create_app, supabase_extension
from openai import OpenAI
from settings import OPENAI_API_KEY
import time
from typing import List, Dict, Any
import json

# Initialize OpenAI client
client_openai = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.openai.com/v1")


def generate_embedding(text: str) -> List[float] | None:
    """Generate embedding for text using OpenAI's text-embedding-ada-002 model"""
    try:
        # Add a small delay to respect rate limits
        time.sleep(0.1)

        response = client_openai.embeddings.create(
            model="text-embedding-ada-002", input=text, encoding_format="float"
        )
        return response.data[0].embedding
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
            else:  # user_message table
                text = item.get("message", "")  # Get the message directly

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

            # Add delay between items
            time.sleep(0.5)

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

            user_messages_response = (
                supabase_extension.client.table("user_message")
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
                batch_size = 10
                for i in range(0, len(memory_response.data), batch_size):
                    batch = memory_response.data[i : i + batch_size]
                    updated = process_batch(batch, "memory_stream")
                    total_updated += updated
                    print(
                        f"Completed batch {i//batch_size + 1} of {(len(memory_response.data) + batch_size - 1)//batch_size}"
                    )
                    time.sleep(1)  # Delay between batches

            # Process user messages in batches
            if user_messages_response.data:
                print(
                    f"\nProcessing {len(user_messages_response.data)} user messages..."
                )
                batch_size = 10  # Can use regular batch size since messages are simpler
                for i in range(0, len(user_messages_response.data), batch_size):
                    batch = user_messages_response.data[i : i + batch_size]
                    updated = process_batch(batch, "user_message")
                    total_updated += updated
                    print(
                        f"Completed batch {i//batch_size + 1} of {(len(user_messages_response.data) + batch_size - 1)//batch_size}"
                    )
                    time.sleep(1)  # Delay between batches

            print(
                f"\nPopulation complete! Updated {total_updated} items with embeddings"
            )

    except Exception as e:
        print(f"Error in main process: {e}")
        raise


if __name__ == "__main__":
    main()
