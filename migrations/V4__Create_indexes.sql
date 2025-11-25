-- V4__Create_indexes.sql
-- Performance indexes

-- User profiles indexes
CREATE INDEX idx_user_profiles_user ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_gender ON user_profiles(gender);
CREATE INDEX idx_user_profiles_location ON user_profiles(country, state, city);
CREATE INDEX idx_user_profiles_religion ON user_profiles(religion, caste);
CREATE INDEX idx_user_profiles_verification ON user_profiles(verification_status);

-- Engagement indexes
CREATE INDEX idx_engagement_events_user ON engagement_events(user_id);
CREATE INDEX idx_engagement_events_type ON engagement_events(event_type);
CREATE INDEX idx_engagement_events_processed ON engagement_events(processed);
CREATE INDEX idx_contact_approvals_requester ON contact_approvals(requester_id);
CREATE INDEX idx_contact_approvals_target ON contact_approvals(target_id);
CREATE INDEX idx_contact_approvals_status ON contact_approvals(status);

-- Communication indexes
CREATE INDEX idx_conversations_users ON conversations(user1_id, user2_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_unread ON messages(conversation_id, is_read);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_type ON notifications(type);

-- Session indexes
CREATE INDEX idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

-- Shortlist indexes
CREATE INDEX idx_user_shortlists_user ON user_shortlists(user_id);
CREATE INDEX idx_user_shortlists_shortlisted ON user_shortlists(shortlisted_user_id);