
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

CREATE TABLE report_reasons (
    reason_id SERIAL PRIMARY KEY,
    reason_text VARCHAR(255) NOT NULL
);

CREATE TABLE user_reports (
    report_id BIGSERIAL PRIMARY KEY,
    reporter_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    reported_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    reason_id INT REFERENCES report_reasons(reason_id),
    report_details TEXT,
    reported_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_reported_id ON user_reports(reported_id);
CREATE INDEX idx_reporter_id ON user_reports(reporter_id);
CREATE INDEX idx_reason_id ON user_reports(reason_id);
CREATE INDEX idx_reported_at ON user_reports(reported_at);
CREATE INDEX idx_blocker_id ON blocked_users(blocker_id);
CREATE INDEX idx_blocked_id ON blocked_users(blocked_id);
CREATE INDEX idx_user_privacy_profile_visible ON user_privacy(profile_visible_to);
CREATE INDEX idx_user_privacy_photos_visible ON user_privacy(photos_visible_to);
CREATE INDEX idx_user_privacy_allow_messages ON user_privacy(allow_messages);
CREATE INDEX idx_user_privacy_appear_in_search ON user_privacy(appear_in_search);
-- =====================================================