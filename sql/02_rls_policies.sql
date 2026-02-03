-- Row-Level Security (RLS) Policies
-- Run this after creating tables to ensure users can only access their own data

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- USERS TABLE POLICIES
-- =====================================================

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  USING (auth.uid() = id);

-- Users can insert their own profile (for new signups)
CREATE POLICY "Users can insert own profile"
  ON users FOR INSERT
  WITH CHECK (auth.uid() = id);

-- =====================================================
-- API_KEYS TABLE POLICIES
-- =====================================================

-- Users can view their own API keys
CREATE POLICY "Users can view own API keys"
  ON api_keys FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own API keys
CREATE POLICY "Users can insert own API keys"
  ON api_keys FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own API keys
CREATE POLICY "Users can delete own API keys"
  ON api_keys FOR DELETE
  USING (auth.uid() = user_id);

-- Users can update their own API keys (for usage tracking)
CREATE POLICY "Users can update own API keys"
  ON api_keys FOR UPDATE
  USING (auth.uid() = user_id);

-- =====================================================
-- GENERATION_REQUESTS TABLE POLICIES
-- =====================================================

-- Users can view their own generation requests
CREATE POLICY "Users can view own generation requests"
  ON generation_requests FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own generation requests
CREATE POLICY "Users can insert own generation requests"
  ON generation_requests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own generation requests
CREATE POLICY "Users can update own generation requests"
  ON generation_requests FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own generation requests
CREATE POLICY "Users can delete own generation requests"
  ON generation_requests FOR DELETE
  USING (auth.uid() = user_id);

-- =====================================================
-- QUESTIONS TABLE POLICIES
-- =====================================================

-- Users can view questions from their own generation requests
CREATE POLICY "Users can view own questions"
  ON questions FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM generation_requests
      WHERE generation_requests.id = questions.generation_id
      AND generation_requests.user_id = auth.uid()
    )
  );

-- Users can insert questions for their own generation requests
CREATE POLICY "Users can insert own questions"
  ON questions FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM generation_requests
      WHERE generation_requests.id = questions.generation_id
      AND generation_requests.user_id = auth.uid()
    )
  );

-- Users can update questions from their own generation requests
CREATE POLICY "Users can update own questions"
  ON questions FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM generation_requests
      WHERE generation_requests.id = questions.generation_id
      AND generation_requests.user_id = auth.uid()
    )
  );

-- Users can delete questions from their own generation requests
CREATE POLICY "Users can delete own questions"
  ON questions FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM generation_requests
      WHERE generation_requests.id = questions.generation_id
      AND generation_requests.user_id = auth.uid()
    )
  );

-- =====================================================
-- ACTIVITY_LOGS TABLE POLICIES
-- =====================================================

-- Users can view their own activity logs
CREATE POLICY "Users can view own activity logs"
  ON activity_logs FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own activity logs
CREATE POLICY "Users can insert own activity logs"
  ON activity_logs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Note: Users typically don't update or delete activity logs (audit trail)

-- =====================================================
-- SERVICE ROLE POLICIES (for backend operations)
-- =====================================================

-- The service role key can bypass RLS for administrative operations
-- This is handled automatically by Supabase when using the service role key

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

-- Grant usage on tables to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON generation_requests TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON questions TO authenticated;
GRANT SELECT, INSERT ON activity_logs TO authenticated;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION increment_key_usage(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION update_updated_at_column() TO authenticated;
