-- V7__Add_profile_status_to_users.sql
-- Add profile_status column and enum type to users table

-- Create ENUM type for profile status
DO $$ BEGIN
    CREATE TYPE profile_status_enum AS ENUM ('pending_profile', 'pending_admin', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add profile_status column to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS profile_status profile_status_enum DEFAULT 'pending_profile';

-- Add index on profile_status for faster filtering
CREATE INDEX IF NOT EXISTS idx_users_profile_status ON users(profile_status);
