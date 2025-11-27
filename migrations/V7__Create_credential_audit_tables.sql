-- V7__Create_credential_audit_tables.sql
-- Credential management for admin export and tracking

CREATE TABLE credential_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Export details
    export_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_method VARCHAR(50) DEFAULT 'whatsapp' NOT NULL,  -- whatsapp, email, manual
    export_file_hash VARCHAR(256),
    
    -- Delivery tracking
    marked_delivered BOOLEAN DEFAULT FALSE,
    delivery_timestamp TIMESTAMP,
    delivery_note VARCHAR(500),
    
    -- IP tracking for security
    admin_ip_address VARCHAR(45),
    admin_user_agent VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for credential audit
CREATE INDEX idx_credential_audit_user_timestamp ON credential_audit(user_id, export_timestamp DESC);
CREATE INDEX idx_credential_audit_admin_timestamp ON credential_audit(admin_id, export_timestamp DESC);
CREATE INDEX idx_credential_audit_delivery ON credential_audit(marked_delivered);

-- Create credential exports table
CREATE TABLE credential_exports (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL UNIQUE REFERENCES credential_audit(id) ON DELETE CASCADE,
    
    -- Encrypted credentials (phone + password)
    encrypted_phone VARCHAR(255) NOT NULL,
    encrypted_password VARCHAR(255) NOT NULL,
    
    -- Export format
    export_format VARCHAR(20) DEFAULT 'json' NOT NULL,
    
    -- Access control
    download_token VARCHAR(256) UNIQUE,
    downloaded BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    CONSTRAINT credentials_not_expired CHECK (expires_at > created_at)
);

-- Indexes for credential exports
CREATE INDEX idx_credential_export_audit ON credential_exports(audit_id);
CREATE INDEX idx_credential_export_token ON credential_exports(download_token);
CREATE INDEX idx_credential_export_expires ON credential_exports(expires_at DESC);

-- Add comment for documentation
COMMENT ON TABLE credential_audit IS 'Audit log for credential exports - tracks who exported credentials and how they were delivered';
COMMENT ON TABLE credential_exports IS 'Temporary storage for encrypted exported credentials - automatically expires after 24 hours';
COMMENT ON COLUMN credential_audit.delivery_method IS 'How credentials are delivered to user (whatsapp, email, manual)';
COMMENT ON COLUMN credential_audit.marked_delivered IS 'Admin confirms credentials have been delivered to user';
COMMENT ON COLUMN credential_exports.download_token IS 'One-time use token for downloading credentials - expires after 24 hours or 3 downloads';
