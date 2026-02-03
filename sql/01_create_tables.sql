  -- JD2Q Database Schema
  -- Run this in Supabase SQL Editor to create all tables
  -- This assumes the auth.users table already exists from Supabase Auth

  -- Users table (links to Supabase auth.users)
  CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  -- Create index on email for faster lookups
  CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

  -- API Keys table (encrypted Gemini API keys)
  CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  -- Create indexes for faster queries
  CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
  CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at DESC);

  -- Generation Requests table
  CREATE TABLE IF NOT EXISTS generation_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE RESTRICT,
    job_description TEXT NOT NULL,
    role_level TEXT,
    extracted_skills JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  -- Create indexes for faster queries
  CREATE INDEX IF NOT EXISTS idx_generation_requests_user_id ON generation_requests(user_id);
  CREATE INDEX IF NOT EXISTS idx_generation_requests_created_at ON generation_requests(created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_generation_requests_status ON generation_requests(status);

  -- Questions table
  CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES generation_requests(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    section_title TEXT,
    skill TEXT,
    question_type TEXT,
    difficulty TEXT,
    question_text TEXT NOT NULL,
    expected_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_answer TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  -- Create indexes for faster queries
  CREATE INDEX IF NOT EXISTS idx_questions_generation_id ON questions(generation_id);
  CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at);

  -- Activity Logs table
  CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  -- Create indexes for faster queries
  CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
  CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);

  -- Create function to increment API key usage (called from service)
  CREATE OR REPLACE FUNCTION increment_key_usage(key_id UUID)
  RETURNS VOID AS $$
  BEGIN
    UPDATE api_keys 
    SET usage_count = usage_count + 1,
        last_used = NOW()
    WHERE id = key_id;
  END;
  $$ LANGUAGE plpgsql SECURITY DEFINER;

  -- Create function to update updated_at timestamp
  CREATE OR REPLACE FUNCTION update_updated_at_column()
  RETURNS TRIGGER AS $$
  BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;

  -- Create trigger for users table
  CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  -- Comments for documentation
  COMMENT ON TABLE users IS 'User profiles linked to Supabase Auth';
  COMMENT ON TABLE api_keys IS 'Encrypted Gemini API keys for each user';
  COMMENT ON TABLE generation_requests IS 'History of question generation requests';
  COMMENT ON TABLE questions IS 'Generated interview questions';
  COMMENT ON TABLE activity_logs IS 'User activity audit log';
