-- ============================================================
--  AttendIQ — Complete PostgreSQL Database Schema
--  Supabase-ready
-- ============================================================

-- ============================================================
--  1. DEPARTMENTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL UNIQUE,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    contact_email   VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  2. PROFILES (Users) TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY,
    full_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    role            VARCHAR(50) NOT NULL DEFAULT 'student',
    department_id   UUID REFERENCES departments(id) ON DELETE SET NULL,
    roll_number     VARCHAR(50),
    semester        INT,
    section         VARCHAR(50),
    face_enrolled   BOOLEAN DEFAULT FALSE,
    voice_enrolled  BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT FALSE,
    activation_token VARCHAR(500),
    activation_expires TIMESTAMP,
    account_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(department_id, roll_number) WHERE roll_number IS NOT NULL
);

-- ============================================================
--  3. SUBJECTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS subjects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(100) NOT NULL UNIQUE,
    department_id   UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    faculty_id      UUID REFERENCES profiles(id) ON DELETE SET NULL,
    semester        INT,
    section         VARCHAR(50),
    join_code       VARCHAR(10) NOT NULL UNIQUE,
    qr_code_data    TEXT,
    description     TEXT,
    credits         INT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  4. STUDENT_SUBJECTS (Enrollment) TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS student_subjects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    subject_id      UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, subject_id)
);

-- ============================================================
--  5. ATTENDANCE_SESSIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id      UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    faculty_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    session_date    DATE NOT NULL,
    start_time      TIME,
    end_time        TIME,
    session_label   VARCHAR(255),
    status          VARCHAR(50) DEFAULT 'scheduled',
    qr_code         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  6. ATTENDANCE_RECORDS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    status          VARCHAR(50) DEFAULT 'unmarked',
    marked_by       VARCHAR(50),
    marked_at       TIMESTAMP,
    face_match_score FLOAT,
    voice_match_score FLOAT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, student_id)
);

-- ============================================================
--  7. FACE_EMBEDDINGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS face_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    embedding       BYTEA NOT NULL,
    image_path      VARCHAR(500),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id)
);

-- ============================================================
--  8. VOICE_EMBEDDINGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS voice_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    embedding       BYTEA NOT NULL,
    audio_path      VARCHAR(500),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id)
);

-- ============================================================
--  9. INDEXES FOR PERFORMANCE
-- ============================================================
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_department_id ON profiles(department_id);
CREATE INDEX idx_student_subjects_student_id ON student_subjects(student_id);
CREATE INDEX idx_student_subjects_subject_id ON student_subjects(subject_id);
CREATE INDEX idx_attendance_sessions_subject_id ON attendance_sessions(subject_id);
CREATE INDEX idx_attendance_sessions_faculty_id ON attendance_sessions(faculty_id);
CREATE INDEX idx_attendance_records_session_id ON attendance_records(session_id);
CREATE INDEX idx_attendance_records_student_id ON attendance_records(student_id);
CREATE INDEX idx_face_embeddings_student_id ON face_embeddings(student_id);
CREATE INDEX idx_voice_embeddings_student_id ON voice_embeddings(student_id);

-- ============================================================
--  10. ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_embeddings ENABLE ROW LEVEL SECURITY;
