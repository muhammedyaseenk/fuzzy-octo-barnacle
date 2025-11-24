| Table            | Description                        | Key Fields                                         |
| ---------------- | ---------------------------------- | -------------------------------------------------- |
| `states`         | Indian states                      | `state_id(PK)`, `state_name`                       |
| `districts`      | Districts (e.g., Kerala districts) | `district_id(PK)`, `state_id(FK)`, `district_name` |
| `cities`         | Cities & towns                     | `city_id(PK)`, `district_id(FK)`, `city_name`      |
| `religions`      | Religion list                      | `religion_id(PK)`, `religion_name`                 |
| `castes`         | Caste list                         | `caste_id(PK)`, `religion_id(FK)`, `caste_name`    |
| `mother_tongues` | Languages                          | `mother_tongue_id(PK)`, `language_name`            |
-- =================================

CREATE PRIMARY TABLE user_cards_primary_details (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
    full_name VARCHAR(255) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    height INT NOT NULL,
    weight INT NOT NULL,
    marital_status VARCHAR(20) NOT NULL,
    mother_tongue_id INT REFERENCES mother_tongues(mother_tongue_id),
    religion_id INT REFERENCES religions(religion_id),
    caste_id INT REFERENCES castes(caste_id),
    sub_caste VARCHAR(255),
    city_id INT REFERENCES cities(city_id),
    state_id INT REFERENCES states(state_id),
    country_id INT REFERENCES countries(country_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP.
    hobbies JSONB,
    looking_for VARCHAR(255),
    education VARCHAR(255),
    occupation VARCHAR(255),
    family_financial_status VARCHAR(255), / only for system to pick
    rule OUTER JOINS (
        SELECT
            up.user_id,
            CONCAT(up.first_name, ' ', up.last_name) AS full_name,
            DATE_PART('year', AGE(CURRENT_DATE, up.dob)) AS age,
            up.gender,
            up.height,up.weight,
            up.marital_status,  
            up.mother_tongue_id,
            up.religion_id,
            up.caste_id,
            up.sub_caste,
            up.city_id,
            c.state_id,
            c.country_id,
            ue.highest_degree AS education,

    
)