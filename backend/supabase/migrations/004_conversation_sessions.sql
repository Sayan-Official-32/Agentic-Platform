-- Migration 004: conversation_sessions table
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id TEXT UNIQUE NOT NULL,
    title           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_conv_id ON conversation_sessions(conversation_id);
