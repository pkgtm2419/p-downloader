-- Migration 0001: Initial P-Downloader schema
CREATE TABLE IF NOT EXISTS downloads (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    filename TEXT NOT NULL,
    save_path TEXT NOT NULL,
    total_bytes INTEGER DEFAULT 0,
    downloaded_bytes INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    category TEXT DEFAULT 'General',
    connections INTEGER DEFAULT 8,
    supports_range INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transfer_journals (
    task_id TEXT PRIMARY KEY,
    staging_path TEXT NOT NULL,
    journal_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
