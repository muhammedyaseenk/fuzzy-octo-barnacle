DO $$ BEGIN
    CREATE TYPE profile_status_enum AS ENUM ('pending_profile', 'pending_admin', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_status profile_status_enum DEFAULT 'pending_profile';
CREATE INDEX IF NOT EXISTS idx_users_profile_status ON users(profile_status);
