| Table              | Description                     | Key Fields                                                                                            |
| ------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `profile_visits`   | Track who visited whose profile | `visit_id(PK)`, `visitor_user_id(FK)`, `visited_user_id(FK)`, `visited_at`                            |
| `express_interest` | Likes or “interests” sent       | `interest_id(PK)`, `sender_id(FK)`, `receiver_id(FK)`, `status(pending/accepted/rejected)`, `sent_at` |
| `messages`         | Chat between users              | `message_id(PK)`, `sender_id(FK)`, `receiver_id(FK)`, `message_text`, `sent_at`, `is_read`            |
| `blocked_users`    | Users blocked by others         | `block_id(PK)`, `user_id(FK)`, `blocked_user_id(FK)`, `blocked_at`                                    |

CREATE TABLE interaction_engagement (
    visit_id BIGSERIAL PRIMARY KEY,
    visitor_user_id BIGINT REFERENCES users(user_id),
    visited_user_id BIGINT REFERENCES users(user_id),
    visited_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE express_interest (
    interest_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id),
    receiver_id BIGINT REFERENCES users(user_id),
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, rejected
    sent_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id),
    receiver_id BIGINT REFERENCES users(user_id),
    message_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE
);
CREATE TABLE blocked_users (
    block_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    blocked_user_id BIGINT REFERENCES users(user_id),
    blocked_at TIMESTAMP DEFAULT NOW()
);


-- =====================================================
-- 5️⃣ INTERACTIONS & MATCHING
-- =====================================================

CREATE TABLE profile_visits (
    visit_id BIGSERIAL PRIMARY KEY,
    visitor_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    visited_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    visited_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(visitor_id, visited_id, DATE(visited_at))
);

CREATE TABLE express_interest (
    interest_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'Pending',
    sent_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sender_id, receiver_id)
);

CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE match_scores (
    match_id BIGSERIAL PRIMARY KEY,
    user1_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    user2_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    compatibility_score DECIMAL(5,2) NOT NULL,
    score_factors JSONB,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user1_id, user2_id)
);
CREATE TABLE blocked_users (
    block_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    blocked_user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    blocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, blocked_user_id)
);

-- Indexes for performance optimization
CREATE INDEX idx_profile_visits_visitor ON profile_visits(visitor_id);
CREATE INDEX idx_express_interest_receiver ON express_interest(receiver_id);
CREATE INDEX idx_messages_receiver ON messages(receiver_id);
CREATE INDEX idx_blocked_users_user ON blocked_users(user_id);