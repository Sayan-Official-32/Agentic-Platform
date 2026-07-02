-- Migration 003: document_chunks with pgvector (384 dims for MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS document_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_id       UUID NOT NULL REFERENCES user_files(id) ON DELETE CASCADE,
    content       TEXT NOT NULL,
    embedding     VECTOR(384),
    chunk_index   INTEGER NOT NULL,
    page_number   INTEGER,
    section       TEXT,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_user_id ON document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON document_chunks(file_id);
