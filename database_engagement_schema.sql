-- database_engagement_schema.sql
-- Engagement and rule engine tables

-- Engagement events tracking
CREATE TABLE IF NOT EXISTS engagement_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    metadata TEXT,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_engagement_events_user ON engagement_events(user_id, created_at DESC);
CREATE INDEX idx_engagement_events_type ON engagement_events(event_type, processed);
CREATE INDEX idx_engagement_events_processed ON engagement_events(processed) WHERE processed = FALSE;

-- Contact approval workflow
CREATE TABLE IF NOT EXISTS contact_approvals (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_contact_approvals_requester ON contact_approvals(requester_id, target_id);
CREATE INDEX idx_contact_approvals_status ON contact_approvals(status) WHERE status = 'pending';
CREATE UNIQUE INDEX idx_contact_approvals_unique ON contact_approvals(requester_id, target_id);

-- User engagement scoring
CREATE TABLE IF NOT EXISTS user_engagement_scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_views INTEGER DEFAULT 0,
    interests_sent INTEGER DEFAULT 0,
    interests_received INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    response_rate INTEGER DEFAULT 0 CHECK (response_rate >= 0 AND response_rate <= 100),
    last_active TIMESTAMP WITH TIME ZONE,
    engagement_score INTEGER DEFAULT 0 CHECK (engagement_score >= 0 AND engagement_score <= 100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_engagement_scores_score ON user_engagement_scores(engagement_score DESC);
CREATE INDEX idx_engagement_scores_active ON user_engagement_scores(last_active DESC);

-- Add subscription fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'premium', 'elite'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_users_subscription ON users(subscription_tier, subscription_expires);

-- Function to update engagement score
CREATE OR REPLACE FUNCTION update_engagement_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.engagement_score := LEAST(
        (NEW.profile_views * 2) +
        (NEW.interests_sent * 5) +
        (NEW.interests_received * 5) +
        (NEW.messages_sent * 3) +
        (NEW.messages_received * 3) +
        (NEW.response_rate / 10),
        100
    );
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_engagement_score
BEFORE UPDATE ON user_engagement_scores
FOR EACH ROW
EXECUTE FUNCTION update_engagement_score();

-- Views for analytics
CREATE OR REPLACE VIEW v_user_tier_stats AS
SELECT 
    subscription_tier,
    COUNT(*) as user_count,
    AVG(ues.engagement_score) as avg_engagement,
    COUNT(*) FILTER (WHERE ues.last_active >= NOW() - INTERVAL '7 days') as active_users
FROM users u
LEFT JOIN user_engagement_scores ues ON u.id = ues.user_id
GROUP BY subscription_tier;

CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT 
    ca.id,
    ca.requester_id,
    ca.target_id,
    ca.created_at,
    p1.first_name as requester_name,
    p2.first_name as target_name,
    EXTRACT(EPOCH FROM (NOW() - ca.created_at))/3600 as hours_pending
FROM contact_approvals ca
JOIN profiles p1 ON ca.requester_id = p1.user_id
JOIN profiles p2 ON ca.target_id = p2.user_id
WHERE ca.status = 'pending'
ORDER BY ca.created_at ASC;

-- Sample data for testing
INSERT INTO user_engagement_scores (user_id, profile_views, interests_sent, interests_received, messages_sent, messages_received, response_rate, last_active)
SELECT 
    id,
    FLOOR(RANDOM() * 50)::INTEGER,
    FLOOR(RANDOM() * 20)::INTEGER,
    FLOOR(RANDOM() * 20)::INTEGER,
    FLOOR(RANDOM() * 30)::INTEGER,
    FLOOR(RANDOM() * 30)::INTEGER,
    FLOOR(RANDOM() * 100)::INTEGER,
    NOW() - (RANDOM() * INTERVAL '30 days')
FROM users
WHERE id NOT IN (SELECT user_id FROM user_engagement_scores)
ON CONFLICT (user_id) DO NOTHING;

ANALYZE engagement_events;
ANALYZE contact_approvals;
ANALYZE user_engagement_scores;
