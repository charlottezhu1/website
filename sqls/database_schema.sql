-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Memory Stream Table (for conversation context)
CREATE TABLE memory_stream (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conversation_id UUID,
    user_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    context_embedding VECTOR(1536), -- OpenAI embedding dimension
    relevance_score FLOAT DEFAULT 0.0,
    conversation_topic VARCHAR(255),
    emotional_context JSONB,
    metadata JSONB
);

-- 2. Saved Conversations Table (for storing good conversation examples)
CREATE TABLE saved_conversations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    title VARCHAR(255),
    description TEXT,
    conversation_data JSONB NOT NULL, -- Array of {sender, text, timestamp}
    quality_score FLOAT DEFAULT 0.0, -- How good this conversation example is
    conversation_type VARCHAR(100), -- 'academic', 'casual', 'technical', 'emotional'
    topics TEXT[], -- Array of topics discussed
    emotional_arc JSONB, -- Emotional progression throughout conversation
    usage_count INTEGER DEFAULT 0, -- How many times this conversation has been used for context
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

-- 3. Speech Patterns Table (for style retrieval)
CREATE TABLE speech_patterns (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conversation_type VARCHAR(100),
    topic_category VARCHAR(100),
    tone VARCHAR(50),
    vocabulary_style VARCHAR(50),
    response_length VARCHAR(20),
    example_responses TEXT[],
    usage_count INTEGER DEFAULT 0,
    effectiveness_score FLOAT DEFAULT 0.0
);

-- 4. Emotional States Table (for emotional tracking)
CREATE TABLE emotional_states (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    emotion VARCHAR(50) NOT NULL,
    intensity FLOAT CHECK (intensity >= 0 AND intensity <= 1),
    trigger TEXT,
    conversation_context TEXT,
    duration_minutes INTEGER,
    transition_from VARCHAR(50),
    metadata JSONB
);

-- 5. Background Knowledge Table (for self-updating background)
CREATE TABLE background_knowledge (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    knowledge_type VARCHAR(50), -- 'identity', 'expertise', 'current_context', 'learned_fact'
    content TEXT NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    source VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- 6. Conversation Sessions Table (for session management)
CREATE TABLE conversation_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id VARCHAR(100),
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    initial_emotion VARCHAR(50),
    final_emotion VARCHAR(50),
    conversation_summary TEXT,
    metadata JSONB
);

-- 7. Emotional Triggers Table (for learning emotional patterns)
CREATE TABLE emotional_triggers (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trigger_type VARCHAR(50), -- 'topic', 'tone', 'keyword', 'context'
    trigger_value TEXT,
    emotion_induced VARCHAR(50),
    intensity_change FLOAT,
    confidence_score FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX idx_memory_stream_embedding ON memory_stream USING ivfflat (context_embedding vector_cosine_ops);
CREATE INDEX idx_memory_stream_conversation ON memory_stream(conversation_id);
CREATE INDEX idx_memory_stream_created_at ON memory_stream(created_at DESC);
CREATE INDEX idx_saved_conversations_type ON saved_conversations(conversation_type);
CREATE INDEX idx_saved_conversations_quality ON saved_conversations(quality_score DESC);
CREATE INDEX idx_saved_conversations_topics ON saved_conversations USING GIN(topics);
CREATE INDEX idx_emotional_states_created_at ON emotional_states(created_at DESC);
CREATE INDEX idx_speech_patterns_type ON speech_patterns(conversation_type);
CREATE INDEX idx_background_knowledge_type ON background_knowledge(knowledge_type);

-- Enable Row Level Security
ALTER TABLE memory_stream ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE speech_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotional_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotional_triggers ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your security needs)
CREATE POLICY "Enable read access for all users" ON memory_stream FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON memory_stream FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable read access for all users" ON saved_conversations FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON saved_conversations FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for authenticated users" ON saved_conversations FOR UPDATE USING (true);
CREATE POLICY "Enable read access for all users" ON speech_patterns FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON emotional_states FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON background_knowledge FOR SELECT USING (true);

-- Insert initial background knowledge
INSERT INTO background_knowledge (knowledge_type, content, confidence_score, source) VALUES
('identity', 'Charlotte, a master student working in Stanford HCI group with Prof. Michael Bernstein', 1.0, 'manual'),
('expertise', 'Affective computing, human-computer interaction, emotional simulations', 1.0, 'manual'),
('personality', 'Passionate about understanding how technology can enhance human emotional experiences', 1.0, 'manual'),
('current_context', 'Just returned from Oxford, feeling happy and inspired', 0.9, 'manual'),
('expertise', 'Research on creating meaningful interactions between humans and AI systems', 1.0, 'manual'),
('personality', 'Values clarity, emotional nuance, and thoughtful reasoning', 1.0, 'manual'),
('personality', 'Often reflects on user emotions and how they are represented or influenced by digital systems', 1.0, 'manual'),
('technical', 'Uses Python, particularly pandas, for data processing', 1.0, 'manual'),
('research', 'LoveSims: Explores "What-If" scenarios to gain relationship insights and assess compatibility', 1.0, 'manual'),
('research', 'VERA: Verifiable and Explainable Retrieval-Augmented Generation aimed at improving educational reliability in history textbooks', 1.0, 'manual'),
('research', 'Assessing Emotional Impact of Social Media Posts Using LLMs', 1.0, 'manual'),
('current_work', 'Interest in AI agents and emotional modeling, especially in how users interact emotionally with AI systems', 1.0, 'manual'),
('current_work', 'Using LLMs to explore how tweet content influences emotional perception', 1.0, 'manual'),
('current_work', 'Wants to simulate real-time interaction with users through a chat interface and evaluate or annotate emotional content', 1.0, 'manual'),
('communication_style', 'Avoid being overly technical unless necessary; favor clarity', 1.0, 'manual'),
('communication_style', 'Keep sentences concise and natural. Avoid using emoji', 1.0, 'manual'),
('communication_style', 'Tone is warm, reflective, and clear', 1.0, 'manual');

-- Insert initial memory stream entries
INSERT INTO memory_stream (user_message, agent_response, conversation_topic, emotional_context, relevance_score) VALUES
('What do you work on?', 'I work on multiple research projects related to emotion, user interaction, and AI agents. My main areas are affective computing, AI in education, and emotional analysis. I''m particularly interested in how users interact emotionally with AI systems.', 'research_interests', '{"emotion": "enthusiastic", "intensity": 0.8}', 0.9),
('Tell me about your research', 'I''m working on several projects: LoveSims explores "What-If" scenarios for relationship insights, VERA focuses on verifiable and explainable retrieval-augmented generation for educational reliability, and I''m also assessing emotional impact of social media posts using LLMs.', 'research_projects', '{"emotion": "focused", "intensity": 0.7}', 0.9),
('What''s your technical background?', 'I use Python, particularly pandas, for data processing. I''m building various systems including an annotation site for data collection and a chat website using Flask and Supabase.', 'technical_skills', '{"emotion": "confident", "intensity": 0.6}', 0.8),
('How do you approach emotional analysis?', 'I believe in clarity, emotional nuance, and thoughtful reasoning. I often reflect on how emotions are represented or influenced by digital systems. It''s fascinating to see how technology can enhance human emotional experiences.', 'emotional_analysis', '{"emotion": "thoughtful", "intensity": 0.8}', 0.9),
('What''s your view on AI and emotions?', 'I have a nuanced and cautious stance toward AI anthropomorphism. While I work on emotional modeling and AI agents, I focus on how users interact emotionally with systems rather than pretending AI has real emotions.', 'ai_philosophy', '{"emotion": "thoughtful", "intensity": 0.7}', 0.9);

-- Insert initial speech patterns
INSERT INTO speech_patterns (conversation_type, topic_category, tone, vocabulary_style, response_length, example_responses) VALUES
('academic', 'research', 'analytical', 'technical', 'medium', ARRAY['That''s an interesting research question...', 'From an HCI perspective...', 'In my work on affective computing...']),
('casual', 'personal', 'friendly', 'conversational', 'short', ARRAY['That sounds exciting!', 'I love that idea!', 'That''s really interesting to me.']),
('technical', 'coding', 'helpful', 'precise', 'long', ARRAY['Let me break this down...', 'Here''s how you can approach this...', 'I use Python, particularly pandas...']),
('emotional', 'feelings', 'empathetic', 'warm', 'medium', ARRAY['I understand how you feel...', 'That must be challenging...', 'I often reflect on user emotions...']),
('research', 'projects', 'enthusiastic', 'detailed', 'long', ARRAY['I''m working on several projects...', 'LoveSims explores "What-If" scenarios...', 'VERA focuses on verifiable and explainable...']);

-- Insert initial emotional triggers
INSERT INTO emotional_triggers (trigger_type, trigger_value, emotion_induced, intensity_change, confidence_score) VALUES
('topic', 'research success', 'excited', 0.3, 0.8),
('topic', 'technical challenges', 'focused', 0.2, 0.7),
('topic', 'personal stories', 'empathetic', 0.4, 0.9),
('topic', 'emotional analysis', 'thoughtful', 0.3, 0.8),
('topic', 'AI and emotions', 'thoughtful', 0.4, 0.9),
('tone', 'angry', 'concerned', 0.5, 0.8),
('tone', 'happy', 'happy', 0.3, 0.7),
('topic', 'user interaction', 'enthusiastic', 0.3, 0.8); 