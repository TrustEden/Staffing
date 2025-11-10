CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE user_role AS ENUM ('admin', 'staff', 'agency_admin', 'agency_staff');
CREATE TYPE company_type AS ENUM ('facility', 'agency');
CREATE TYPE shift_status AS ENUM ('open', 'pending', 'approved', 'denied', 'cancelled');
CREATE TYPE shift_visibility AS ENUM ('internal', 'agency', 'all', 'tiered');
CREATE TYPE claim_status AS ENUM ('pending', 'approved', 'denied');
CREATE TYPE relationship_status AS ENUM ('invited', 'active', 'revoked');

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type company_type NOT NULL,
    address VARCHAR(255),
    contact_email VARCHAR(255),
    phone VARCHAR(50),
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    license_number VARCHAR(100),
    role user_role NOT NULL,
    company_id UUID REFERENCES companies(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    role_required VARCHAR(100) NOT NULL,
    status shift_status NOT NULL DEFAULT 'open',
    visibility shift_visibility NOT NULL DEFAULT 'internal',
    posted_by_id UUID NOT NULL REFERENCES users(id),
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    premium_notes TEXT,
    recurring_template_id UUID,
    release_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_shift_time_range CHECK (start_time < end_time)
);

CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shift_id UUID NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status claim_status NOT NULL DEFAULT 'pending',
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by_id UUID REFERENCES users(id),
    denial_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_claim_shift_user UNIQUE (shift_id, user_id)
);

CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    agency_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    status relationship_status NOT NULL,
    invited_by_id UUID REFERENCES users(id),
    invite_accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_relationship_facility_agency UNIQUE (facility_id, agency_id)
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    entity_id UUID,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details JSONB
);

CREATE INDEX ix_shifts_facility_date ON shifts (facility_id, date);
CREATE INDEX ix_claims_shift_id ON claims (shift_id);
CREATE INDEX ix_notifications_recipient ON notifications (recipient_id, read);
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['companies','users','shifts','claims','relationships','notifications']
    LOOP
        EXECUTE format('CREATE TRIGGER trig_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION set_updated_at();', tbl, tbl);
    END LOOP;
END;
$$;
