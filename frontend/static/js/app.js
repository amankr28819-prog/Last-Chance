// Last Chance — Personal Study Planner & Exam Preparation System
// Local-First, High-Contrast Accessible Design System
const { useState, useEffect, useMemo, useRef } = React;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [theme, setTheme] = useState(localStorage.getItem('lastchance_theme') || 'dark');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  // Core Data States
  const [timeData, setTimeData] = useState(null);
  const [dates, setDates] = useState(null);
  const [feasibility, setFeasibility] = useState(null);
  const [settings, setSettings] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [todaySchedule, setTodaySchedule] = useState(null);
  const [todayQuote, setTodayQuote] = useState(null);
  const [dailyDSA, setDailyDSA] = useState(null);
  const [englishToday, setEnglishToday] = useState(null);

  // Focus Session Modal State
  const [focusSessionTask, setFocusSessionTask] = useState(null);
  const [isFocusModalOpen, setIsFocusModalOpen] = useState(false);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Synchronize Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('lastchance_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Clock Update (Ticking every second)
  useEffect(() => {
    const fetchTime = async () => {
      try {
        const t = await window.LastChanceAPI.getTime();
        setTimeData(t);
      } catch (e) {
        // Fallback local clock
        const now = new Date();
        setTimeData({
          formatted_date: now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
          formatted_time: now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }),
          date_str: now.toISOString().split('T')[0],
          timezone: 'Asia/Kolkata'
        });
      }
    };
    fetchTime();
    const interval = setInterval(fetchTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [dInfo, fInfo, stg, subjs, tSched, quote, dsa, eng] = await Promise.all([
        window.LastChanceAPI.getDates(),
        window.LastChanceAPI.getFeasibility(),
        window.LastChanceAPI.getSettings(),
        window.LastChanceAPI.getSubjects(),
        window.LastChanceAPI.getTodaySchedule(),
        window.LastChanceAPI.getDailyQuote().catch(() => null),
        window.LastChanceAPI.getDailyDSA().catch(() => null),
        window.LastChanceAPI.getEnglishToday().catch(() => null)
      ]);
      setDates(dInfo);
      setFeasibility(fInfo);
      setSettings(stg);
      setSubjects(subjs);
      setTodaySchedule(tSched);
      if (quote) setTodayQuote(quote.quote);
      if (dsa) setDailyDSA(dsa);
      if (eng) setEnglishToday(eng);
    } catch (err) {
      console.error(err);
      showToast('Failed to load initial data: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const refreshAll = async () => {
    try {
      const [dInfo, fInfo, subjs, tSched, quote, dsa, eng] = await Promise.all([
        window.LastChanceAPI.getDates(),
        window.LastChanceAPI.getFeasibility(),
        window.LastChanceAPI.getSubjects(),
        window.LastChanceAPI.getTodaySchedule(),
        window.LastChanceAPI.getDailyQuote().catch(() => null),
        window.LastChanceAPI.getDailyDSA().catch(() => null),
        window.LastChanceAPI.getEnglishToday().catch(() => null)
      ]);
      setDates(dInfo);
      setFeasibility(fInfo);
      setSubjects(subjs);
      setTodaySchedule(tSched);
      if (quote) setTodayQuote(quote.quote);
      if (dsa) setDailyDSA(dsa);
      if (eng) setEnglishToday(eng);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen space-y-4" style={{ backgroundColor: 'var(--bg-page)', color: 'var(--text-primary)' }}>
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-semibold tracking-wide" style={{ color: 'var(--text-muted)' }}>Loading Last Chance Study Planner...</p>
      </div>
    );
  }

  // 11 Main Navigation Items
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⚡' },
    { id: 'calendar', label: 'Study Calendar', icon: '🗓️' },
    { id: 'courses', label: 'Courses & Units', icon: '📚' },
    { id: 'dsa', label: 'Daily DSA', icon: '💻' },
    { id: 'english', label: 'English Speaking', icon: '🗣️' },
    { id: 'revision', label: 'Revision Planner', icon: '🔄' },
    { id: 'extra_time', label: 'Extra Time', icon: '⭐' },
    { id: 'analytics', label: 'Progress & Analytics', icon: '📊' },
    { id: 'history', label: 'Study History', icon: '📜' },
    { id: 'import', label: 'Handout Import', icon: '📥' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row" style={{ backgroundColor: 'var(--bg-page)', color: 'var(--text-primary)' }}>
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg border text-sm flex items-center space-x-3 transition-smooth ${
          toast.type === 'error' ? 'badge-error' :
          toast.type === 'success' ? 'badge-success' : 'badge-info'
        }`}>
          <span>{toast.type === 'error' ? '⚠️' : toast.type === 'success' ? '✓' : 'ℹ️'}</span>
          <span className="font-semibold">{toast.message}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 shrink-0 flex flex-col border-r" style={{ backgroundColor: 'var(--bg-sidebar)', borderColor: 'var(--border-color)' }}>
        {/* Branding */}
        <div className="p-5 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-extrabold text-lg shadow-sm">
                LC
              </span>
              <h1 className="text-lg font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Last Chance
              </h1>
            </div>
            <p className="text-[11px] font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
              Personal Academic Study Planner
            </p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1 flex-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-smooth text-left ${
                  isActive
                    ? 'shadow-sm'
                    : 'hover:bg-slate-800/10'
                }`}
                style={{
                  backgroundColor: isActive ? 'var(--btn-primary-bg)' : 'transparent',
                  color: isActive ? '#ffffff' : 'var(--text-secondary)'
                }}
              >
                <span className="text-base">{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                {item.id === 'dsa' && dailyDSA && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    dailyDSA.solved_count >= 2 ? 'bg-emerald-500 text-white' : 'bg-slate-700 text-slate-200'
                  }`}>
                    {dailyDSA.solved_count}/2
                  </span>
                )}
                {item.id === 'english' && englishToday?.log?.is_completed && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-emerald-500 text-white">
                    ✓
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Streak & College Hours Card in Sidebar */}
        <div className="p-3.5 m-3 rounded-lg border text-xs space-y-2" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div className="flex items-center justify-between">
            <span className="font-semibold" style={{ color: 'var(--text-muted)' }}>English Streak:</span>
            <span className="font-bold text-amber-500">🔥 {englishToday?.streak_days || 0} days</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-semibold" style={{ color: 'var(--text-muted)' }}>College Today:</span>
            <span className="font-bold" style={{ color: 'var(--text-primary)' }}>
              {todaySchedule?.college_hours > 0 ? `${todaySchedule.college_hours} hrs` : 'Holiday / Off'}
            </span>
          </div>
          {feasibility && (
            <div className="pt-1.5 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <div className="flex justify-between items-center text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                <span className={`font-bold ${
                  feasibility.status_label === 'ON_TRACK' ? 'text-emerald-500' :
                  feasibility.status_label === 'TIGHT' ? 'text-amber-500' : 'text-rose-500'
                }`}>
                  {feasibility.status_label.replace('_', ' ')}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header Bar */}
        <header className="px-6 py-3.5 border-b flex flex-wrap items-center justify-between gap-4 sticky top-0 z-30" style={{ backgroundColor: 'var(--bg-header)', borderColor: 'var(--border-color)', backdropFilter: 'blur(8px)' }}>
          <div>
            <h2 className="text-base font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
              {navItems.find(n => n.id === activeTab)?.label || 'Dashboard'}
            </h2>
            {timeData && (
              <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                {timeData.formatted_date} • <span className="font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>{timeData.formatted_time}</span> (IST)
              </p>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* Quick Metrics */}
            <div className="hidden lg:flex items-center space-x-3 text-xs">
              <div className="px-2.5 py-1 rounded-md border font-medium flex items-center space-x-1.5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <span>📖 Academic:</span>
                <strong style={{ color: 'var(--text-primary)' }}>
                  {todaySchedule?.academic_completed_minutes || 0}/{todaySchedule?.academic_target_minutes || 240}m
                </strong>
              </div>
              <div className="px-2.5 py-1 rounded-md border font-medium flex items-center space-x-1.5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <span>💻 DSA:</span>
                <strong style={{ color: 'var(--text-primary)' }}>
                  {dailyDSA?.solved_count || 0}/2
                </strong>
              </div>
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border text-sm transition-smooth"
              style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              title="Toggle Light / Dark Theme"
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>

            <button
              onClick={refreshAll}
              className="p-2 rounded-lg border text-sm transition-smooth"
              style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              title="Refresh Data"
            >
              🔄
            </button>
          </div>
        </header>

        {/* View Router */}
        <main className="p-6 flex-1 overflow-y-auto max-w-7xl w-full mx-auto space-y-6">
          {activeTab === 'dashboard' && (
            <DashboardView
              todaySchedule={todaySchedule}
              dates={dates}
              feasibility={feasibility}
              todayQuote={todayQuote}
              dailyDSA={dailyDSA}
              englishToday={englishToday}
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              onNavigate={(tab) => setActiveTab(tab)}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'calendar' && (
            <StudyCalendarView
              dates={dates}
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'courses' && (
            <CoursesUnitsView
              subjects={subjects}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'dsa' && (
            <DailyDSAView
              dailyDSA={dailyDSA}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'english' && (
            <EnglishSpeakingView
              englishToday={englishToday}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'revision' && (
            <RevisionPlannerView
              dates={dates}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'extra_time' && (
            <ExtraTimeView
              onNavigate={(tab) => setActiveTab(tab)}
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              showToast={showToast}
            />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsView
              feasibility={feasibility}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'history' && (
            <StudyHistoryView
              showToast={showToast}
            />
          )}

          {activeTab === 'import' && (
            <HandoutImportView
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView
              settings={settings}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}
        </main>
      </div>

      {/* Focus Mode Running Timer Modal */}
      {isFocusModalOpen && focusSessionTask && (
        <FocusModeModal
          task={focusSessionTask}
          onClose={() => {
            setIsFocusModalOpen(false);
            setFocusSessionTask(null);
            refreshAll();
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}

// ----------------- 1. DASHBOARD VIEW -----------------

function DashboardView({ todaySchedule, dates, feasibility, todayQuote, dailyDSA, englishToday, onStartSession, onNavigate, onRefresh, showToast }) {
  const [extraRecs, setExtraRecs] = useState([]);
  const [quoteFav, setQuoteFav] = useState(todayQuote?.is_favorite || false);
  const [rescheduleModalTask, setRescheduleModalTask] = useState(null);
  const [completePct, setCompletePct] = useState(100);
  const [actualMins, setActualMins] = useState(60);
  const [confidence, setConfidence] = useState(4);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    window.LastChanceAPI.getExtraTime().then(res => {
      setExtraRecs(res.recommendations || []);
    }).catch(() => {});
  }, []);

  const academicDone = todaySchedule?.academic_completed_minutes || 0;
  const academicTarget = todaySchedule?.academic_target_minutes || 240;
  const academicPct = Math.min(100, Math.round((academicDone / academicTarget) * 100));

  const dsaSolved = dailyDSA?.solved_count || 0;
  const englishCompleted = englishToday?.log?.is_completed || false;
  const englishSeconds = englishToday?.log?.time_spent_seconds || 0;
  const englishMins = Math.floor(englishSeconds / 60);

  const tasks = todaySchedule?.tasks || [];

  const handleToggleQuoteFav = async () => {
    if (!todayQuote?.id) return;
    try {
      const res = await window.LastChanceAPI.toggleQuoteFavorite(todayQuote.id);
      setQuoteFav(res.is_favorite);
      showToast(res.is_favorite ? 'Added to favorites!' : 'Removed from favorites.');
    } catch (e) {
      showToast('Failed to update favorite', 'error');
    }
  };

  const handleQuickComplete = async (taskId, minutes) => {
    try {
      await window.LastChanceAPI.completeTask(taskId, {
        status: 'COMPLETED',
        completion_percentage: 100,
        actual_minutes: minutes,
        confidence_rating: 4,
        notes: 'Quick completed from dashboard'
      });
      await onRefresh();
      showToast('Task marked 100% completed!', 'success');
    } catch (e) {
      showToast('Failed to update task: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* 4 Core Daily Targets Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Academic Study (240m target) */}
        <div className="lc-card p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>📖 Academic Target</span>
            <span className="text-indigo-400 font-bold">{academicPct}%</span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {academicDone} <span className="text-xs font-medium text-slate-400">/ {academicTarget} mins</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-indigo-500 h-2 rounded-full transition-smooth" style={{ width: `${academicPct}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Reserved for semester coursework (4 courses).
          </p>
        </div>

        {/* Metric 2: Daily DSA (2 questions) */}
        <div className="lc-card p-4 space-y-2 cursor-pointer hover:border-emerald-500/50" onClick={() => onNavigate('dsa')}>
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>💻 Compulsory DSA</span>
            <span className={dsaSolved >= 2 ? 'badge-success badge' : 'badge-warning badge'}>
              {dsaSolved >= 2 ? 'Completed' : 'Pending'}
            </span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {dsaSolved} <span className="text-xs font-medium text-slate-400">/ 2 questions</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-emerald-500 h-2 rounded-full transition-smooth" style={{ width: `${(dsaSolved / 2) * 100}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Tracked separately outside 240m target.
          </p>
        </div>

        {/* Metric 3: English Speaking (30 min) */}
        <div className="lc-card p-4 space-y-2 cursor-pointer hover:border-amber-500/50" onClick={() => onNavigate('english')}>
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>🗣️ English Speaking</span>
            <span className={englishCompleted ? 'badge-success badge' : 'badge-warning badge'}>
              {englishCompleted ? 'Done' : 'Incomplete'}
            </span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {englishMins} <span className="text-xs font-medium text-slate-400">/ 30 mins</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-amber-500 h-2 rounded-full transition-smooth" style={{ width: `${Math.min(100, (englishMins / 30) * 100)}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Daily fluency & interview drill.
          </p>
        </div>

        {/* Metric 4: College Commitments */}
        <div className="lc-card p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>🏫 College Classes</span>
            <span className="badge badge-info font-bold">
              {todaySchedule?.college_hours > 0 ? 'Working Day' : 'Holiday'}
            </span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {todaySchedule?.college_hours || 0} <span className="text-xs font-medium text-slate-400">hours</span>
          </div>
          <p className="text-[11px] pt-2" style={{ color: 'var(--text-muted)' }}>
            {todaySchedule?.college_hours > 0
              ? 'Classes scheduled. Academic study starts afterwards.'
              : 'No college classes today. Full study window available.'}
          </p>
        </div>
      </div>

      {/* Daily Motivational Quote */}
      {todayQuote && (
        <div className="lc-card p-4 border-l-4 border-indigo-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1 flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
                Daily Motivation • {todayQuote.category}
              </span>
            </div>
            <p className="text-sm font-semibold italic text-slate-200">
              "{todayQuote.quote_text}"
            </p>
            <p className="text-xs font-medium text-slate-400">— {todayQuote.author || 'Anonymous'}</p>
          </div>
          <button
            onClick={handleToggleQuoteFav}
            className={`p-2 rounded-lg text-sm border transition-smooth shrink-0 ${
              quoteFav ? 'bg-amber-500/20 border-amber-500 text-amber-400' : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title={quoteFav ? 'Favorited' : 'Save as Favorite'}
          >
            {quoteFav ? '★ Saved' : '☆ Save'}
          </button>
        </div>
      )}

      {/* Today's Schedule & Extra Time Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Today's Timeline Tasks */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Today's Academic Study Tasks</h3>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {tasks.length} sessions scheduled • {todaySchedule?.scheduled_minutes || 0} minutes total
              </p>
            </div>
            <button
              onClick={() => window.LastChanceAPI.generateSchedule(true).then(() => { onRefresh(); showToast('Schedule recalculated!', 'success'); })}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold btn-secondary"
            >
              🔄 Recalculate
            </button>
          </div>

          {tasks.length === 0 ? (
            <div className="lc-card p-8 text-center space-y-3">
              <p className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                No academic study sessions scheduled for today.
              </p>
              <button
                onClick={() => window.LastChanceAPI.generateSchedule(true).then(() => { onRefresh(); showToast('Schedule generated!', 'success'); })}
                className="btn-primary text-xs font-bold"
              >
                Generate Today's Study Plan
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task, idx) => {
                const isCompleted = task.status === 'COMPLETED';
                return (
                  <div key={task.id} className="lc-card p-4 space-y-3 transition-smooth">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: task.subject_color || '#4f46e5' }}>
                          {task.subject_code}
                        </span>
                        <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                          Unit {task.unit_number}: {task.unit_title}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                          ⏱️ {task.duration_minutes}m
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        isCompleted ? 'badge-success badge' : 'badge-warning badge'
                      }`}>
                        {task.status}
                      </span>
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-slate-100">{task.topic_title}</h4>
                      {task.subtopics?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {task.subtopics.map((st, i) => (
                            <span key={i} className="code-pill text-[11px]">{st}</span>
                          ))}
                        </div>
                      )}
                    </div>

                    {task.learning_objectives && (
                      <div className="p-2.5 rounded-md text-xs border space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                        <div className="font-semibold text-indigo-400">Objectives & Method:</div>
                        <div className="text-slate-300 whitespace-pre-line text-[11px] leading-relaxed">{task.learning_objectives}</div>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between pt-1 gap-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                      <button
                        onClick={() => onStartSession(task)}
                        className="px-3 py-1.5 rounded-md text-xs font-bold btn-primary"
                      >
                        ⏱️ Launch Focus Mode
                      </button>

                      <div className="flex items-center space-x-2">
                        {!isCompleted && (
                          <button
                            onClick={() => handleQuickComplete(task.id, task.duration_minutes)}
                            className="px-3 py-1.5 rounded-md text-xs font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-smooth"
                          >
                            ✓ Mark Done
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setRescheduleModalTask(task);
                            setActualMins(task.duration_minutes);
                          }}
                          className="px-3 py-1.5 rounded-md text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 transition-smooth"
                        >
                          Log / Reschedule
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 1 Col: "Have Extra Time?" & Exam Countdown */}
        <div className="space-y-6">
          {/* "Have Extra Time? Do This Next" */}
          <div className="lc-card p-4 space-y-3 border-amber-500/30">
            <div className="flex items-center space-x-2">
              <span className="text-base">⭐</span>
              <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                Have Extra Time? Do This Next
              </h3>
            </div>
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Intelligent optional recommendations based on remaining time and weak areas:
            </p>

            <div className="space-y-2.5">
              {extraRecs.length === 0 ? (
                <p className="text-xs text-slate-400 py-3 text-center">
                  You're all caught up! Take a break and recharge.
                </p>
              ) : (
                extraRecs.map((rec, idx) => (
                  <div key={idx} className="p-3 rounded-lg border text-xs space-y-1.5 transition-smooth" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: rec.color || '#4f46e5' }}>
                        {rec.category}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">⏱️ {rec.estimated_minutes}m</span>
                    </div>
                    <div className="font-semibold text-slate-200">{rec.title}</div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{rec.reason}</p>
                    {rec.action_type === 'DSA_NAV' && (
                      <button onClick={() => onNavigate('dsa')} className="text-[11px] font-bold text-indigo-400 hover:underline pt-1 block">
                        Go to Daily DSA →
                      </button>
                    )}
                    {rec.action_type === 'ENGLISH_NAV' && (
                      <button onClick={() => onNavigate('english')} className="text-[11px] font-bold text-indigo-400 hover:underline pt-1 block">
                        Go to English Speaking →
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Upcoming Exam Milestones */}
          <div className="lc-card p-4 space-y-3">
            <h3 className="text-sm font-bold flex items-center justify-between" style={{ color: 'var(--text-primary)' }}>
              <span>🎯 Exam Countdown</span>
              <span className="text-xs text-rose-400 font-bold">First: {dates?.days_to_exam || 0}d left</span>
            </h3>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div>
                  <div className="font-bold text-slate-200">CSN 3001: Data Structures</div>
                  <div className="text-[10px] text-slate-400">Exam: 2026-11-26</div>
                </div>
                <span className="badge badge-error">Nov 26</span>
              </div>
              <div className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div>
                  <div className="font-bold text-slate-200">CSN 3003: Discrete Structures</div>
                  <div className="text-[10px] text-slate-400">Exam: 2026-11-28</div>
                </div>
                <span className="badge badge-error">Nov 28</span>
              </div>
              <div className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div>
                  <div className="font-bold text-slate-200">CSN 3004: Object-Oriented Prog</div>
                  <div className="text-[10px] text-slate-400">Exam: 2026-12-01</div>
                </div>
                <span className="badge badge-error">Dec 01</span>
              </div>
              <div className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div>
                  <div className="font-bold text-slate-200">CSN 3002: Data Science & ML</div>
                  <div className="text-[10px] text-slate-400">Exam: 2026-12-04</div>
                </div>
                <span className="badge badge-error">Dec 04</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Task Reschedule / Completion Modal */}
      {rescheduleModalTask && (
        <div className="modal-overlay" onClick={() => setRescheduleModalTask(null)}>
          <div className="modal-dialog p-5 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-base font-bold text-slate-100">Log Progress / Reschedule Task</h3>
              <button onClick={() => setRescheduleModalTask(null)} className="text-slate-400 hover:text-slate-200 text-lg">✕</button>
            </div>

            <div>
              <div className="text-xs text-indigo-400 font-bold">{rescheduleModalTask.subject_code} • {rescheduleModalTask.subject_name}</div>
              <div className="text-sm font-bold text-slate-100">{rescheduleModalTask.topic_title}</div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Completion Percentage ({completePct}%):</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="10"
                  value={completePct}
                  onChange={e => setCompletePct(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Actual Minutes Spent:</label>
                <input
                  type="number"
                  value={actualMins}
                  onChange={e => setActualMins(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Confidence Rating (1 to 5):</label>
                <select value={confidence} onChange={e => setConfidence(Number(e.target.value))} className="w-full">
                  <option value="1">1 - Stが現 Struggled / Confused</option>
                  <option value="2">2 - Partially Understood</option>
                  <option value="3">3 - Moderate Comprehension</option>
                  <option value="4">4 - Confident</option>
                  <option value="5">5 - Mastered & Retained</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Notes / Blockers:</label>
                <textarea
                  rows="2"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Record what was easy or what needs revision..."
                  className="w-full"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button onClick={() => setRescheduleModalTask(null)} className="btn-secondary text-xs">Cancel</button>
              <button
                onClick={async () => {
                  try {
                    await window.LastChanceAPI.completeTask(rescheduleModalTask.id, {
                      status: completePct >= 100 ? 'COMPLETED' : 'PARTIALLY_COMPLETED',
                      completion_percentage: completePct,
                      actual_minutes: actualMins,
                      confidence_rating: confidence,
                      notes: notes
                    });
                    setRescheduleModalTask(null);
                    await onRefresh();
                    showToast('Task progress saved and future schedule updated!', 'success');
                  } catch (e) {
                    showToast('Failed to save progress: ' + e.message, 'error');
                  }
                }}
                className="btn-primary text-xs"
              >
                Save & Update Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 2. STUDY CALENDAR VIEW (FULL REPAIR) -----------------

function StudyCalendarView({ dates, onStartSession, onRefresh, showToast }) {
  const [events, setEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(dates?.today_str || new Date().toISOString().split('T')[0]);
  const [viewMode, setViewMode] = useState('month'); // 'month', 'week', 'day'
  const [currentMonth, setCurrentMonth] = useState(() => {
    const d = new Date(selectedDate || '2026-10-25');
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const [addEventModalDate, setAddEventModalDate] = useState(null);
  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventType, setNewEventType] = useState('study');
  const [newEventTime, setNewEventTime] = useState('18:00');
  const [newEventDesc, setNewEventDesc] = useState('');

  const loadCalendarEvents = async () => {
    try {
      const data = await window.LastChanceAPI.getCalendarEvents();
      setEvents(data.events || []);
    } catch (err) {
      showToast('Failed to load calendar events: ' + err.message, 'error');
    }
  };

  useEffect(() => {
    loadCalendarEvents();
  }, []);

  // Events indexed by date
  const eventsByDate = useMemo(() => {
    const map = {};
    for (const ev of events) {
      if (!map[ev.event_date]) map[ev.event_date] = [];
      map[ev.event_date].push(ev);
    }
    return map;
  }, [events]);

  // Month navigation
  const prevMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };
  const nextMonth = () => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };
  const goToToday = () => {
    const t = new Date(dates?.today_str || '2026-10-25');
    setCurrentMonth(new Date(t.getFullYear(), t.getMonth(), 1));
    setSelectedDate(dates?.today_str || '2026-10-25');
  };

  // Generate Month Grid Days
  const monthGridDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sun
    const totalDays = new Date(year, month + 1, 0).getDate();

    const days = [];
    // Previous month padding
    const prevMonthTotalDays = new Date(year, month, 0).getDate();
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const d = prevMonthTotalDays - i;
      const dStr = new Date(year, month - 1, d).toISOString().split('T')[0];
      days.push({
        dayNumber: d,
        dateStr: dStr,
        isCurrentMonth: false,
        events: eventsByDate[dStr] || []
      });
    }

    // Current month days
    for (let d = 1; d <= totalDays; d++) {
      const dStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        dayNumber: d,
        dateStr: dStr,
        isCurrentMonth: true,
        events: eventsByDate[dStr] || []
      });
    }

    // Next month padding to fill 35 or 42 cells
    const remaining = (7 - (days.length % 7)) % 7;
    for (let d = 1; d <= remaining; d++) {
      const dStr = new Date(year, month + 1, d).toISOString().split('T')[0];
      days.push({
        dayNumber: d,
        dateStr: dStr,
        isCurrentMonth: false,
        events: eventsByDate[dStr] || []
      });
    }

    return days;
  }, [currentMonth, eventsByDate]);

  // Selected date events
  const selectedDayEvents = eventsByDate[selectedDate] || [];

  const handleCreateCustomEvent = async () => {
    if (!newEventTitle.trim()) {
      showToast('Please enter an event title', 'error');
      return;
    }
    try {
      await window.LastChanceAPI.createCalendarEvent({
        title: newEventTitle,
        description: newEventDesc,
        event_date: addEventModalDate,
        start_time: newEventTime,
        event_type: newEventType,
        is_completed: false
      });
      setAddEventModalDate(null);
      setNewEventTitle('');
      setNewEventDesc('');
      await loadCalendarEvents();
      showToast('Custom calendar event created!', 'success');
    } catch (e) {
      showToast('Failed to create event: ' + e.message, 'error');
    }
  };

  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const currentMonthLabel = `${monthNames[currentMonth.getMonth()]} ${currentMonth.getFullYear()}`;

  return (
    <div className="space-y-6">
      {/* Calendar Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Study Calendar</h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Real schedule timeline, college class schedules, exams, and special breaks
          </p>
        </div>

        {/* View Switcher & Month Navigation */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1.5 text-xs font-semibold ${viewMode === 'month' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Month
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={`px-3 py-1.5 text-xs font-semibold ${viewMode === 'week' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Week
            </button>
            <button
              onClick={() => setViewMode('day')}
              className={`px-3 py-1.5 text-xs font-semibold ${viewMode === 'day' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Day
            </button>
          </div>

          <div className="flex items-center space-x-1.5">
            <button onClick={prevMonth} className="px-2.5 py-1.5 rounded-lg border text-xs btn-secondary" title="Previous Month">
              ← Prev
            </button>
            <button onClick={goToToday} className="px-3 py-1.5 rounded-lg border text-xs btn-secondary font-bold">
              Today
            </button>
            <button onClick={nextMonth} className="px-2.5 py-1.5 rounded-lg border text-xs btn-secondary" title="Next Month">
              Next →
            </button>
          </div>

          <span className="text-sm font-bold px-2 py-1" style={{ color: 'var(--text-primary)' }}>
            {currentMonthLabel}
          </span>
        </div>
      </div>

      {/* Main Calendar & Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Month View Grid */}
        {viewMode === 'month' && (
          <div className="lg:col-span-2 space-y-3">
            <div className="calendar-grid">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d, i) => (
                <div key={i} className="text-center py-2 text-xs font-bold text-slate-400 border-b border-slate-700 bg-slate-900/50">
                  {d}
                </div>
              ))}

              {monthGridDays.map((cell, idx) => {
                const isSelected = cell.dateStr === selectedDate;
                const isToday = cell.dateStr === dates?.today_str;
                const hasExams = cell.events.some(e => e.event_type === 'exam');
                const hasBreak = cell.events.some(e => e.event_type === 'holiday');

                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedDate(cell.dateStr)}
                    className={`calendar-cell ${!cell.isCurrentMonth ? 'inactive-month' : ''} ${isToday ? 'is-today' : ''} ${
                      isSelected ? 'outline outline-2 outline-indigo-500' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-bold ${isToday ? 'text-indigo-400 font-black' : 'text-slate-300'}`}>
                        {cell.dayNumber}
                      </span>
                      {cell.events.length > 0 && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          {cell.events.length}
                        </span>
                      )}
                    </div>

                    <div className="space-y-1 overflow-hidden flex-1">
                      {cell.events.slice(0, 3).map((ev, eIdx) => (
                        <div
                          key={eIdx}
                          className="calendar-event-pill text-white"
                          style={{
                            backgroundColor: ev.event_type === 'exam' ? '#ef4444' :
                                             ev.event_type === 'holiday' ? '#8b5cf6' :
                                             ev.event_type === 'college' ? '#475569' :
                                             (ev.color || '#4f46e5')
                          }}
                          title={ev.title}
                        >
                          {ev.title}
                        </div>
                      ))}
                      {cell.events.length > 3 && (
                        <div className="text-[9px] text-slate-400 text-right">
                          +{cell.events.length - 3} more
                        </div>
                      )}
                    </div>

                    {hasBreak && <span className="text-[8px] font-bold text-purple-400 uppercase">Break</span>}
                    {hasExams && <span className="text-[8px] font-bold text-rose-400 uppercase">Exam</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Week View */}
        {viewMode === 'week' && (
          <div className="lg:col-span-2 lc-card p-5 space-y-4">
            <h3 className="text-sm font-bold">Week Timeline</h3>
            <div className="space-y-3">
              {monthGridDays.slice(0, 7).map((day, idx) => (
                <div key={idx} className="p-3 rounded-lg border space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex items-center justify-between font-bold text-xs text-indigo-400">
                    <span>{day.dateStr}</span>
                    <span>{day.events.length} scheduled</span>
                  </div>
                  <div className="space-y-1">
                    {day.events.length === 0 ? (
                      <p className="text-[11px] text-slate-500">No events</p>
                    ) : (
                      day.events.map((e, ei) => (
                        <div key={ei} className="text-xs p-1.5 rounded text-white flex justify-between" style={{ backgroundColor: e.color || '#4f46e5' }}>
                          <span>{e.title}</span>
                          <span className="font-mono text-[10px]">{e.start_time}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Day View */}
        {viewMode === 'day' && (
          <div className="lg:col-span-2 lc-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <div>
                <h3 className="text-base font-bold text-slate-100">Day View: {selectedDate}</h3>
                <p className="text-xs text-slate-400">{selectedDayEvents.length} scheduled sessions & commitments</p>
              </div>
              <button
                onClick={() => setAddEventModalDate(selectedDate)}
                className="btn-primary text-xs font-semibold"
              >
                + Add Event
              </button>
            </div>

            <div className="space-y-2">
              {selectedDayEvents.length === 0 ? (
                <p className="text-xs text-slate-400 py-8 text-center">No events for this day.</p>
              ) : (
                selectedDayEvents.map((e, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg border space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: e.color || '#4f46e5' }}>
                        {e.event_type.toUpperCase()}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{e.start_time}</span>
                    </div>
                    <div className="text-sm font-bold text-slate-200">{e.title}</div>
                    <div className="text-xs text-slate-400">{e.description}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Selected Date Inspector Panel */}
        <div className="lc-card p-5 space-y-4">
          <div className="border-b pb-3 flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <p className="text-xs uppercase font-bold" style={{ color: 'var(--text-muted)' }}>Selected Date Details</p>
              <h3 className="text-base font-bold text-slate-100 mt-0.5">{selectedDate}</h3>
            </div>
            <button
              onClick={() => setAddEventModalDate(selectedDate)}
              className="px-2.5 py-1 text-xs font-semibold btn-primary"
            >
              + Event
            </button>
          </div>

          <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
            {selectedDayEvents.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No tasks or commitments on this date.</p>
            ) : (
              selectedDayEvents.map((ev, idx) => (
                <div key={idx} className="p-3 rounded-lg border space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: ev.color || '#4f46e5' }}>
                      {ev.event_type}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">{ev.start_time}</span>
                  </div>
                  <div className="text-xs font-bold text-slate-200">{ev.title}</div>
                  <p className="text-[11px] text-slate-400">{ev.description}</p>
                  {ev.event_type === 'study' && (
                    <div className="pt-1.5 flex justify-end">
                      <button
                        onClick={() => onStartSession({ id: ev.source_id, topic_title: ev.title, duration_minutes: ev.duration_minutes || 60 })}
                        className="px-2.5 py-1 rounded text-[11px] font-bold btn-primary"
                      >
                        ⏱️ Start Session
                      </button>
                    </div>
                  )}
                  {ev.id.startsWith('custom_') && (
                    <div className="pt-1 flex justify-end">
                      <button
                        onClick={async () => {
                          try {
                            await window.LastChanceAPI.deleteCalendarEvent(ev.source_id);
                            await loadCalendarEvents();
                            showToast('Custom event deleted');
                          } catch (e) {
                            showToast('Failed to delete event', 'error');
                          }
                        }}
                        className="text-[11px] text-rose-400 hover:underline"
                      >
                        Delete Event
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Add Custom Calendar Event Modal */}
      {addEventModalDate && (
        <div className="modal-overlay" onClick={() => setAddEventModalDate(null)}>
          <div className="modal-dialog p-5 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-base font-bold text-slate-100">Add Calendar Event ({addEventModalDate})</h3>
              <button onClick={() => setAddEventModalDate(null)} className="text-slate-400 text-lg">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Event Title:</label>
                <input
                  type="text"
                  value={newEventTitle}
                  onChange={e => setNewEventTitle(e.target.value)}
                  placeholder="e.g. Lab Exam, Extra Math Practice, Mock Test"
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Event Type:</label>
                  <select value={newEventType} onChange={e => setNewEventType(e.target.value)} className="w-full">
                    <option value="study">Academic Study</option>
                    <option value="college">College Class / Lab</option>
                    <option value="exam">Exam / Test</option>
                    <option value="personal">Personal / Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Start Time:</label>
                  <input
                    type="time"
                    value={newEventTime}
                    onChange={e => setNewEventTime(e.target.value)}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Description / Notes:</label>
                <textarea
                  rows="2"
                  value={newEventDesc}
                  onChange={e => setNewEventDesc(e.target.value)}
                  placeholder="Additional details..."
                  className="w-full"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button onClick={() => setAddEventModalDate(null)} className="btn-secondary text-xs">Cancel</button>
              <button onClick={handleCreateCustomEvent} className="btn-primary text-xs">Save Event</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 3. COURSES & UNITS VIEW -----------------

function CoursesUnitsView({ subjects, onRefresh, showToast }) {
  const [activeCourseId, setActiveCourseId] = useState(subjects[0]?.id || null);
  const [syllabusData, setSyllabusData] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    if (activeCourseId) {
      window.LastChanceAPI.getSyllabus(activeCourseId).then(res => {
        setSyllabusData(res.units || []);
      }).catch(e => console.error(e));
    }
  }, [activeCourseId]);

  const activeCourse = subjects.find(s => s.id === activeCourseId);

  const handleUpdateTopicMastery = async (topicId, newMastery) => {
    try {
      await window.LastChanceAPI.updateTopic(topicId, { mastery_level: newMastery });
      // Refresh local syllabus
      const res = await window.LastChanceAPI.getSyllabus(activeCourseId);
      setSyllabusData(res.units || []);
      showToast('Topic mastery status updated!');
    } catch (e) {
      showToast('Failed to update topic: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* 4 Course Tabs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {subjects.map(subj => {
          const isSelected = subj.id === activeCourseId;
          return (
            <div
              key={subj.id}
              onClick={() => setActiveCourseId(subj.id)}
              className={`lc-card p-4 cursor-pointer transition-smooth border-l-4 ${
                isSelected ? 'shadow-md' : 'opacity-85 hover:opacity-100'
              }`}
              style={{
                borderLeftColor: subj.color || '#4f46e5',
                backgroundColor: isSelected ? 'var(--bg-card-elevated)' : 'var(--bg-card)'
              }}
            >
              <div className="text-[11px] font-bold font-mono" style={{ color: subj.color || '#4f46e5' }}>
                {subj.code}
              </div>
              <h3 className="text-sm font-bold text-slate-100 truncate mt-0.5">{subj.name}</h3>
              <div className="text-xs text-slate-400 mt-2 flex justify-between">
                <span>{subj.credits} Credits • {subj.total_lectures} Lect</span>
                <span>Exam: {subj.exam_date || 'TBD'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Course Details & Unit Topics Hierarchy */}
      <div className="lc-card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <h3 className="text-base font-bold text-slate-100">{activeCourse?.name} ({activeCourse?.code})</h3>
            <p className="text-xs text-slate-400">Complete official university unit & topic breakdown</p>
          </div>
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search topics..."
              className="text-xs"
            />
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="text-xs">
              <option value="ALL">All Status</option>
              <option value="NOT_STARTED">Not Started</option>
              <option value="CONFIDENT">Confident</option>
              <option value="NEEDS_REVISION">Needs Revision</option>
              <option value="MASTERED">Mastered</option>
            </select>
          </div>
        </div>

        {/* Units Accordion */}
        <div className="space-y-4">
          {syllabusData.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">Loading unit syllabus data...</p>
          ) : (
            syllabusData.map(unit => {
              const filteredTopics = (unit.topics || []).filter(t => {
                const matchSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase());
                const matchStatus = statusFilter === 'ALL' || t.mastery_level === statusFilter;
                return matchSearch && matchStatus;
              });

              if (filteredTopics.length === 0 && searchTerm) return null;

              return (
                <div key={unit.id} className="p-4 rounded-xl border space-y-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
                    <div className="font-bold text-sm text-slate-200">
                      Unit {unit.unit_number}: {unit.title}
                    </div>
                    <span className="text-xs text-slate-400 font-mono">
                      {unit.lecture_allocation} Lectures • {filteredTopics.length} Topics
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {filteredTopics.map(t => (
                      <div key={t.id} className="p-3 rounded-lg border text-xs space-y-2" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-bold text-slate-100 text-sm">{t.title}</span>
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-slate-400 text-[11px]">⏱️ {t.estimated_minutes}m</span>
                            <select
                              value={t.mastery_level}
                              onChange={e => handleUpdateTopicMastery(t.id, e.target.value)}
                              className="text-[11px] font-semibold"
                            >
                              <option value="NOT_STARTED">Not Started</option>
                              <option value="STUDIED_ONCE">Studied Once</option>
                              <option value="PARTIALLY_UNDERSTOOD">Partially Understood</option>
                              <option value="NEEDS_REVISION">Needs Revision</option>
                              <option value="CONFIDENT">Confident</option>
                              <option value="MASTERED">Mastered</option>
                            </select>
                          </div>
                        </div>

                        {t.subtopics?.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {t.subtopics.map((st, sIdx) => (
                              <span key={sIdx} className="code-pill text-[10px]">{st}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ----------------- 4. DAILY DSA VIEW (2 COMPULSORY QUESTIONS) -----------------

function DailyDSAView({ dailyDSA, onRefresh, showToast }) {
  const [activeTab, setActiveTab] = useState('today'); // 'today' or 'all'
  const [allQuestions, setAllQuestions] = useState([]);
  const [hintsVisible, setHintsVisible] = useState({});
  const [solutionVisible, setSolutionVisible] = useState({});
  const [notesState, setNotesState] = useState({});
  const [timeSpentState, setTimeSpentState] = useState({});

  useEffect(() => {
    if (activeTab === 'all') {
      window.LastChanceAPI.getAllDSA().then(res => {
        setAllQuestions(res.questions || []);
      }).catch(e => console.error(e));
    }
  }, [activeTab]);

  const assignments = dailyDSA?.assignments || [];

  const handleUpdateStatus = async (assignmentId, status) => {
    try {
      await window.LastChanceAPI.updateDSAAssignment(assignmentId, {
        status: status,
        user_approach: notesState[assignmentId]?.approach || '',
        mistakes_notes: notesState[assignmentId]?.mistakes || '',
        time_spent_minutes: timeSpentState[assignmentId] || 25
      });
      await onRefresh();
      showToast(`DSA question marked as ${status}!`, 'success');
    } catch (e) {
      showToast('Failed to update DSA status: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Daily DSA (Data Structures Practice)</h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Exactly 2 compulsory practice problems assigned daily from the university Data Structures syllabus.
          </p>
        </div>

        <div className="flex rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('today')}
            className={`px-3 py-1.5 text-xs font-semibold ${activeTab === 'today' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
          >
            Today's 2 Questions
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 text-xs font-semibold ${activeTab === 'all' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
          >
            Question Bank ({allQuestions.length || '15+'})
          </button>
        </div>
      </div>

      {activeTab === 'today' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {assignments.length === 0 ? (
              <div className="col-span-2 lc-card p-8 text-center text-xs text-slate-400">
                Loading today's assigned DSA questions...
              </div>
            ) : (
              assignments.map((item, idx) => {
                const q = item;
                const isSolved = item.status === 'Solved';
                return (
                  <div key={item.id} className="lc-card p-5 space-y-4 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          Problem #{idx + 1} • {q.topic}
                        </span>
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                          q.difficulty === 'Easy' ? 'bg-blue-500/10 text-blue-400' :
                          q.difficulty === 'Medium' ? 'bg-amber-500/10 text-amber-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>
                          {q.difficulty}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-slate-100">{q.title}</h3>

                      <div className="p-3 rounded-lg border text-xs text-slate-300 leading-relaxed font-mono" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                        {q.problem_statement}
                      </div>

                      {q.concept && (
                        <div className="text-xs text-slate-400">
                          <strong className="text-slate-200">Core Concept:</strong> {q.concept}
                        </div>
                      )}

                      {/* Progressive Hints Accordions */}
                      <div className="space-y-1.5 pt-1">
                        {q.hint_1 && (
                          <div>
                            <button
                              onClick={() => setHintsVisible(p => ({ ...p, [`${item.id}_1`]: !p[`${item.id}_1`] }))}
                              className="text-xs font-semibold text-indigo-400 hover:underline flex items-center space-x-1"
                            >
                              <span>{hintsVisible[`${item.id}_1`] ? '▼ Hide Hint 1' : '► Reveal Hint 1'}</span>
                            </button>
                            {hintsVisible[`${item.id}_1`] && (
                              <p className="text-xs text-slate-300 p-2 rounded bg-slate-800/60 mt-1 border border-slate-700">
                                💡 {q.hint_1}
                              </p>
                            )}
                          </div>
                        )}

                        {q.hint_2 && (
                          <div>
                            <button
                              onClick={() => setHintsVisible(p => ({ ...p, [`${item.id}_2`]: !p[`${item.id}_2`] }))}
                              className="text-xs font-semibold text-indigo-400 hover:underline flex items-center space-x-1"
                            >
                              <span>{hintsVisible[`${item.id}_2`] ? '▼ Hide Hint 2' : '► Reveal Hint 2'}</span>
                            </button>
                            {hintsVisible[`${item.id}_2`] && (
                              <p className="text-xs text-slate-300 p-2 rounded bg-slate-800/60 mt-1 border border-slate-700">
                                💡 {q.hint_2}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Solution & Code Reveal */}
                        <div>
                          <button
                            onClick={() => setSolutionVisible(p => ({ ...p, [item.id]: !p[item.id] }))}
                            className="text-xs font-bold text-amber-400 hover:underline flex items-center space-x-1 pt-1"
                          >
                            <span>{solutionVisible[item.id] ? '▼ Hide Explanation & Code' : '► Reveal Solution & Code'}</span>
                          </button>
                          {solutionVisible[item.id] && (
                            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 mt-2 space-y-2 text-xs">
                              <div className="text-slate-300 whitespace-pre-line">{q.solution_approach}</div>
                              {q.solution_code && (
                                <pre className="p-2.5 rounded bg-black/60 text-[11px] font-mono text-emerald-300 overflow-x-auto border border-slate-800">
                                  {q.solution_code}
                                </pre>
                              )}
                              <div className="flex justify-between text-[11px] text-slate-400 border-t border-slate-800 pt-1">
                                <span>Time: {q.time_complexity || 'O(N)'}</span>
                                <span>Space: {q.space_complexity || 'O(1)'}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Approach & Mistakes Recording */}
                      <div className="space-y-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                        <textarea
                          rows="2"
                          placeholder="Record your logic, approach, and invariants..."
                          defaultValue={item.user_approach || ''}
                          onChange={e => setNotesState(p => ({ ...p, [item.id]: { ...(p[item.id] || {}), approach: e.target.value } }))}
                          className="w-full text-xs"
                        />
                        <textarea
                          rows="1"
                          placeholder="Mistakes, bugs or edge cases to remember..."
                          defaultValue={item.mistakes_notes || ''}
                          onChange={e => setNotesState(p => ({ ...p, [item.id]: { ...(p[item.id] || {}), mistakes: e.target.value } }))}
                          className="w-full text-xs"
                        />
                      </div>
                    </div>

                    {/* Status Toggle Buttons */}
                    <div className="flex items-center justify-between pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        isSolved ? 'badge-success badge' : 'badge-warning badge'
                      }`}>
                        Status: {item.status}
                      </span>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleUpdateStatus(item.id, 'Attempted')}
                          className="px-2.5 py-1 text-xs rounded bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                        >
                          Attempted
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(item.id, 'Needs Revision')}
                          className="px-2.5 py-1 text-xs rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 font-semibold"
                        >
                          Needs Revision
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(item.id, 'Solved')}
                          className="px-3 py-1 text-xs rounded bg-emerald-600 text-white hover:bg-emerald-500 font-bold shadow"
                        >
                          ✓ Solved
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        <div className="lc-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100">All DSA Syllabus Practice Problems</h3>
          <div className="space-y-3">
            {allQuestions.map(q => (
              <div key={q.id} className="p-3.5 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400">
                      {q.topic}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400">{q.difficulty}</span>
                    {q.solve_count > 0 && <span className="badge badge-success text-[10px]">Solved {q.solve_count}x</span>}
                  </div>
                  <h4 className="text-sm font-bold text-slate-200">{q.title}</h4>
                  <p className="text-xs text-slate-400 line-clamp-1">{q.problem_statement}</p>
                </div>
                <div className="text-xs text-slate-400 font-mono shrink-0">
                  Time: {q.time_complexity} • Space: {q.space_complexity}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 5. ENGLISH SPEAKING IMPROVEMENT (30 MIN) -----------------

function EnglishSpeakingView({ englishToday, onRefresh, showToast }) {
  const [timerSeconds, setTimerSeconds] = useState(englishToday?.log?.time_spent_seconds || 0);
  const [timerRunning, setTimerRunning] = useState(false);
  const [notes, setNotes] = useState(englishToday?.log?.notes || '');
  const [history, setHistory] = useState([]);

  useEffect(() => {
    window.LastChanceAPI.getEnglishHistory().then(res => setHistory(res.history || [])).catch(() => {});
  }, []);

  useEffect(() => {
    let interval = null;
    if (timerRunning) {
      interval = setInterval(() => {
        setTimerSeconds(s => s + 1);
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [timerRunning]);

  const topic = englishToday?.topic;
  const isCompleted = englishToday?.log?.is_completed || false;

  const formatTimer = (totalSec) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleSaveLog = async (markComplete = false) => {
    try {
      await window.LastChanceAPI.saveEnglishLog({
        log_date: englishToday?.date || new Date().toISOString().split('T')[0],
        topic_id: topic?.id,
        time_spent_seconds: timerSeconds,
        is_completed: markComplete || (timerSeconds >= 1800),
        notes: notes
      });
      await onRefresh();
      showToast(markComplete ? '30-minute English speaking session saved as completed!' : 'Session progress saved!');
    } catch (e) {
      showToast('Failed to save log: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>English Speaking Improvement</h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Daily 30-minute speaking practice scheduled separately outside the 4-hour academic target.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-3 py-1 rounded-full">
            🔥 {englishToday?.streak_days || 0} Day Streak
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Daily Topic & Prompt */}
        <div className="lg:col-span-2 lc-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 uppercase tracking-wider">
                Today's Topic • {topic?.category || 'General'}
              </span>
              <h3 className="text-lg font-bold text-slate-100 mt-1">{topic?.title || 'Daily Speaking Practice'}</h3>
            </div>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
              isCompleted ? 'badge-success badge' : 'badge-warning badge'
            }`}>
              {isCompleted ? '✓ Completed Today' : 'Pending 30m'}
            </span>
          </div>

          <div className="p-3.5 rounded-lg border text-xs space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <div className="font-bold text-indigo-400">Objective:</div>
            <p className="text-slate-300 leading-relaxed">{topic?.objective}</p>
          </div>

          {/* Suggested Vocabulary */}
          {topic?.vocabulary?.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-xs font-bold text-slate-300">Suggested Vocabulary & Phrases:</div>
              <div className="flex flex-wrap gap-1.5">
                {topic.vocabulary.map((v, i) => (
                  <span key={i} className="code-pill text-xs font-semibold">{v}</span>
                ))}
              </div>
            </div>
          )}

          {/* Speaking Prompts */}
          {topic?.speaking_prompts?.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-300">Speaking Prompts & Questions to Answer Aloud:</div>
              <div className="space-y-1.5">
                {topic.speaking_prompts.map((p, i) => (
                  <div key={i} className="text-xs p-2 rounded bg-slate-800/40 border border-slate-700/50 text-slate-300 flex items-start space-x-2">
                    <span className="text-indigo-400 font-bold">{i + 1}.</span>
                    <span>{p}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Speech Notes & Observations */}
          <div className="space-y-1.5 pt-2">
            <label className="block text-xs font-bold text-slate-300">Speech Notes, Grammar & Fluency Observations:</label>
            <textarea
              rows="3"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Record points you discussed, pronunciation doubts, or vocabulary you used..."
              className="w-full text-xs"
            />
          </div>
        </div>

        {/* Right 1 Col: Speaking Timer & History */}
        <div className="space-y-6">
          {/* Speaking Timer Box */}
          <div className="lc-card p-5 space-y-4 text-center">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Practice Timer</h3>
            <div className="text-4xl font-black font-mono tracking-tight text-slate-100 py-2">
              {formatTimer(timerSeconds)}
            </div>
            <div className="text-xs text-slate-400 font-medium">Target: 30:00 minutes</div>

            <div className="flex items-center justify-center space-x-2 pt-2">
              <button
                onClick={() => setTimerRunning(!timerRunning)}
                className={`px-4 py-2 rounded-lg text-xs font-bold ${
                  timerRunning ? 'bg-amber-600 text-white' : 'btn-primary'
                }`}
              >
                {timerRunning ? '⏸️ Pause Timer' : '▶️ Start Speaking'}
              </button>
              <button
                onClick={() => { setTimerRunning(false); setTimerSeconds(0); }}
                className="px-3 py-2 rounded-lg text-xs font-medium btn-secondary"
              >
                Reset
              </button>
            </div>

            <div className="pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button
                onClick={() => handleSaveLog(true)}
                className="w-full py-2 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-500 shadow transition-smooth"
              >
                ✓ Mark 30m Practice Completed
              </button>
            </div>
          </div>

          {/* Recent History Table */}
          <div className="lc-card p-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Recent Practice Log</h4>
            <div className="space-y-2 text-xs max-h-48 overflow-y-auto pr-1">
              {history.length === 0 ? (
                <p className="text-[11px] text-slate-500 text-center py-4">No past logs recorded.</p>
              ) : (
                history.slice(0, 7).map((h, i) => (
                  <div key={i} className="p-2 rounded border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div>
                      <div className="font-semibold text-slate-300">{h.log_date}</div>
                      <div className="text-[10px] text-slate-400">{h.topic_title || 'Practice Session'}</div>
                    </div>
                    <div className="text-right">
                      <span className={`text-[10px] font-bold ${h.is_completed ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {Math.floor(h.time_spent_seconds / 60)} mins
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- 6. REVISION PLANNER VIEW -----------------

function RevisionPlannerView({ dates, onRefresh, showToast }) {
  const [revisionData, setRevisionData] = useState(null);

  useEffect(() => {
    window.LastChanceAPI.getRevision().then(res => setRevisionData(res)).catch(() => {});
  }, []);

  const weakTopics = revisionData?.weak_topics || [];
  const bufferSessions = revisionData?.buffer_sessions || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Revision Planner & Buffer Protection</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Systematic spaced review queue and the 7-day pre-exam protected revision buffer
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weak Topics Queue */}
        <div className="lc-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Weak / Low-Confidence Topics</h3>
              <p className="text-xs text-slate-400">Topics needing revision before first-pass deadline</p>
            </div>
            <span className="badge badge-warning">{weakTopics.length} Topics</span>
          </div>

          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {weakTopics.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No topics currently marked as weak. Great job!</p>
            ) : (
              weakTopics.map(t => (
                <div key={t.id} className="p-3 rounded-lg border space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: t.subject_color || '#4f46e5' }}>
                      {t.subject_name}
                    </span>
                    <span className="text-[10px] font-bold text-amber-400">{t.mastery_level}</span>
                  </div>
                  <div className="text-xs font-bold text-slate-200">{t.title}</div>
                  <div className="text-[10px] text-slate-400">Confidence Score: {t.lowest_confidence}/5</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 7-Day Protected Pre-Exam Buffer */}
        <div className="lc-card p-5 space-y-4">
          <div className="border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
              Protected 7-Day Buffer
            </span>
            <h3 className="text-sm font-bold text-slate-100 mt-1">
              Revision Buffer ({dates?.first_pass_deadline_str} to {dates?.first_exam_str})
            </h3>
            <p className="text-xs text-slate-400">
              Guarantees zero new syllabus topics are scheduled during the final 7 days before exams.
            </p>
          </div>

          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {bufferSessions.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">
                Buffer sessions will appear here as the final 7-day revision schedule is compiled.
              </p>
            ) : (
              bufferSessions.map((s, idx) => (
                <div key={idx} className="p-3 rounded-lg border space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex items-center justify-between text-xs font-bold text-indigo-400">
                    <span>{s.scheduled_date}</span>
                    <span className="text-white text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: s.subject_color }}>
                      {s.subject_name}
                    </span>
                  </div>
                  <div className="text-xs font-bold text-slate-200">{s.topic_title}</div>
                  <div className="text-[11px] text-slate-400">⏱️ {s.duration_minutes}m Revision</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- 7. EXTRA TIME VIEW -----------------

function ExtraTimeView({ onNavigate, onStartSession, showToast }) {
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    window.LastChanceAPI.getExtraTime().then(res => {
      setRecommendations(res.recommendations || []);
    }).catch(e => console.error(e));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Have Extra Time? Do This Next</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Workload-aware optional productivity recommendations prioritized after reviewing overdue tasks, weak topics, and daily targets.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.length === 0 ? (
          <div className="col-span-2 lc-card p-10 text-center space-y-2">
            <div className="text-3xl">☕</div>
            <h3 className="text-base font-bold text-slate-200">No Extra Work Recommended</h3>
            <p className="text-xs text-slate-400">
              All your daily commitments and review queues are satisfied. Get rest and sleep well to maintain high cognitive retention!
            </p>
          </div>
        ) : (
          recommendations.map((rec, idx) => (
            <div key={idx} className="lc-card p-5 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: rec.color || '#4f46e5' }}>
                    {rec.category}
                  </span>
                  <span className="text-xs font-mono text-slate-400">⏱️ {rec.estimated_minutes} mins</span>
                </div>
                <h4 className="text-sm font-bold text-slate-100">{rec.title}</h4>
                <p className="text-xs text-slate-300 leading-relaxed">{rec.reason}</p>
              </div>

              <div className="pt-2 border-t flex justify-end" style={{ borderColor: 'var(--border-color)' }}>
                {rec.action_type === 'DSA_NAV' && (
                  <button onClick={() => onNavigate('dsa')} className="btn-primary text-xs font-bold">
                    Open DSA Questions →
                  </button>
                )}
                {rec.action_type === 'ENGLISH_NAV' && (
                  <button onClick={() => onNavigate('english')} className="btn-primary text-xs font-bold">
                    Open English Practice →
                  </button>
                )}
                {rec.action_type === 'STUDY_TASK' && (
                  <button onClick={() => onStartSession({ id: rec.target_id, topic_title: rec.title, duration_minutes: rec.estimated_minutes })} className="btn-primary text-xs font-bold">
                    Start Catch-up Session →
                  </button>
                )}
                {rec.action_type === 'TOPIC_REVIEW' && (
                  <button onClick={() => onNavigate('courses')} className="btn-secondary text-xs font-bold">
                    Inspect in Syllabus →
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ----------------- 8. PROGRESS & ANALYTICS VIEW -----------------

function AnalyticsView({ feasibility, onRefresh, showToast }) {
  const [analyticsData, setAnalyticsData] = useState(null);

  useEffect(() => {
    window.LastChanceAPI.getAnalytics().then(res => setAnalyticsData(res)).catch(() => {});
  }, []);

  const subjectsStats = analyticsData?.subjects_stats || [];
  const dailyHistory = analyticsData?.daily_history || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Progress & Learning Analytics</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Real stored metrics: academic study time vs commitments, course completion, and workload trajectory
        </p>
      </div>

      {/* Feasibility Summary Banner */}
      {feasibility && (
        <div className="lc-card p-5 space-y-3 border-l-4 border-indigo-500">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Feasibility Status</span>
              <h3 className="text-base font-bold text-slate-100">{feasibility.status_label.replace('_', ' ')}</h3>
            </div>
            <span className="text-sm font-bold text-slate-200">
              Capacity Utilization: {feasibility.capacity_utilization_percent}%
            </span>
          </div>
          <p className="text-xs text-slate-300">{feasibility.warning_message}</p>
        </div>
      )}

      {/* Course Completion Breakdown */}
      <div className="lc-card p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-100">Course Completion by Topics</h3>
        <div className="space-y-3">
          {subjectsStats.map(s => {
            const pct = s.total_topics > 0 ? Math.round((s.mastered_topics / s.total_topics) * 100) : 0;
            return (
              <div key={s.id} className="space-y-1 text-xs">
                <div className="flex justify-between font-semibold">
                  <span style={{ color: s.color || '#4f46e5' }}>{s.code}: {s.name}</span>
                  <span className="text-slate-300">{s.mastered_topics} / {s.total_topics} topics ({pct}%)</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div className="h-2 rounded-full transition-smooth" style={{ width: `${pct}%`, backgroundColor: s.color || '#4f46e5' }}></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Daily Study Consistency */}
      <div className="lc-card p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-100">Recent Completed Study History (Last 14 Days)</h3>
        <div className="space-y-2 text-xs">
          {dailyHistory.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">No past study sessions completed yet.</p>
          ) : (
            dailyHistory.map((d, i) => (
              <div key={i} className="p-2.5 rounded border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <span className="font-bold text-slate-200">{d.scheduled_date}</span>
                <span className="text-slate-300">{d.tasks_count} tasks</span>
                <span className="font-mono text-indigo-400 font-bold">{d.total_actual_minutes} actual mins</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ----------------- 9. STUDY HISTORY VIEW -----------------

function StudyHistoryView({ showToast }) {
  const [historyItems, setHistoryItems] = useState([]);
  const [changeLogs, setChangeLogs] = useState([]);

  useEffect(() => {
    window.LastChanceAPI.getHistory().then(res => {
      setHistoryItems(res.history || []);
      setChangeLogs(res.change_logs || []);
    }).catch(e => console.error(e));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Study History & Audit Logs</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Historical record of all completed tasks, sessions, and schedule adaptations. Never overwritten.
        </p>
      </div>

      <div className="lc-card p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-100">Completed Sessions</h3>
        <div className="space-y-2 text-xs">
          {historyItems.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No study history recorded yet.</p>
          ) : (
            historyItems.map(item => (
              <div key={item.id} className="p-3 rounded-lg border space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-[10px] px-2 py-0.5 rounded" style={{ backgroundColor: item.subject_color || '#4f46e5' }}>
                    {item.subject_name}
                  </span>
                  <span className="text-slate-400 font-mono text-[11px]">{item.scheduled_date}</span>
                </div>
                <div className="font-bold text-slate-200">{item.topic_title}</div>
                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Actual: {item.actual_minutes}m (Planned: {item.duration_minutes}m)</span>
                  <span>Confidence: {item.confidence_rating}/5</span>
                </div>
                {item.notes && <p className="text-[11px] text-slate-300 italic pt-1">Notes: "{item.notes}"</p>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ----------------- 10. HANDOUT IMPORT VIEW -----------------

function HandoutImportView({ onRefresh, showToast }) {
  const [file, setFile] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [extractedData, setExtractedData] = useState(null);

  const handleUpload = async () => {
    if (!file) {
      showToast('Please select a file to import', 'error');
      return;
    }
    setParsing(true);
    try {
      const res = await window.LastChanceAPI.uploadSyllabus(file);
      setExtractedData(res.data);
      showToast('Syllabus text parsed successfully!', 'success');
    } catch (e) {
      showToast('Failed to parse syllabus: ' + e.message, 'error');
    } finally {
      setParsing(false);
    }
  };

  const handleCommit = async () => {
    if (!extractedData) return;
    try {
      await window.LastChanceAPI.commitSyllabus(extractedData);
      setExtractedData(null);
      setFile(null);
      await onRefresh();
      showToast('Imported syllabus committed to database!', 'success');
    } catch (e) {
      showToast('Failed to commit syllabus: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Handout & Syllabus Import</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Import course syllabus documents (PDF, TXT, MD) with automatic unit and topic extraction
        </p>
      </div>

      <div className="lc-card p-6 space-y-4">
        <div className="border-2 border-dashed rounded-xl p-8 text-center space-y-3" style={{ borderColor: 'var(--border-color)' }}>
          <div className="text-3xl">📥</div>
          <div className="text-sm font-bold text-slate-200">Select Syllabus Document</div>
          <p className="text-xs text-slate-400">Supported formats: PDF, TXT, Markdown (.md)</p>
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={e => setFile(e.target.files[0])}
            className="text-xs"
          />
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleUpload}
            disabled={!file || parsing}
            className="btn-primary text-xs font-bold"
          >
            {parsing ? 'Parsing Document...' : 'Upload & Parse Document'}
          </button>
        </div>

        {extractedData && (
          <div className="p-4 rounded-xl border space-y-3 mt-4" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <h3 className="text-sm font-bold text-slate-100">Parsed Syllabus Preview</h3>
            <div className="text-xs text-slate-300">
              <strong>Course:</strong> {extractedData.course_name} ({extractedData.course_code})
            </div>
            <div className="text-xs text-slate-400">
              Extracted {extractedData.units?.length || 0} Units.
            </div>
            <button onClick={handleCommit} className="btn-primary text-xs font-bold">
              Commit to Syllabus Database
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------- 11. SETTINGS VIEW -----------------

function SettingsView({ settings, onRefresh, showToast }) {
  const [formData, setFormData] = useState(settings || {});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setFormData(settings);
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await window.LastChanceAPI.updateSettings(formData);
      await onRefresh();
      showToast('Settings saved successfully!', 'success');
    } catch (e) {
      showToast('Failed to save settings: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleExportBackup = async () => {
    try {
      const data = await window.LastChanceAPI.exportBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `last_chance_backup_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      showToast('Backup exported successfully!', 'success');
    } catch (e) {
      showToast('Failed to export backup: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Application Settings</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Configure study targets, college timetables, special holiday breaks, and database backups.
        </p>
      </div>

      <div className="lc-card p-6 space-y-6">
        {/* Core Daily Targets */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">Core Daily Targets</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Academic Study Target (minutes):</label>
              <input
                type="number"
                value={formData.daily_academic_target_minutes || 240}
                onChange={e => setFormData({ ...formData, daily_academic_target_minutes: Number(e.target.value) })}
                className="w-full"
              />
              <span className="text-[11px] text-slate-500">Default: 240 mins (4 hours)</span>
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">English Speaking Target (minutes):</label>
              <input
                type="number"
                value={formData.english_speaking_target_minutes || 30}
                onChange={e => setFormData({ ...formData, english_speaking_target_minutes: Number(e.target.value) })}
                className="w-full"
              />
              <span className="text-[11px] text-slate-500">Tracked separately outside 240m</span>
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Daily DSA Compulsory Questions:</label>
              <input
                type="number"
                value={formData.daily_dsa_count || 2}
                onChange={e => setFormData({ ...formData, daily_dsa_count: Number(e.target.value) })}
                className="w-full"
              />
              <span className="text-[11px] text-slate-500">Default: 2 questions per day</span>
            </div>
          </div>
        </div>

        {/* College Commitments */}
        <div className="space-y-4 border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">College Timetable & Commitments</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Working Day Class Hours:</label>
              <input
                type="number"
                step="0.5"
                value={formData.college_working_day_hours || 3.0}
                onChange={e => setFormData({ ...formData, college_working_day_hours: Number(e.target.value) })}
                className="w-full"
              />
              <span className="text-[11px] text-slate-500">Default: 3.0 hours on working days (Mon-Fri)</span>
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Holiday Class Hours (When Marked):</label>
              <input
                type="number"
                step="0.5"
                value={formData.college_holiday_hours || 5.0}
                onChange={e => setFormData({ ...formData, college_holiday_hours: Number(e.target.value) })}
                className="w-full"
              />
              <span className="text-[11px] text-slate-500">Default: 5.0 hours for special dates</span>
            </div>
          </div>
        </div>

        {/* Special Holiday Break */}
        <div className="space-y-4 border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">Special Holiday Break</h3>
          <div className="p-3 rounded-lg border text-xs text-amber-300 bg-amber-500/10 border-amber-500/30">
            ⚠️ <strong>Duration Notice:</strong> 6 December to 11 December 2026 is 6 calendar days, not 7.
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Break Start Date:</label>
              <input
                type="date"
                value={formData.special_break_start || '2026-12-06'}
                onChange={e => setFormData({ ...formData, special_break_start: e.target.value })}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Break End Date:</label>
              <input
                type="date"
                value={formData.special_break_end || '2026-12-11'}
                onChange={e => setFormData({ ...formData, special_break_end: e.target.value })}
                className="w-full"
              />
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <input
              type="checkbox"
              id="seventh_day"
              checked={formData.special_break_include_7th_day || false}
              onChange={e => setFormData({ ...formData, special_break_include_7th_day: e.target.checked })}
            />
            <label htmlFor="seventh_day" className="text-slate-300 font-medium">
              Include missing 7th day (extend break through 12 December 2026)
            </label>
          </div>
        </div>

        {/* Timezone Setting */}
        <div className="space-y-2 border-t pt-4 text-xs" style={{ borderColor: 'var(--border-color)' }}>
          <label className="block text-slate-300 font-medium">Application Timezone:</label>
          <input
            type="text"
            value={formData.time_zone || 'Asia/Kolkata'}
            onChange={e => setFormData({ ...formData, time_zone: e.target.value })}
            className="w-full sm:w-1/2"
          />
          <span className="text-[11px] text-slate-500">Default: Asia/Kolkata (India Standard Time)</span>
        </div>

        {/* Save & Backup Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-5" style={{ borderColor: 'var(--border-color)' }}>
          <div className="flex space-x-2">
            <button onClick={handleExportBackup} className="btn-secondary text-xs">
              💾 Export JSON Backup
            </button>
          </div>
          <button onClick={handleSave} disabled={saving} className="btn-primary text-xs font-bold">
            {saving ? 'Saving Changes...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ----------------- FOCUS MODE MODAL -----------------

function FocusModeModal({ task, onClose, showToast }) {
  const [seconds, setSeconds] = useState(0);
  const [isRunning, setIsRunning] = useState(true);
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(4);

  useEffect(() => {
    let interval = null;
    if (isRunning) {
      interval = setInterval(() => setSeconds(s => s + 1), 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  const targetSec = (task.duration_minutes || 60) * 60;
  const remainingSec = Math.max(0, targetSec - seconds);

  const formatTime = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleFinish = async () => {
    try {
      const actualMinutes = Math.max(1, Math.round(seconds / 60));
      await window.LastChanceAPI.completeTask(task.id, {
        status: 'COMPLETED',
        completion_percentage: 100,
        actual_minutes: actualMinutes,
        confidence_rating: confidence,
        notes: notes
      });
      showToast('Focus session logged and task marked complete!', 'success');
      onClose();
    } catch (e) {
      showToast('Failed to log session: ' + e.message, 'error');
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-dialog p-6 space-y-6 text-center max-w-lg">
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Focus Mode</span>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">✕</button>
        </div>

        <div>
          <h3 className="text-lg font-bold text-slate-100">{task.topic_title}</h3>
          <p className="text-xs text-slate-400 mt-1">Planned Target: {task.duration_minutes} minutes</p>
        </div>

        <div className="p-6 rounded-2xl border text-center space-y-2" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
          <div className="text-5xl font-black font-mono tracking-tight text-indigo-400">
            {formatTime(remainingSec)}
          </div>
          <div className="text-xs text-slate-400">
            Elapsed: {formatTime(seconds)}
          </div>
        </div>

        <div className="flex items-center justify-center space-x-3">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`px-5 py-2.5 rounded-lg text-xs font-bold ${
              isRunning ? 'bg-amber-600 text-white' : 'btn-primary'
            }`}
          >
            {isRunning ? '⏸️ Pause' : '▶️ Resume'}
          </button>
        </div>

        <div className="space-y-2 text-left text-xs">
          <label className="block text-slate-300 font-medium">Session Observations / Notes:</label>
          <textarea
            rows="2"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Record key derivations, formulas or recall notes..."
            className="w-full text-xs"
          />
        </div>

        <div className="flex justify-end space-x-2 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
          <button onClick={onClose} className="btn-secondary text-xs">Close</button>
          <button onClick={handleFinish} className="btn-primary text-xs font-bold">
            ✓ Complete & Save Session
          </button>
        </div>
      </div>
    </div>
  );
}

// Render Application into Root
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
