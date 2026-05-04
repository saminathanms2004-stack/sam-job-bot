CREATE TABLE IF NOT EXISTS applied_jobs (
  id SERIAL PRIMARY KEY,
  job_id TEXT UNIQUE NOT NULL,
  job_title TEXT,
  company TEXT,
  status TEXT DEFAULT 'applied',
  applied_at TIMESTAMPTZ DEFAULT NOW()
);
