-- =====================================================
-- AURUM MATRIMONY - WORLD-CLASS DATABASE SCHEMA
-- Complete End-to-End Matrimony Platform for Kerala & India
-- =====================================================

-- =====================================================
-- 1️⃣ CORE USER MANAGEMENT
-- =====================================================

-- Users Authentication Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email CITEXT UNIQUE NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0
);

-- User Profiles - Core Information
CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Basic Details
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    date_of_birth DATE NOT NULL,
    age SMALLINT GENERATED ALWAYS AS (DATE_PART('year', AGE(date_of_birth))) STORED,
    gender VARCHAR(10) NOT NULL CHECK (gender IN ('Male', 'Female')),
    marital_status VARCHAR(20) NOT NULL CHECK (marital_status IN ('Never Married', 'Divorced', 'Widowed', 'Separated')),
    
    -- Physical Attributes
    height_cm SMALLINT NOT NULL,
    weight_kg SMALLINT,
    complexion VARCHAR(20) CHECK (complexion IN ('Fair', 'Wheatish', 'Dark', 'Very Fair')),
    body_type VARCHAR(20) CHECK (body_type IN ('Slim', 'Average', 'Athletic', 'Heavy')),
    blood_group VARCHAR(5),
    
    -- Location
    country_id INTEGER NOT NULL,
    state_id INTEGER NOT NULL,
    district_id INTEGER,
    city_id INTEGER,
    current_location VARCHAR(255),
    native_place VARCHAR(255),
    
    -- Religion & Community
    religion_id INTEGER NOT NULL,
    caste_id INTEGER,
    sub_caste VARCHAR(100),
    mother_tongue_id INTEGER NOT NULL,
    
    -- Lifestyle
    diet VARCHAR(20) CHECK (diet IN ('Vegetarian', 'Non-Vegetarian', 'Vegan', 'Jain Vegetarian')),
    smoking VARCHAR(20) CHECK (smoking IN ('Never', 'Occasionally', 'Regularly', 'Trying to Quit')),
    drinking VARCHAR(20) CHECK (drinking IN ('Never', 'Occasionally', 'Socially', 'Regularly')),
    
    -- Profile Status
    profile_completion_percentage SMALLINT DEFAULT 0,
    profile_verified BOOLEAN DEFAULT FALSE,
    premium_member BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 2️⃣ MASTER DATA TABLES
-- =====================================================

-- Countries, States, Districts, Cities
CREATE TABLE countries (
    country_id SERIAL PRIMARY KEY,
    country_name VARCHAR(100) UNIQUE NOT NULL,
    country_code VARCHAR(3) UNIQUE NOT NULL,
    phone_code VARCHAR(5)
);

CREATE TABLE states (
    state_id SERIAL PRIMARY KEY,
    country_id INTEGER REFERENCES countries(country_id),
    state_name VARCHAR(100) NOT NULL,
    state_code VARCHAR(10)
);

CREATE TABLE districts (
    district_id SERIAL PRIMARY KEY,
    state_id INTEGER REFERENCES states(state_id),
    district_name VARCHAR(100) NOT NULL
);

CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    district_id INTEGER REFERENCES districts(district_id),
    city_name VARCHAR(100) NOT NULL,
    is_metro BOOLEAN DEFAULT FALSE
);

-- Religions, Castes, Languages
CREATE TABLE religions (
    religion_id SERIAL PRIMARY KEY,
    religion_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE castes (
    caste_id SERIAL PRIMARY KEY,
    religion_id INTEGER REFERENCES religions(religion_id),
    caste_name VARCHAR(100) NOT NULL,
    caste_category VARCHAR(20)
);

CREATE TABLE mother_tongues (
    mother_tongue_id SERIAL PRIMARY KEY,
    language_name VARCHAR(50) UNIQUE NOT NULL,
    language_code VARCHAR(5)
);

-- =====================================================
-- 3️⃣ EDUCATION & CAREER
-- =====================================================

CREATE TABLE user_education (
    education_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    degree_level VARCHAR(50) NOT NULL,
    degree_name VARCHAR(200) NOT NULL,
    specialization VARCHAR(200),
    university VARCHAR(200),
    graduation_year SMALLINT,
    is_highest BOOLEAN DEFAULT FALSE
);

CREATE TABLE user_career (
    career_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    occupation VARCHAR(200) NOT NULL,
    company_name VARCHAR(200),
    designation VARCHAR(200),
    annual_income BIGINT,
    employment_type VARCHAR(20),
    is_current BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- 4️⃣ FAMILY & PREFERENCES
-- =====================================================

CREATE TABLE user_family (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    father_name VARCHAR(200),
    mother_name VARCHAR(200),
    family_type VARCHAR(20),
    family_status VARCHAR(20),
    total_siblings SMALLINT DEFAULT 0,
    family_contact_person VARCHAR(200),
    family_contact_phone VARCHAR(15)
);

CREATE TABLE user_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    preferred_age_min SMALLINT NOT NULL,
    preferred_age_max SMALLINT NOT NULL,
    preferred_height_min SMALLINT,
    preferred_height_max SMALLINT,
    preferred_religions INTEGER[],
    preferred_castes INTEGER[],
    preferred_income_min BIGINT,
    willing_to_relocate BOOLEAN DEFAULT TRUE,
    partner_expectations TEXT
);


CREATE TABLES special_expectations ( -- for  partner expectations include is must from the same career, family background, working abroad, specific career , status etc.
    expectation_id BIGSERIAL PRIMARY KEY, -- this must be linked to user_preferences
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    expectation_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL
);
-- =====================================================
-- 5️⃣ INTERACTIONS & MATCHING
-- =====================================================

CREATE TABLE profile_visits (
    visit_id BIGSERIAL PRIMARY KEY,
    visitor_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    visited_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    visited_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(visitor_id, visited_id, DATE(visited_at))
);

CREATE TABLE express_interest (
    interest_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'Pending',
    sent_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sender_id, receiver_id)
);

CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE match_scores (
    match_id BIGSERIAL PRIMARY KEY,
    user1_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    user2_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    compatibility_score DECIMAL(5,2) NOT NULL,
    score_factors JSONB,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user1_id, user2_id)
);

-- =====================================================
-- 6️⃣ SUBSCRIPTION & PAYMENTS
-- =====================================================

CREATE TABLE subscription_plans (
    plan_id SERIAL PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL,
    plan_type VARCHAR(20),
    duration_months SMALLINT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    features JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE user_subscriptions (
    subscription_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES subscription_plans(plan_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Active',
    amount_paid DECIMAL(10,2)
);

-- =====================================================
-- 7️⃣ PRIVACY & SAFETY
-- =====================================================

CREATE TABLE user_privacy (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    profile_visible_to VARCHAR(20) DEFAULT 'All',
    photos_visible_to VARCHAR(20) DEFAULT 'All',
    allow_messages BOOLEAN DEFAULT TRUE,
    appear_in_search BOOLEAN DEFAULT TRUE
);

CREATE TABLE blocked_users (
    block_id BIGSERIAL PRIMARY KEY,
    blocker_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    blocked_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    blocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(blocker_id, blocked_id)
);

-- =====================================================
-- 8️⃣ KERALA-SPECIFIC TABLES
-- =====================================================

CREATE TABLE kerala_districts (
    district_id SERIAL PRIMARY KEY,
    district_name VARCHAR(50) UNIQUE NOT NULL,
    headquarters VARCHAR(50)
);

CREATE TABLE kerala_hindu_castes (
    caste_id SERIAL PRIMARY KEY,
    caste_name VARCHAR(100) UNIQUE NOT NULL,
    caste_category VARCHAR(20),
    gothra_applicable BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- 9️⃣ PERFORMANCE INDEXES
-- =====================================================

CREATE INDEX idx_user_profiles_age ON user_profiles(age);
CREATE INDEX idx_user_profiles_location ON user_profiles(state_id, district_id);
CREATE INDEX idx_user_profiles_religion_caste ON user_profiles(religion_id, caste_id);
CREATE INDEX idx_user_career_income ON user_career(annual_income);
CREATE INDEX idx_match_scores_compatibility ON match_scores(user1_id, compatibility_score DESC);
CREATE INDEX idx_profile_visits_visited ON profile_visits(visited_id, visited_at);
