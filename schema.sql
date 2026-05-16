CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    cost NUMERIC(10,2) NOT NULL,
    billing_cycle VARCHAR(20),
    seats_paid INTEGER,
    seats_used INTEGER,
    renewal_date DATE,
    owner VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE budget (
    id SERIAL PRIMARY KEY,
    monthly_budget NUMERIC(10,2) NOT NULL,
    team_size INTEGER DEFAULT 10,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO budget (monthly_budget) VALUES (1000);