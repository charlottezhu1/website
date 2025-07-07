-- Create the saved_conversations table (only this table, since others already exist)
CREATE TABLE saved_conversations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    title VARCHAR(255),
    description TEXT,
    conversation_data JSONB NOT NULL,
    quality_score FLOAT DEFAULT 0.0,
    conversation_type VARCHAR(100),
    topics TEXT[],
    emotional_arc JSONB,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

-- Create indexes for performance
CREATE INDEX idx_saved_conversations_type ON saved_conversations(conversation_type);
CREATE INDEX idx_saved_conversations_quality ON saved_conversations(quality_score DESC);
CREATE INDEX idx_saved_conversations_topics ON saved_conversations USING GIN(topics);

-- Enable Row Level Security
ALTER TABLE saved_conversations ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Enable read access for all users" ON saved_conversations FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON saved_conversations FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for authenticated users" ON saved_conversations FOR UPDATE USING (true); 