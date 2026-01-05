-- Schéma PostgreSQL initial
-- Adapté pour centraliser les offres, tracer les swipes et les candidatures avec variantes de CV.

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label TEXT NOT NULL, -- ex: "Data Analyst", "Backend Go"
  headline TEXT,
  skills JSONB DEFAULT '{}'::jsonb,
  experience JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, label)
);

CREATE TABLE IF NOT EXISTS job_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  kind TEXT NOT NULL, -- api | rss | scrape | manual
  base_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES job_sources(id) ON DELETE SET NULL,
  source_job_id TEXT, -- identifiant propre à la source
  title TEXT NOT NULL,
  company TEXT,
  location TEXT,
  employment_type TEXT, -- full-time, internship, contract
  seniority TEXT,
  salary_min NUMERIC,
  salary_max NUMERIC,
  currency TEXT,
  is_remote BOOLEAN DEFAULT FALSE,
  url TEXT,
  description TEXT,
  tags TEXT[],
  published_at TIMESTAMPTZ,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_job_id)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES job_sources(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL, -- success | partial | failed
  note TEXT
);

CREATE TABLE IF NOT EXISTS job_ingestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES ingestion_runs(id) ON DELETE CASCADE,
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  status TEXT NOT NULL, -- created | updated | skipped
  raw JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS swipes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  decision TEXT NOT NULL, -- yes | no
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, job_id)
);

CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  swipe_id UUID REFERENCES swipes(id) ON DELETE SET NULL,
  status TEXT NOT NULL, -- draft | generated | submitted | rejected | accepted
  submitted_at TIMESTAMPTZ,
  channel TEXT, -- email | form | ats
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
  application_id UUID REFERENCES applications(id) ON DELETE SET NULL,
  profile_label TEXT, -- correspond à user_profiles.label
  model TEXT, -- provider/modèle IA
  prompt TEXT,
  cv_url TEXT,
  cover_letter_url TEXT,
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, provider)
);

-- Indexes utiles
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs USING gin (to_tsvector('simple', title));
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);
CREATE INDEX IF NOT EXISTS idx_swipes_user ON swipes (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications (user_id);
