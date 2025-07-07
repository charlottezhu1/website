-- Add embedding column to memory_stream table
ALTER TABLE memory_stream 
ADD COLUMN context_embedding vector(1536);

-- Add index for vector similarity search (if using pgvector)
-- CREATE INDEX ON memory_stream USING ivfflat (context_embedding vector_cosine_ops);

-- Update existing rows to have empty embedding arrays
UPDATE memory_stream 
SET context_embedding = '[]'::vector 
WHERE context_embedding IS NULL; 