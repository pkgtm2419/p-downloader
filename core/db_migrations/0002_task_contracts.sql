-- Migration 0002: Add task contracts and metadata
ALTER TABLE downloads ADD COLUMN kind TEXT DEFAULT 'direct';
ALTER TABLE downloads ADD COLUMN headers_json TEXT;
ALTER TABLE downloads ADD COLUMN page_url TEXT;
ALTER TABLE downloads ADD COLUMN context_blob BLOB;
ALTER TABLE downloads ADD COLUMN route_reason TEXT;
ALTER TABLE downloads ADD COLUMN expected_checksum TEXT;

UPDATE downloads SET kind = 'hls' WHERE lower(url) LIKE '%.m3u8%';
UPDATE downloads SET kind = 'extractor' WHERE kind = 'direct' AND (url LIKE '%youtube.com%' OR url LIKE '%youtu.be%');
