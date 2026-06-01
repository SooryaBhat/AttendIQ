-- ============================================================
--  AttendIQ — Supabase PostgreSQL Schema
--  File: database/schema.sql
--
--  Paste this entire file into:
--  Supabase Dashboard → SQL Editor → New Query → Run
-- ============================================================


-- ============================================================
--  EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
--  ENUMS
-- ============================================================

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM (
        'super_admin', 'department_admin', 'faculty', 'student'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE attendance_method AS ENUM ('face', 'voice');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE attendance_status AS ENUM ('present', 'absent');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE session_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE enrollment_type AS ENUM ('face', 'voice');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ============================================================
--  TABLE: departments
-- ============================================================

CREATE TABLE IF NOT EXISTS departments (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT        NOT NULL UNIQUE,
    code        TEXT        NOT NULL UNIQUE,
    description TEXT,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_departments_code ON departments (code);


-- ============================================================
--  TABLE: profiles  (ALL users — every role)
-- ============================================================

CREATE TABLE IF NOT EXISTS profiles (
    id              UUID        PRIMARY KEY,
    email           TEXT        NOT NULL UNIQUE,
    password_hash   TEXT        NOT NULL,
    full_name       TEXT        NOT NULL,
    role            user_role   NOT NULL,
    department_id   UUID        REFERENCES departments (id) ON DELETE SET NULL,
    roll_number     TEXT        UNIQUE,
    phone           TEXT,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    face_enrolled   BOOLEAN     NOT NULL DEFAULT FALSE,
    voice_enrolled  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email      ON profiles (email);
CREATE INDEX IF NOT EXISTS idx_profiles_role       ON profiles (role);
CREATE INDEX IF NOT EXISTS idx_profiles_department ON profiles (department_id);
CREATE INDEX IF NOT EXISTS idx_profiles_roll       ON profiles (roll_number);


-- ============================================================
--  TABLE: subjects
-- ============================================================

CREATE TABLE IF NOT EXISTS subjects (
    id            UUID     PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          TEXT     NOT NULL,
    code          TEXT     NOT NULL UNIQUE,
    department_id UUID     NOT NULL REFERENCES departments (id) ON DELETE CASCADE,
    faculty_id    UUID     REFERENCES profiles (id) ON DELETE SET NULL,
    semester      SMALLINT NOT NULL CHECK (semester BETWEEN 1 AND 10),
    credits       SMALLINT DEFAULT 3  CHECK (credits  BETWEEN 1 AND 6),
    is_active     BOOLEAN  NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subjects_department ON subjects (department_id);
CREATE INDEX IF NOT EXISTS idx_subjects_faculty    ON subjects (faculty_id);


-- ============================================================
--  TABLE: attendance_sessions
-- ============================================================

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id                 UUID             PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id         UUID             NOT NULL REFERENCES subjects (id) ON DELETE CASCADE,
    faculty_id         UUID             NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    department_id      UUID             NOT NULL REFERENCES departments (id) ON DELETE CASCADE,
    session_date       DATE             NOT NULL DEFAULT CURRENT_DATE,
    session_label      TEXT,
    method             attendance_method NOT NULL,
    status             session_status   NOT NULL DEFAULT 'pending',
    uploaded_file_path TEXT,
    total_students     INTEGER          DEFAULT 0,
    present_count      INTEGER          DEFAULT 0,
    absent_count       INTEGER          DEFAULT 0,
    processing_log     TEXT,
    created_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_faculty    ON attendance_sessions (faculty_id);
CREATE INDEX IF NOT EXISTS idx_sessions_subject    ON attendance_sessions (subject_id);
CREATE INDEX IF NOT EXISTS idx_sessions_date       ON attendance_sessions (session_date);


-- ============================================================
--  TABLE: attendance_records
-- ============================================================

CREATE TABLE IF NOT EXISTS attendance_records (
    id            UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id    UUID              NOT NULL REFERENCES attendance_sessions (id) ON DELETE CASCADE,
    student_id    UUID              NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    subject_id    UUID              NOT NULL REFERENCES subjects (id) ON DELETE CASCADE,
    department_id UUID              NOT NULL REFERENCES departments (id) ON DELETE CASCADE,
    status        attendance_status NOT NULL DEFAULT 'absent',
    method        attendance_method,
    confidence    NUMERIC(5,4)      CHECK (confidence BETWEEN 0 AND 1),
    marked_at     TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    remarks       TEXT,
    created_at    TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_student UNIQUE (session_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_session   ON attendance_records (session_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student   ON attendance_records (student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_subject   ON attendance_records (subject_id);


-- ============================================================
--  TABLE: biometric_enrollments
-- ============================================================

CREATE TABLE IF NOT EXISTS biometric_enrollments (
    id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id    UUID            NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    type          enrollment_type NOT NULL,
    encoding      TEXT            NOT NULL,
    file_path     TEXT,
    model_version TEXT,
    is_active     BOOLEAN         NOT NULL DEFAULT TRUE,
    enrolled_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_enrollment_student_type UNIQUE (student_id, type)
);

CREATE INDEX IF NOT EXISTS idx_enrollment_student ON biometric_enrollments (student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_type    ON biometric_enrollments (type);


-- ============================================================
--  TRIGGER: auto-update updated_at on all tables
-- ============================================================

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_departments
        BEFORE UPDATE ON departments
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_profiles
        BEFORE UPDATE ON profiles
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_subjects
        BEFORE UPDATE ON subjects
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_sessions
        BEFORE UPDATE ON attendance_sessions
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_attendance
        BEFORE UPDATE ON attendance_records
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_enrollments
        BEFORE UPDATE ON biometric_enrollments
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ============================================================
--  RLS: Enable but allow service role full access
--  The backend uses the service role key which bypasses RLS.
--  These policies protect direct/anon access only.
-- ============================================================

ALTER TABLE departments          ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles             ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects             ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records   ENABLE ROW LEVEL SECURITY;
ALTER TABLE biometric_enrollments ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access to all tables (backend uses this)
DO $$ BEGIN
    CREATE POLICY "service_role_all_departments"
        ON departments FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "service_role_all_profiles"
        ON profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "service_role_all_subjects"
        ON subjects FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "service_role_all_sessions"
        ON attendance_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "service_role_all_records"
        ON attendance_records FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "service_role_all_enrollments"
        ON biometric_enrollments FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ============================================================
--  END OF SCHEMA
-- ============================================================