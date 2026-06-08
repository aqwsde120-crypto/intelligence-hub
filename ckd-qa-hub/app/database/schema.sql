-- Warning Letters
CREATE TABLE IF NOT EXISTS warning_letters (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_name TEXT NOT NULL,
    country TEXT,
    issued_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FDA 483
CREATE TABLE IF NOT EXISTS fda_483 (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_name TEXT NOT NULL,
    inspection_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MFDS 공지사항
CREATE TABLE IF NOT EXISTS mfds_notices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    published_date DATE,
    source_url TEXT UNIQUE NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI 분석 결과
CREATE TABLE IF NOT EXISTS ai_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_type TEXT NOT NULL,  -- 'warning_letter' | 'fda_483' | 'mfds_notice'
    source_id UUID NOT NULL,
    summary TEXT,
    root_cause TEXT,
    gmp_area TEXT,
    risk_level TEXT,
    capa TEXT,
    lessons_learned TEXT,
    ckd_impact TEXT,
    recommended_action TEXT,
    alcoa_category TEXT,        -- 데이터 완전성 분류
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);

-- 주간 브리핑
CREATE TABLE IF NOT EXISTS weekly_briefings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    week_start DATE NOT NULL UNIQUE,
    briefing_content TEXT,
    action_items TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 정책
ALTER TABLE warning_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE fda_483 ENABLE ROW LEVEL SECURITY;
ALTER TABLE mfds_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_briefings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_all" ON warning_letters FOR ALL USING (true);
CREATE POLICY "allow_all" ON fda_483 FOR ALL USING (true);
CREATE POLICY "allow_all" ON mfds_notices FOR ALL USING (true);
CREATE POLICY "allow_all" ON ai_analyses FOR ALL USING (true);
CREATE POLICY "allow_all" ON weekly_briefings FOR ALL USING (true);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_wl_date ON warning_letters(issued_date DESC);
CREATE INDEX IF NOT EXISTS idx_483_date ON fda_483(inspection_date DESC);
CREATE INDEX IF NOT EXISTS idx_mfds_date ON mfds_notices(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_source ON ai_analyses(source_type, source_id);
