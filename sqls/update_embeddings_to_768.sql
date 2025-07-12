-- Update embedding columns to use 768 dimensions for intfloat/multilingual-e5-base model

-- Drop existing embedding columns and recreate with new dimensions
ALTER TABLE memory_stream DROP COLUMN IF EXISTS embedding;
ALTER TABLE memory_stream DROP COLUMN IF EXISTS context_embedding;
ALTER TABLE saved_conversations DROP COLUMN IF EXISTS embedding;

-- Add new 768-dimension embedding columns
ALTER TABLE memory_stream ADD COLUMN embedding vector(768);
ALTER TABLE memory_stream ADD COLUMN context_embedding vector(768);
ALTER TABLE saved_conversations ADD COLUMN embedding vector(768);

-- Drop old indexes
DROP INDEX IF EXISTS memory_stream_embedding_idx;
DROP INDEX IF EXISTS saved_conversations_embedding_idx;
DROP INDEX IF EXISTS idx_memory_stream_embedding;
DROP INDEX IF EXISTS memory_stream_context_embedding_idx;

-- Create new indexes for 768-dimension vectors
CREATE INDEX memory_stream_embedding_idx 
ON memory_stream 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX memory_stream_context_embedding_idx 
ON memory_stream 
USING ivfflat (context_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX saved_conversations_embedding_idx 
ON saved_conversations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Clear any existing data since dimensions have changed
UPDATE memory_stream SET embedding = NULL, context_embedding = NULL;
UPDATE saved_conversations SET embedding = NULL;