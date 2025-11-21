-- Migration: Add User-Based Conversation Tracking
-- Date: 2025-11-20
-- Description: Implements per-user conversation isolation with role-based context

-- ============================================================================
-- PHASE 1: Add user_id columns to existing tables
-- ============================================================================

-- 1.1 Add user_id to memory_stream
-- Allows filtering conversation history by user
ALTER TABLE memory_stream
ADD COLUMN user_id UUID REFERENCES auth.users(id);

CREATE INDEX idx_memory_stream_user ON memory_stream(user_id);

-- 1.2 Add user_id to saved_conversations
-- Isolates saved conversation examples per user
ALTER TABLE saved_conversations
ADD COLUMN user_id UUID REFERENCES auth.users(id);

CREATE INDEX idx_saved_conversations_user ON saved_conversations(user_id);

-- 1.3 Add user_id to emotional_states
-- Tracks emotional state separately for each user
ALTER TABLE emotional_states
ADD COLUMN user_id UUID REFERENCES auth.users(id);

CREATE INDEX idx_emotional_states_user ON emotional_states(user_id);

-- 1.4 Create user_profiles table
-- Stores user metadata including role information for context-aware responses
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(100), -- e.g., 'friend', 'parent', 'colleague'
    role_description TEXT, -- Additional context about the relationship
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    CONSTRAINT valid_role CHECK (role IS NOT NULL)
);

CREATE INDEX idx_user_profiles_role ON user_profiles(role);

-- 1.5 Update conversation_sessions to properly reference auth.users
-- Converts existing user_id from VARCHAR to UUID and adds foreign key
ALTER TABLE conversation_sessions
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid,
    ADD CONSTRAINT fk_conversation_session_user
        FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX idx_conversation_sessions_user ON conversation_sessions(user_id);

-- ============================================================================
-- UPDATE RLS POLICIES for user isolation
-- ============================================================================

-- Enable RLS on user_profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own profile
CREATE POLICY "Users can view own profile"
ON user_profiles FOR SELECT
USING (auth.uid() = id);

-- Policy: Service role can manage all profiles (for server-side operations)
CREATE POLICY "Service role can manage profiles"
ON user_profiles FOR ALL
USING (true);

-- Update memory_stream RLS policies for user filtering
DROP POLICY IF EXISTS "Enable read access for all users" ON memory_stream;
DROP POLICY IF EXISTS "Enable insert for authenticated users" ON memory_stream;

CREATE POLICY "Users can view own memories"
ON memory_stream FOR SELECT
USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert own memories"
ON memory_stream FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Update saved_conversations RLS policies
DROP POLICY IF EXISTS "Enable read access for all users" ON saved_conversations;
DROP POLICY IF EXISTS "Enable insert for authenticated users" ON saved_conversations;
DROP POLICY IF EXISTS "Enable update for authenticated users" ON saved_conversations;

CREATE POLICY "Users can view own conversations"
ON saved_conversations FOR SELECT
USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert own conversations"
ON saved_conversations FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
ON saved_conversations FOR UPDATE
USING (auth.uid() = user_id);

-- Update emotional_states RLS policies
DROP POLICY IF EXISTS "Enable read access for all users" ON emotional_states;

CREATE POLICY "Users can view own emotional states"
ON emotional_states FOR SELECT
USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert own emotional states"
ON emotional_states FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get current user's role
CREATE OR REPLACE FUNCTION get_current_user_role()
RETURNS VARCHAR(100) AS $$
DECLARE
    user_role VARCHAR(100);
BEGIN
    SELECT role INTO user_role
    FROM user_profiles
    WHERE id = auth.uid();

    RETURN COALESCE(user_role, 'unknown');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update last_active timestamp
CREATE OR REPLACE FUNCTION update_user_last_active()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE user_profiles
    SET last_active = NOW()
    WHERE id = NEW.user_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Update last_active when user sends a message
CREATE TRIGGER trigger_update_last_active
AFTER INSERT ON memory_stream
FOR EACH ROW
WHEN (NEW.user_id IS NOT NULL)
EXECUTE FUNCTION update_user_last_active();

-- ============================================================================
-- DATA MIGRATION NOTES
-- ============================================================================

-- IMPORTANT: Existing data in memory_stream, saved_conversations, and
-- emotional_states will have NULL user_id values.
--
-- Options for handling existing data:
-- 1. Delete existing data (clean slate)
-- 2. Keep as shared "bootstrap" memories (user_id = NULL allowed by RLS)
-- 3. Create a system user and assign all existing data to it
--
-- Current approach: Keep existing data as shared memories (NULL user_id)
-- These will be visible to all users through the RLS policies above.

COMMENT ON TABLE user_profiles IS 'Stores user metadata and role information for context-aware agent responses';
COMMENT ON COLUMN user_profiles.role IS 'User relationship to Charlotte (e.g., friend, parent, colleague)';
COMMENT ON COLUMN user_profiles.role_description IS 'Additional context about the relationship used in prompts';
COMMENT ON COLUMN memory_stream.user_id IS 'References auth.users(id). NULL for shared/bootstrap memories';
COMMENT ON COLUMN saved_conversations.user_id IS 'References auth.users(id). NULL for global conversation examples';
COMMENT ON COLUMN emotional_states.user_id IS 'References auth.users(id). NULL for system-level emotional states';
