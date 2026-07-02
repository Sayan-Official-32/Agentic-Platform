-- Migration 002: user_files table (9 file types)
CREATE TABLE IF NOT EXISTS user_files (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name     TEXT NOT NULL,
    file_type     TEXT NOT NULL CHECK (file_type IN ('pdf','docx','txt','csv','xlsx','pptx','html','json','md')),
    storage_path  TEXT NOT NULL,
    file_size     BIGINT,
    chunk_count   INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'processing' CHECK (status IN ('processing','ready','failed')),
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_files_user_id ON user_files(user_id);
CREATE INDEX IF NOT EXISTS idx_user_files_status  ON user_files(status);
