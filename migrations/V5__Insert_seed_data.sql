-- V5__Insert_seed_data.sql
-- Seed data for initial setup

-- Create admin user
INSERT INTO users (
    phone, email, hashed_password, role, is_active, admin_approved, is_verified
) VALUES (
    '+919999999999', 
    'admin@aurum.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uDjS', -- password: admin123
    'admin', 
    true, 
    true, 
    true
) ON CONFLICT (phone) DO NOTHING;

-- Create admin profile
INSERT INTO user_profiles (
    user_id, first_name, last_name, verification_status, profile_complete
) SELECT 
    id, 'Admin', 'User', 'approved', true
FROM users 
WHERE phone = '+919999999999'
ON CONFLICT (user_id) DO NOTHING;