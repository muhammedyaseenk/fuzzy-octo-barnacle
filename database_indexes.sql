-- database_indexes.sql
-- Critical indexes for fast scrolling and query performance

-- Profile scrolling indexes (cursor-based pagination)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_created_at_id 
ON profiles(created_at DESC, id DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_verification_gender 
ON profiles(verification_status, gender) 
WHERE verification_status = 'approved';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_age_lookup 
ON profiles(date_of_birth) 
WHERE verification_status = 'approved';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_religion 
ON profiles(religion, verification_status) 
WHERE verification_status = 'approved';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_location 
ON profiles(city, state, country);

-- Matching indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shortlist_user_created 
ON user_shortlists(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shortlist_target 
ON user_shortlists(target_user_id);

-- Chat indexes for fast message loading
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_conversation_time 
ON messages(conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_participants 
ON conversations(user1_id, user2_id);

-- Notification indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, is_read, created_at DESC) 
WHERE is_read = false;

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_search_composite 
ON profiles(verification_status, gender, religion, city) 
WHERE verification_status = 'approved';

-- Partial indexes for active users
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active 
ON users(id, last_login_at) 
WHERE is_active = true;

-- BRIN indexes for time-series data (memory efficient)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_created_brin 
ON audit_logs USING BRIN(created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_created_brin 
ON user_sessions USING BRIN(created_at);

-- Statistics update for query planner
ANALYZE profiles;
ANALYZE user_shortlists;
ANALYZE messages;
ANALYZE conversations;
ANALYZE notifications;
