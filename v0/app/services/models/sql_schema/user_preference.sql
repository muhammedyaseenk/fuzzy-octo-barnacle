
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