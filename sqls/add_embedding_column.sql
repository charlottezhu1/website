-- Add embedding column to saved_conversations table
ALTER TABLE saved_conversations
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Add embedding column to memory_stream table
ALTER TABLE memory_stream
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create an index for similarity search
CREATE INDEX IF NOT EXISTS saved_conversations_embedding_idx 
ON saved_conversations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS memory_stream_embedding_idx 
ON memory_stream 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Enable the vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Update existing rows to have empty embedding arrays
UPDATE memory_stream 
SET context_embedding = '[]'::vector 
WHERE context_embedding IS NULL; 