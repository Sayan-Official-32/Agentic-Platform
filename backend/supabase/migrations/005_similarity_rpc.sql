-- Migration 005: Cosine similarity search database RPC function
DROP FUNCTION IF EXISTS match_document_chunks(vector,double precision,integer,uuid);
DROP FUNCTION IF EXISTS match_document_chunks(vector,double precision,integer,uuid,uuid[]);

CREATE OR REPLACE FUNCTION match_document_chunks (
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  filter_user_id uuid,
  filter_file_ids uuid[] DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  file_id uuid,
  file_name text,
  user_id uuid,
  content text,
  chunk_index int,
  page_number int,
  section text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.file_id,
    uf.file_name,
    dc.user_id,
    dc.content,
    dc.chunk_index,
    dc.page_number,
    dc.section,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM document_chunks dc
  JOIN user_files uf ON dc.file_id = uf.id
  WHERE dc.user_id = filter_user_id
    AND (filter_file_ids IS NULL OR dc.file_id = ANY(filter_file_ids))
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
