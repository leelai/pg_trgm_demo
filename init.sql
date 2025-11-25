-- Enable pg_trgm extension for trigram-based fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create worlds table to store book data
CREATE TABLE IF NOT EXISTS worlds (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

-- Indexes will be created by seed.py after data insertion
