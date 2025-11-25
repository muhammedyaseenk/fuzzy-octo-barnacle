-- V1__Create_base_tables.sql
-- Base tables that don't depend on others

-- Users table (base identity)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    whatsapp VARCHAR(15),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    admin_approved BOOLEAN DEFAULT false,
    role VARCHAR(20) DEFAULT 'user',
    mfa_secret VARCHAR(32),
    mfa_enabled BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Audit logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Base indexes
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);