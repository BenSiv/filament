-- FILAMENT Database Initialization
-- PostgreSQL with pgvector extension

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Unidentified Cases Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS unidentified_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number VARCHAR(50) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'BCCS',
    
    -- Discovery information
    discovery_date DATE,
    discovery_location_name VARCHAR(255),
    discovery_lat DOUBLE PRECISION,
    discovery_lon DOUBLE PRECISION,
    
    -- Physical description
    estimated_age_min INTEGER,
    estimated_age_max INTEGER,
    estimated_sex VARCHAR(20),
    height_cm_min INTEGER,
    height_cm_max INTEGER,
    weight_kg_min INTEGER,
    weight_kg_max INTEGER,
    
    -- Evidence flags
    dna_available BOOLEAN DEFAULT FALSE,
    dental_available BOOLEAN DEFAULT FALSE,
    
    -- Full text description
    description TEXT,
    
    -- Vector embedding for semantic search
    embedding vector(384),
    
    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- Missing Persons Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS missing_persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_number VARCHAR(50) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'NCMPUR',
    
    -- Personal information
    name VARCHAR(255),
    
    -- Last seen information
    last_seen_date DATE,
    last_seen_location_name VARCHAR(255),
    last_seen_lat DOUBLE PRECISION,
    last_seen_lon DOUBLE PRECISION,
    
    -- Physical description
    age_at_disappearance INTEGER,
    sex VARCHAR(20),
    height_cm INTEGER,
    weight_kg INTEGER,
    eye_color VARCHAR(50),
    hair_color VARCHAR(50),
    
    -- Distinguishing features
    distinguishing_features TEXT[],
    
    -- Full text description
    description TEXT,
    
    -- Vector embedding for semantic search
    embedding vector(384),
    
    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- Clothing Items Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS clothing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES unidentified_cases(id) ON DELETE CASCADE,
    missing_person_id UUID REFERENCES missing_persons(id) ON DELETE CASCADE,
    
    item_type VARCHAR(50) NOT NULL,
    brand VARCHAR(100),
    color VARCHAR(50),
    size VARCHAR(20),
    condition VARCHAR(100),
    description TEXT,
    
    -- Embedding for this item
    embedding vector(384),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure item belongs to either case or missing person
    CHECK (
        (case_id IS NOT NULL AND missing_person_id IS NULL) OR
        (case_id IS NULL AND missing_person_id IS NOT NULL)
    )
);

-- =============================================================================
-- Match Candidates Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS match_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unidentified_case_id UUID REFERENCES unidentified_cases(id) ON DELETE CASCADE,
    missing_person_id UUID REFERENCES missing_persons(id) ON DELETE CASCADE,
    
    -- Scoring
    overall_score DOUBLE PRECISION NOT NULL,
    vector_similarity DOUBLE PRECISION,
    graph_score DOUBLE PRECISION,
    bio_score DOUBLE PRECISION,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, reviewed, confirmed, rejected
    reviewer_notes TEXT,
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    
    UNIQUE(unidentified_case_id, missing_person_id)
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Vector similarity indexes
CREATE INDEX IF NOT EXISTS idx_unidentified_embedding 
ON unidentified_cases USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_missing_embedding 
ON missing_persons USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_clothing_embedding 
ON clothing USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- Geographic indexes (for proximity searches)
CREATE INDEX IF NOT EXISTS idx_unidentified_location 
ON unidentified_cases (discovery_lat, discovery_lon);

CREATE INDEX IF NOT EXISTS idx_missing_location 
ON missing_persons (last_seen_lat, last_seen_lon);

-- Date indexes
CREATE INDEX IF NOT EXISTS idx_unidentified_date ON unidentified_cases (discovery_date);
CREATE INDEX IF NOT EXISTS idx_missing_date ON missing_persons (last_seen_date);

-- =============================================================================
-- Initial Data (Test Records)
-- =============================================================================

-- Insert a test unidentified case
INSERT INTO unidentified_cases (case_number, source, discovery_date, discovery_location_name, discovery_lat, discovery_lon, estimated_age_min, estimated_age_max, estimated_sex, description)
VALUES 
    ('TEST-2024-001', 'BCCS', '2024-01-15', 'Hope, BC', 49.38, -121.44, 25, 35, 'Female', 'Test case for development purposes. Found with blue Nike shoes and hooded sweatshirt.')
ON CONFLICT (case_number) DO NOTHING;

-- Insert a test missing person
INSERT INTO missing_persons (file_number, source, name, last_seen_date, last_seen_location_name, last_seen_lat, last_seen_lon, age_at_disappearance, sex, description)
VALUES 
    ('TEST-MP-001', 'NCMPUR', 'Jane Test', '2023-06-15', 'Chilliwack, BC', 49.16, -121.95, 28, 'Female', 'Test missing person for development. Was wearing a bunnyhug and sneakers.')
ON CONFLICT (file_number) DO NOTHING;

-- Database initialization complete
SELECT 'FILAMENT database initialized successfully!' AS status;
