-- =================================
-- Kerala Matrimony Platform Schema
-- Supports Hindu, Muslim, Christian Users
-- =================================

-- =================================
-- 1️⃣ Users Table
-- =================================
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =================================
-- 2️⃣ User Profile Table
-- =================================
CREATE TABLE user_profile (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),

    -- Basic Info
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    gender VARCHAR(20),
    date_of_birth DATE,
    age SMALLINT GENERATED ALWAYS AS (DATE_PART('year', AGE(date_of_birth))) STORED,
    marital_status VARCHAR(50),
    no_of_children SMALLINT DEFAULT 0,
    first_married_status BOOLEAN DEFAULT FALSE,

    -- Religion / Community
    religion VARCHAR(50), -- Hindu, Muslim, Christian
    caste VARCHAR(100),
    sub_caste VARCHAR(100),
    community_group VARCHAR(100),
    religious_views VARCHAR(100),

    -- Location
    native_place VARCHAR(100),
    nationality VARCHAR(100),
    state VARCHAR(100),
    district VARCHAR(100),
    city VARCHAR(100),
    present_location VARCHAR(255),
    future_location VARCHAR(255),
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),

    -- Physical Attributes
    height_cm SMALLINT,
    weight_kg SMALLINT,
    complexion VARCHAR(50),
    body_type VARCHAR(50),
    disability_status VARCHAR(100),
    blood_group VARCHAR(10),
    special_conditions TEXT,

    -- Education & Career
    education VARCHAR(255),
    education_level VARCHAR(50),
    occupation VARCHAR(255),
    job_role VARCHAR(255),
    annual_income BIGINT,
    employer VARCHAR(255),
    work_location VARCHAR(255),
    work_type VARCHAR(50),
    work_experience_years INT,
    employment_status VARCHAR(50),

    -- Lifestyle
    diet VARCHAR(50),
    drinking VARCHAR(50),
    smoking VARCHAR(50),
    pets_preference VARCHAR(50),
    hobbies TEXT,
    interests TEXT,
    fitness_activities TEXT,
    allowed_to_do_fitness_activities_at_home BOOLEAN DEFAULT TRUE,
    allowed_to_do_fitness_activities_outside BOOLEAN DEFAULT TRUE,
    are_you_love_to_do_follow_cricketss_or_football BOOLEAN DEFAULT TRUE,
    favorite_sports TEXT,
    loving_in_metrocities BOOLEAN DEFAULT TRUE,
    partener_should_be_fit BOOLEAN DEFAULT TRUE,
    partners_should_enjoy_fitness_activities BOOLEAN DEFAULT TRUE,
    partner_is_at_distance_no_issue BOOLEAN DEFAULT TRUE,
    willing_to_relocate BOOLEAN DEFAULT TRUE,
    love_to_help_partner BOOLEAN DEFAULT TRUE,
    love_to_help_partner_in_family BOOLEAN DEFAULT TRUE,
    love_to_help_partner_in_friends BOOLEAN DEFAULT TRUE,
    love_to_help_partner_in_neighbours BOOLEAN DEFAULT TRUE,
    love_to_help_partner_in_other BOOLEAN DEFAULT TRUE,
    love_to_help_partner_in_other_details TEXT,
    love_to_help_partner_in_other_details BOOLEAN DEFAULT TRUE,



    -- Family Background
    family_type VARCHAR(50),
    family_status VARCHAR(100),
    family_values VARCHAR(100),
    father_name VARCHAR(255),
    mother_name VARCHAR(255),
    father_occupation VARCHAR(255),
    mother_occupation VARCHAR(255),
    father_alive BOOLEAN,
    mother_alive BOOLEAN,
    guardian_name VARCHAR(255),
    guardian_contact VARCHAR(20),
    guardian_contact_relation VARCHAR(100),
    guardian_contact_whatsapp BOOLEAN DEFAULT FALSE,
    guardian_contact_whatsapp_number VARCHAR(20),
    number_of_siblings SMALLINT,
    brothers SMALLINT,
    sisters SMALLINT,
    married_brothers SMALLINT,
    married_sisters SMALLINT,
    unmarried_brothers SMALLINT,
    unmarried_sisters SMALLINT,

    -- Personal Details
    about TEXT,
    languages_spoken TEXT,
    languages_known TEXT,
    social_media_links JSONB,
    profile_picture_url TEXT,

    -- Residency / Immigration
    citizenship VARCHAR(100),
    residing_country VARCHAR(100),
    visa_status VARCHAR(100),
    passport_type VARCHAR(100),

    -- Partner Expectations
    partner_expectation TEXT,
    preferred_family_type VARCHAR(50),
    preferred_occupation TEXT,
    preferred_location TEXT,
    future_education_plans TEXT,
    future_occupation_plans TEXT,
    annual_income_expectation BIGINT,

    -- Verification
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    id_proof_verified BOOLEAN DEFAULT FALSE,
    profile_verified BOOLEAN DEFAULT FALSE,

    -- Engagement
    profile_completion_score SMALLINT DEFAULT 0,
    profile_strength VARCHAR(50),

    -- Hindu Specific
    gotra VARCHAR(100),
    gothram_verified BOOLEAN DEFAULT FALSE,
    kulam VARCHAR(100),
    sect VARCHAR(100),
    sub_sect VARCHAR(100),
    caste_category VARCHAR(50),
    temple_visiting_frequency VARCHAR(100),
    daily_puja_habits VARCHAR(255),
    vratha_habits VARCHAR(255),
    religious_belief_level VARCHAR(100),
    performs_rituals BOOLEAN DEFAULT FALSE,
    performs_pitru_karma BOOLEAN DEFAULT FALSE,
    festival_participation TEXT,
    rasi VARCHAR(50),
    nakshatra VARCHAR(50),
    dosham_present BOOLEAN DEFAULT FALSE,
    dosham_details JSONB,
    horoscope_match_required BOOLEAN DEFAULT FALSE,
    horoscope_matched BOOLEAN DEFAULT FALSE,
    horoscope_details JSONB,

    -- Muslim Specific
    allowed_to_verify_details_from_mahallu BOOLEAN DEFAULT TRUE,
    prayer_frequency VARCHAR(50), -- e.g., Five times a day
    halaal_preference BOOLEAN,
    religious_leader_advised BOOLEAN, -- as per diamonds
    sect_muslim VARCHAR(100), -- Sunni, Shia, etc.
    mosque_name VARCHAR(255),
    mosque_attendance_frequency VARCHAR(50),
    quran_recitation_level VARCHAR(100),
    quran_recitation_fequency VARCHAR(50),
    strict_observer_of_religious_duties BOOLEAN DEFAULT FALSE,
    religious_duties TEXT,
    religious_duties_frequency VARCHAR(50),
    sunna_practices BOOLEAN DEFAULT TRUE,
    hijab_wearing_habits VARCHAR(100),
    support_hijab_wearing BOOLEAN DEFAULT TRUE,
    madrasah_education BOOLEAN DEFAULT FALSE,
    madrasah_classes_attended BIGINT,
    support_qudbah_attendance BOOLEAN DEFAULT TRUE,
    willing_to_go_to_mosque_regularly BOOLEAN DEFAULT TRUE,
    wiling_to_allow_mosque_visits BOOLEAN DEFAULT TRUE,






    -- Christian Specific
    denomination VARCHAR(100), -- Catholic, Protestant, Orthodox
    church_name VARCHAR(255),
    church_attendance_frequency VARCHAR(50)
    
);

-- =================================
-- 3️⃣ Indexes
-- =================================
CREATE INDEX idx_user_profile_religion ON user_profile(religion);
CREATE INDEX idx_user_profile_location ON user_profile(state, district, city);
CREATE INDEX idx_user_profile_education ON user_profile(education_level, education);
CREATE INDEX idx_user_profile_occupation ON user_profile(occupation);
CREATE INDEX idx_user_profile_caste ON user_profile(caste, sub_caste);
CREATE INDEX idx_user_profile_height ON user_profile(height_cm);
CREATE INDEX idx_user_profile_income ON user_profile(annual_income);

-- =================================
-- 4️⃣ Hindu Master Tables
-- =================================
CREATE TABLE hindu_caste_master (
    caste_id BIGSERIAL PRIMARY KEY,
    caste_name VARCHAR(150) UNIQUE NOT NULL,
    varna VARCHAR(50),
    description TEXT
);
CREATE TABLE hindu_subcaste_master (
    subcaste_id BIGSERIAL PRIMARY KEY,
    caste_id BIGINT REFERENCES hindu_caste_master(caste_id) ON DELETE CASCADE,
    subcaste_name VARCHAR(150) NOT NULL,
    description TEXT
);
CREATE TABLE hindu_gotra_master (
    gotra_id BIGSERIAL PRIMARY KEY,
    subcaste_id BIGINT REFERENCES hindu_subcaste_master(subcaste_id) ON DELETE SET NULL,
    gotra_name VARCHAR(150) NOT NULL,
    description TEXT
);
CREATE TABLE hindu_sect_master (
    sect_id BIGSERIAL PRIMARY KEY,
    sect_name VARCHAR(150) UNIQUE NOT NULL,
    philosophy VARCHAR(150),
    deity_preference VARCHAR(150),
    description TEXT
);
CREATE TABLE hindu_rasi_master (
    rasi_id BIGSERIAL PRIMARY KEY,
    rasi_name VARCHAR(50) UNIQUE NOT NULL,
    element VARCHAR(50),
    lord VARCHAR(100)
);
CREATE TABLE hindu_nakshatra_master (
    nakshatra_id BIGSERIAL PRIMARY KEY,
    nakshatra_name VARCHAR(100) UNIQUE NOT NULL,
    rasi_id BIGINT REFERENCES hindu_rasi_master(rasi_id),
    padam_count SMALLINT DEFAULT 4,
    deity VARCHAR(100),
    planet VARCHAR(100)
);
CREATE TABLE hindu_dosham_master (
    dosham_id BIGSERIAL PRIMARY KEY,
    dosham_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);
CREATE TABLE user_hindu_dosham (
    user_id BIGINT PRIMARY KEY REFERENCES user_profile(user_id),
    dosham_details JSONB
);
CREATE TABLE user_hindu_festival_participation (
    user_id BIGINT PRIMARY KEY REFERENCES user_profile(user_id),
    festivals JSONB
);

-- =================================
-- 5️⃣ Muslim Master Tables
-- =================================
CREATE TABLE muslim_sect_master (
    sect_id BIGSERIAL PRIMARY KEY,
    sect_name VARCHAR(150) UNIQUE NOT NULL,
    description TEXT
);
CREATE TABLE muslim_prayer_master (
    prayer_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- =================================
-- 6️⃣ Christian Master Tables
-- =================================
CREATE TABLE christian_denomination_master (
    denomination_id BIGSERIAL PRIMARY KEY,
    denomination_name VARCHAR(150) UNIQUE NOT NULL,
    description TEXT
);
CREATE TABLE christian_church_master (
    church_id BIGSERIAL PRIMARY KEY,
    church_name VARCHAR(255) UNIQUE NOT NULL,
    denomination_id BIGINT REFERENCES christian_denomination_master(denomination_id)
);

-- =================================
-- 7️⃣ Optional Horoscope / Compatibility
-- =================================
CREATE TABLE hindu_horoscope_compatibility_rules (
    rule_id BIGSERIAL PRIMARY KEY,
    rasi_id BIGINT REFERENCES hindu_rasi_master(rasi_id),
    nakshatra_id BIGINT REFERENCES hindu_nakshatra_master(nakshatra_id),
    compatible_rasi_ids BIGINT[],
    compatible_nakshatra_ids BIGINT[],
    notes TEXT
);

-- =================================
-- 8️⃣ Alter User Profile for Foreign Keys
-- =================================
ALTER TABLE user_profile
ADD COLUMN caste_id BIGINT REFERENCES hindu_caste_master(caste_id),
ADD COLUMN subcaste_id BIGINT REFERENCES hindu_subcaste_master(subcaste_id),
ADD COLUMN gotra_id BIGINT REFERENCES hindu_gotra_master(gotra_id),
ADD COLUMN sect_id BIGINT REFERENCES hindu_sect_master(sect_id),
ADD COLUMN rasi_id BIGINT REFERENCES hindu_rasi_master(rasi_id),
ADD COLUMN nakshatra_id BIGINT REFERENCES hindu_nakshatra_master(nakshatra_id),
ADD COLUMN dosham_id BIGINT REFERENCES hindu_dosham_master(dosham_id);

-- =================================
-- End of Kerala Matrimony Platform Schema