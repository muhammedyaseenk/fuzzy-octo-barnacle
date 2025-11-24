-- Aurum Matrimony Database Schema
-- Run this SQL to create the required tables

-- Users table (extends the existing users table from identity domain)
-- The users table is already created by SQLAlchemy, but we need additional tables

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    marital_status VARCHAR(30),
    height INTEGER, -- in cm
    weight INTEGER, -- in kg
    complexion VARCHAR(20),
    body_type VARCHAR(20),
    blood_group VARCHAR(10),
    
    -- Location
    country VARCHAR(100),
    state VARCHAR(100),
    district VARCHAR(100),
    city VARCHAR(100),
    current_location VARCHAR(200),
    native_place VARCHAR(200),
    
    -- Religion
    religion VARCHAR(100),
    caste VARCHAR(100),
    sub_caste VARCHAR(100),
    mother_tongue VARCHAR(100),
    
    -- Lifestyle
    diet VARCHAR(20),
    smoking VARCHAR(20),
    drinking VARCHAR(20),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User education table
CREATE TABLE IF NOT EXISTS user_education (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    highest_education VARCHAR(200) NOT NULL,
    institution VARCHAR(200),
    year_of_completion INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User career table
CREATE TABLE IF NOT EXISTS user_career (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    occupation VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    designation VARCHAR(200),
    annual_income INTEGER,
    employment_type VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User family table
CREATE TABLE IF NOT EXISTS user_family (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    father_name VARCHAR(100),
    mother_name VARCHAR(100),
    family_type VARCHAR(20),
    family_status VARCHAR(30),
    siblings INTEGER,
    family_contact VARCHAR(15),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    min_age INTEGER NOT NULL,
    max_age INTEGER NOT NULL,
    min_height INTEGER NOT NULL, -- in cm
    max_height INTEGER NOT NULL, -- in cm
    preferred_religions TEXT[], -- Array of religions
    preferred_castes TEXT[], -- Array of castes
    min_income INTEGER,
    willing_to_relocate BOOLEAN DEFAULT true,
    expectations TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Admin verification queue
CREATE TABLE IF NOT EXISTS admin_verification_queue (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    admin_notes TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by INTEGER REFERENCES users(id)
);

-- User reports table
CREATE TABLE IF NOT EXISTS user_reports (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason VARCHAR(100) NOT NULL,
    details TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by INTEGER REFERENCES users(id)
);

-- User blocks table
CREATE TABLE IF NOT EXISTS user_blocks (
    id SERIAL PRIMARY KEY,
    blocker_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(blocker_id, blocked_user_id)
);

-- User shortlists table
CREATE TABLE IF NOT EXISTS user_shortlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shortlisted_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, shortlisted_user_id)
);

-- User interests/likes table (for future use)
CREATE TABLE IF NOT EXISTS user_interests (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    status VARCHAR(20) DEFAULT 'sent', -- sent, accepted, declined
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(sender_id, receiver_id)
);

-- User images table
CREATE TABLE IF NOT EXISTS user_images (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_id VARCHAR(100) NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, image_id)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user1_id, user2_id)
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_gender ON user_profiles(gender);
CREATE INDEX IF NOT EXISTS idx_user_profiles_marital_status ON user_profiles(marital_status);
CREATE INDEX IF NOT EXISTS idx_user_profiles_location ON user_profiles(country, state, district, city);
CREATE INDEX IF NOT EXISTS idx_user_profiles_religion ON user_profiles(religion, caste);
CREATE INDEX IF NOT EXISTS idx_user_career_occupation ON user_career(occupation);
CREATE INDEX IF NOT EXISTS idx_user_career_income ON user_career(annual_income);
CREATE INDEX IF NOT EXISTS idx_verification_queue_status ON admin_verification_queue(status);
CREATE INDEX IF NOT EXISTS idx_verification_queue_submitted ON admin_verification_queue(submitted_at);
CREATE INDEX IF NOT EXISTS idx_user_reports_status ON user_reports(status);
CREATE INDEX IF NOT EXISTS idx_user_reports_reported_user ON user_reports(reported_user_id);
CREATE INDEX IF NOT EXISTS idx_user_reports_created ON user_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_user_blocks_blocker ON user_blocks(blocker_id);
CREATE INDEX IF NOT EXISTS idx_user_blocks_blocked ON user_blocks(blocked_user_id);
CREATE INDEX IF NOT EXISTS idx_user_shortlists_user ON user_shortlists(user_id);
CREATE INDEX IF NOT EXISTS idx_user_shortlists_shortlisted ON user_shortlists(shortlisted_user_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_sender ON user_interests(sender_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_receiver ON user_interests(receiver_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_status ON user_interests(status);
CREATE INDEX IF NOT EXISTS idx_user_images_user ON user_images(user_id);
CREATE INDEX IF NOT EXISTS idx_user_images_primary ON user_images(user_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_conversations_users ON conversations(user1_id, user2_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_unread ON messages(conversation_id, is_read);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- Add some constraints
ALTER TABLE user_profiles ADD CONSTRAINT check_height CHECK (height > 0 AND height < 300);
ALTER TABLE user_profiles ADD CONSTRAINT check_weight CHECK (weight > 0 AND weight < 500);
ALTER TABLE user_preferences ADD CONSTRAINT check_age_range CHECK (min_age <= max_age);
ALTER TABLE user_preferences ADD CONSTRAINT check_height_range CHECK (min_height <= max_height);

-- Moderation constraints
ALTER TABLE user_reports ADD CONSTRAINT check_not_self_report CHECK (reporter_id != reported_user_id);
ALTER TABLE user_blocks ADD CONSTRAINT check_not_self_block CHECK (blocker_id != blocked_user_id);

-- Matching constraints
ALTER TABLE user_shortlists ADD CONSTRAINT check_not_self_shortlist CHECK (user_id != shortlisted_user_id);
ALTER TABLE user_interests ADD CONSTRAINT check_not_self_interest CHECK (sender_id != receiver_id);