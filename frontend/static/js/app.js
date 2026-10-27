// Last Chance — Personal Study Planner & Exam Preparation System
// Local-First, High-Contrast Accessible Design System
const { useState, useEffect, useMemo, useRef } = React;

// Utility formatters
function formatMins(mins) {
  if (!mins || mins <= 0) return '0 mins';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m} mins`;
  if (m === 0) return `${h} hr${h > 1 ? 's' : ''}`;
  return `${h} hr${h > 1 ? 's' : ''} ${m} min${m > 1 ? 's' : ''}`;
}

function formatTimeSec(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}


function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [theme, setTheme] = useState(localStorage.getItem('lastchance_theme') || 'dark');
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
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
  const [studyTotals, setStudyTotals] = useState(null);

  // Global Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchDropdownOpen, setSearchDropdownOpen] = useState(false);

  // Modal States
  const [focusSessionTask, setFocusSessionTask] = useState(null);
  const [isFocusModalOpen, setIsFocusModalOpen] = useState(false);
  const [isFavoritesModalOpen, setIsFavoritesModalOpen] = useState(false);
  const [isSessionHistoryModalOpen, setIsSessionHistoryModalOpen] = useState(false);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const APPRECIATION_MESSAGES = [
    "Great work! One more step forward.",
    "Excellent consistency. Keep going!",
    "You completed this shift. Build on that progress.",
    "Small steps every day create real progress.",
    "Outstanding focus! Every minute of honest practice adds up.",
    "Discipline today creates freedom tomorrow.",
    "Your parents and family will be proud of your hard work.",
    "Patience and perseverance lead to true mastery.",
    "Faith in your preparation will conquer exam fear."
  ];

  const showAppreciation = (customMsg) => {
    const msg = customMsg || APPRECIATION_MESSAGES[Math.floor(Math.random() * APPRECIATION_MESSAGES.length)];
    setToast({ message: msg, type: 'appreciation' });
    setTimeout(() => setToast(null), 4500);
  };

  // Synchronize Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('lastchance_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Real-Time IST Clock
  useEffect(() => {
    const fetchTime = async () => {
      try {
        const t = await window.LastChanceAPI.getTime();
        setTimeData(t);
      } catch (e) {
        const now = new Date();
        setTimeData({
          formatted_date: now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Kolkata' }),
          formatted_time: now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true, timeZone: 'Asia/Kolkata' }),
          date_str: now.toISOString().split('T')[0],
          timezone: 'Asia/Kolkata'
        });
      }
    };
    fetchTime();
    const interval = setInterval(fetchTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Global Search Handler
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults(null);
      setSearchDropdownOpen(false);
      return;
    }
    const delayDebounce = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await window.LastChanceAPI.globalSearch(searchQuery.trim());
        setSearchResults(res);
        setSearchDropdownOpen(true);
      } catch (e) {
        console.error(e);
      } finally {
        setIsSearching(false);
      }
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [dInfo, fInfo, stg, subjs, tSched, quote, dsa, eng, totals] = await Promise.all([
        window.LastChanceAPI.getDates().catch(() => null),
        window.LastChanceAPI.getFeasibility().catch(() => null),
        window.LastChanceAPI.getSettings().catch(() => null),
        window.LastChanceAPI.getSubjects().catch(() => []),
        window.LastChanceAPI.getTodaySchedule().catch(() => null),
        window.LastChanceAPI.getDailyQuote().catch(() => null),
        window.LastChanceAPI.getDailyDSA().catch(() => null),
        window.LastChanceAPI.getEnglishToday().catch(() => null),
        window.LastChanceAPI.getStudyTotals().catch(() => null)
      ]);
      setDates(dInfo);
      setFeasibility(fInfo);
      setSettings(stg);
      setSubjects(subjs);
      setTodaySchedule(tSched);
      if (quote) setTodayQuote(quote.quote);
      if (dsa) setDailyDSA(dsa);
      if (eng) setEnglishToday(eng);
      if (totals) setStudyTotals(totals);
    } catch (err) {
      console.error(err);
      showToast('Data load notice: ' + err.message, 'info');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const refreshAll = async () => {
    try {
      const [dInfo, fInfo, subjs, tSched, quote, dsa, eng, totals] = await Promise.all([
        window.LastChanceAPI.getDates().catch(() => null),
        window.LastChanceAPI.getFeasibility().catch(() => null),
        window.LastChanceAPI.getSubjects().catch(() => []),
        window.LastChanceAPI.getTodaySchedule().catch(() => null),
        window.LastChanceAPI.getDailyQuote().catch(() => null),
        window.LastChanceAPI.getDailyDSA().catch(() => null),
        window.LastChanceAPI.getEnglishToday().catch(() => null),
        window.LastChanceAPI.getStudyTotals().catch(() => null)
      ]);
      if (dInfo) setDates(dInfo);
      if (fInfo) setFeasibility(fInfo);
      if (subjs) setSubjects(subjs);
      if (tSched) setTodaySchedule(tSched);
      if (quote) setTodayQuote(quote.quote);
      if (dsa) setDailyDSA(dsa);
      if (eng) setEnglishToday(eng);
      if (totals) setStudyTotals(totals);
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

  // 12 Navigation Items
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⚡' },
    { id: 'timetable', label: 'Daily Work', icon: '📋' },
    { id: 'dsa', label: 'Daily DSA', icon: '💻' },
    { id: 'handouts', label: 'Handouts', icon: '📄' },
    { id: 'redo', label: 'Redo Queue', icon: '🔁' },
    { id: 'english', label: 'English Speaking', icon: '🗣️' },
    { id: 'analytics', label: 'Study Analytics', icon: '📊' }
  ];

  const academicDone = todaySchedule?.plan?.academic_completed_minutes || todaySchedule?.academic_completed_minutes || 0;
  const academicTarget = todaySchedule?.plan?.academic_target_minutes || todaySchedule?.academic_target_minutes || 240;
  const dsaDone = dailyDSA?.solved_count || 0;
  const englishDone = englishToday?.log?.is_completed || false;

  return (
    <div className="min-h-screen flex flex-col md:flex-row" style={{ backgroundColor: 'var(--bg-page)', color: 'var(--text-primary)' }}>
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3.5 rounded-xl shadow-2xl border flex items-center space-x-3 transition-smooth ${
          toast.type === 'appreciation' ? 'appreciation-toast' :
          toast.type === 'error' ? 'badge-error' :
          toast.type === 'success' ? 'badge-success' : 'badge-info'
        }`} style={{
          backgroundColor: toast.type === 'appreciation' ? 'var(--bg-card-elevated)' : undefined,
          borderColor: toast.type === 'appreciation' ? '#6366f1' : undefined
        }}>
          <span className="text-xl">{toast.type === 'appreciation' ? '🌟' : toast.type === 'error' ? '⚠️' : toast.type === 'success' ? '✓' : 'ℹ️'}</span>
          <div>
            {toast.type === 'appreciation' && (
              <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Consistency Milestone</div>
            )}
            <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{toast.message}</span>
          </div>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 shrink-0 flex flex-col border-r" style={{ backgroundColor: 'var(--bg-sidebar)', borderColor: 'var(--border-color)' }}>
        {/* Branding */}
        <div className="p-4 border-b flex items-center justify-center" style={{ borderColor: 'var(--border-color)' }}>
          <img
            src="/static/assets/logo.png"
            alt="Last Chance — Small Steps Big Results"
            className="brand-logo-img"
            style={{ width: '150px', height: 'auto', maxHeight: '54px', objectFit: 'contain' }}
          />
        </div>

        {/* Navigation Links */}
        <nav className="p-2.5 space-y-1 flex-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-smooth text-left ${
                  isActive ? 'shadow-sm' : 'hover:opacity-80'
                }`}
                style={{
                  backgroundColor: isActive ? 'var(--btn-primary-bg)' : 'transparent',
                  color: isActive ? '#ffffff' : 'var(--text-secondary)'
                }}
              >
                <span className="text-base">{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                {item.id === 'dsa' && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    dsaDone >= 2 ? 'bg-emerald-500 text-white' : 'bg-slate-700 text-slate-200'
                  }`}>
                    {dsaDone}/2
                  </span>
                )}
                {item.id === 'english' && englishDone && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-emerald-500 text-white">
                    ✓
                  </span>
                )}
                {item.id === 'dashboard' && todaySchedule?.overdue_count > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-rose-500 text-white">
                    {todaySchedule.overdue_count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Total Academic Hours Studied Sidebar Pill */}
        <div className="p-3 m-2.5 rounded-lg border text-xs space-y-2" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div className="flex items-center justify-between">
            <span className="font-semibold" style={{ color: 'var(--text-muted)' }}>Academic Total:</span>
            <span className="font-bold text-indigo-400 font-mono">
              {studyTotals?.total_academic_hours || '0h 0m'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-semibold" style={{ color: 'var(--text-muted)' }}>English Streak:</span>
            <span className="font-bold text-amber-500">🔥 {englishToday?.streak_days || 0}d</span>
          </div>
          <div className="pt-1 border-t flex items-center justify-between text-[11px]" style={{ borderColor: 'var(--border-color)' }}>
            <span style={{ color: 'var(--text-muted)' }}>First Exam:</span>
            <span className="font-bold text-rose-400">Nov 26 ({dates?.days_to_exam || 0}d left)</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header Bar */}
        <header className="px-5 py-3 border-b flex flex-wrap items-center justify-between gap-3 sticky top-0 z-30" style={{ backgroundColor: 'var(--bg-header)', borderColor: 'var(--border-color)', backdropFilter: 'blur(8px)' }}>
          <div className="flex items-center space-x-4">
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
          </div>

          <div className="flex items-center space-x-2.5 ml-auto">
            {/* Quick Metrics */}
            <div className="hidden sm:flex items-center space-x-2 text-xs">
              <div className="px-2.5 py-1 rounded-md border font-medium flex items-center space-x-1.5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <span>📖 Academic:</span>
                <strong style={{ color: 'var(--text-primary)' }}>{academicDone}/{academicTarget}m</strong>
              </div>
              <div className="px-2.5 py-1 rounded-md border font-medium flex items-center space-x-1.5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <span>💻 DSA:</span>
                <strong style={{ color: 'var(--text-primary)' }}>{dsaDone}/2</strong>
              </div>
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-1.5 px-2.5 rounded-lg border text-xs font-semibold transition-smooth"
              style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              title="Toggle Light / Dark Theme"
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>

            <button
              onClick={refreshAll}
              className="p-1.5 px-2.5 rounded-lg border text-xs transition-smooth"
              style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              title="Refresh Data"
            >
              🔄
            </button>
          </div>
        </header>

        {/* View Router */}
        <main className="p-5 flex-1 overflow-y-auto max-w-7xl w-full mx-auto space-y-6">
          {activeTab === 'dashboard' && (
            <DashboardView
              todaySchedule={todaySchedule}
              dates={dates}
              timeData={timeData}
              feasibility={feasibility}
              todayQuote={todayQuote}
              dailyDSA={dailyDSA}
              englishToday={englishToday}
              studyTotals={studyTotals}
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              onNavigate={(tab) => setActiveTab(tab)}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
              onOpenSessionHistory={() => setIsSessionHistoryModalOpen(true)}
              onOpenFavorites={() => setIsFavoritesModalOpen(true)}
            />
          )}

          {activeTab === 'timetable' && (
            <TimetableView
              dates={dates}
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
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
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'courses' && (
            <CoursesUnitsView
              subjects={subjects}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'handouts' && (
            <HandoutsView
              subjects={subjects}
              showToast={showToast}
            />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsView
              feasibility={feasibility}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'wasted_time' && (
            <WastedTimeView
              dates={dates}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'dsa' && (
            <DailyDSAView
              dailyDSA={dailyDSA}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'redo' && (
            <RedoQueueView
              onStartSession={(task) => {
                setFocusSessionTask(task);
                setIsFocusModalOpen(true);
              }}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'english' && (
            <EnglishSpeakingView
              englishToday={englishToday}
              onRefresh={refreshAll}
              showToast={showToast}
              showAppreciation={showAppreciation}
            />
          )}

          {activeTab === 'revision' && (
            <RevisionPlannerView
              dates={dates}
              onRefresh={refreshAll}
              showToast={showToast}
            />
          )}

          {activeTab === 'history' && (
            <StudyHistoryView
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
          showAppreciation={showAppreciation}
        />
      )}

      {/* Favorite Quotes Modal */}
      {isFavoritesModalOpen && (
        <FavoriteQuotesModal
          onClose={() => setIsFavoritesModalOpen(false)}
          showToast={showToast}
        />
      )}

      {isAuthModalOpen && (
        <AuthModal
          currentUser={currentUser}
          onLoginSuccess={(user) => {
            setCurrentUser(user);
            setIsAuthModalOpen(false);
            showToast(`Welcome back, ${user.username}!`, 'success');
          }}
          onLogout={() => {
            localStorage.removeItem('lc_token');
            setCurrentUser(null);
            setIsAuthModalOpen(false);
            showToast('Logged out successfully.', 'info');
          }}
          onClose={() => setIsAuthModalOpen(false)}
          showToast={showToast}
        />
      )}

      {/* Session History Audit Modal */}
      {isSessionHistoryModalOpen && (
        <SessionHistoryModal
          onClose={() => setIsSessionHistoryModalOpen(false)}
        />
      )}
    </div>
  );
}


function DashboardView({
  todaySchedule,
  dates,
  timeData,
  feasibility,
  todayQuote,
  dailyDSA,
  englishToday,
  studyTotals,
  onStartSession,
  onNavigate,
  onRefresh,
  showToast,
  showAppreciation
}) {
  const [redoCount, setRedoCount] = useState(0);
  const [dsaTopics, setDsaTopics] = useState([]);
  const [autoRescheduling, setAutoRescheduling] = useState(false);

  useEffect(() => {
    window.LastChanceAPI.getDSATopics().then(res => {
      setDsaTopics(res.topics || []);
    }).catch(() => {});
    window.LastChanceAPI.getRedoTasks('PENDING').then(res => {
      setRedoCount(res.count || (res.redo_tasks || []).length || 0);
    }).catch(() => {});
  }, []);

  const plan = todaySchedule?.plan || {};
  const shifts = todaySchedule?.shifts || [];
  const wrapup = todaySchedule?.wrapup || null;
  const overdueCount = todaySchedule?.overdue_count || 0;

  const academicDone = plan.academic_completed_minutes || 0;
  const academicTarget = plan.academic_target_minutes || 240;
  const academicPct = Math.min(100, Math.round((academicDone / academicTarget) * 100));
  const academicRemaining = Math.max(0, academicTarget - academicDone);

  const shiftsCompleted = shifts.filter(s => s.status === 'COMPLETED').length;
  const totalShiftsCount = shifts.length;

  // Next recommended task: first non-completed shift or wrapup
  const nextShift = shifts.find(s => s.status !== 'COMPLETED') || (wrapup && wrapup.status !== 'COMPLETED' ? wrapup : null);

  const dsaSolved = dsaTopics.filter(t => t.status === 'Completed').length || dailyDSA?.solved_count || 0;
  const englishCompleted = englishToday?.log?.is_completed || false;
  const englishMins = englishToday?.log?.actual_minutes || (englishToday?.log?.time_spent_seconds ? Math.floor(englishToday.log.time_spent_seconds / 60) : 0);

  const handleQuickCompleteShift = async (shift, addToRedo = false) => {
    try {
      await window.LastChanceAPI.completeShift(shift.id, {
        actual_minutes: shift.duration_minutes || 45,
        confidence_rating: 4,
        notes: 'Completed on schedule',
        add_to_redo: addToRedo,
        redo_reason: addToRedo ? 'Added to Redo queue for revision' : null
      });
      await onRefresh();
      if (addToRedo) {
        showToast('Shift completed and added to Redo queue!', 'success');
      } else {
        showAppreciation("Excellent work! You completed this academic shift. Build on that progress.");
      }
    } catch (e) {
      showToast('Failed to complete shift: ' + e.message, 'error');
    }
  };

  const handleQuickCompleteWrapup = async () => {
    if (!wrapup) return;
    try {
      await window.LastChanceAPI.completeShift(wrapup.id, {
        actual_minutes: 15,
        confidence_rating: 5,
        notes: 'Wrap-up and active recall completed'
      });
      await onRefresh();
      showAppreciation("Great consistency! Daily wrap-up completed.");
    } catch (e) {
      showToast('Failed to complete wrap-up: ' + e.message, 'error');
    }
  };

  const handleAutoReschedule = async () => {
    setAutoRescheduling(true);
    try {
      const res = await window.LastChanceAPI.autoReschedule();
      await onRefresh();
      showToast(`Rescheduled ${res.rescheduled_count || 0} overdue tasks to upcoming slots without losing history.`, 'success');
    } catch (e) {
      showToast('Failed to auto-reschedule: ' + e.message, 'error');
    } finally {
      setAutoRescheduling(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* SECTION A: GREETING & DAILY CONTEXT */}
      <div className="p-4 sm:p-5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xl">🏔️</span>
            <h1 className="text-lg sm:text-xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Welcome back, Aman!
            </h1>
          </div>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            {dates?.formatted_date || timeData?.formatted_date || 'Today'} • <span className="font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>{timeData?.formatted_time || ''} IST</span>
          </p>
        </div>

        {/* Compact Daily Target Summary */}
        <div className="sm:text-right space-y-1.5 shrink-0">
          <div className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            Daily Academic Target: <strong className="text-indigo-400 font-bold">4h (240 mins)</strong>
          </div>
          <div className="flex items-center sm:justify-end space-x-2 text-xs">
            <span className="font-bold text-emerald-400 font-mono">{academicDone}m studied</span>
            <span style={{ color: 'var(--text-muted)' }}>•</span>
            <span className="font-bold font-mono" style={{ color: academicRemaining > 0 ? '#f59e0b' : '#10b981' }}>
              {academicRemaining > 0 ? `${academicRemaining}m remaining` : 'Target Met! 🎉'}
            </span>
          </div>
          <div className="w-full sm:w-48 bg-slate-800 rounded-full h-2 overflow-hidden border" style={{ borderColor: 'var(--border-color)' }}>
            <div
              className="h-full rounded-full transition-smooth"
              style={{
                width: `${academicPct}%`,
                backgroundColor: academicPct >= 100 ? '#10b981' : '#f59e0b'
              }}
            ></div>
          </div>
        </div>
      </div>

      {/* SECTION B: PROMINENT QUOTE OF THE DAY HERO (Mountain Sunrise Design - ZERO HOVER EFFECT) */}
      {todayQuote && (
        <div className="quote-hero-card p-5 sm:p-6 relative flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-md">
          <div className="space-y-2 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-500 border border-amber-500/35 uppercase tracking-widest font-mono">
                🌅 Quote of the Day • {todayQuote.category || 'Discipline'}
              </span>
              <span className="text-[11px] font-mono text-slate-400">• Stable in IST for {dates?.today_str || 'today'}</span>
            </div>
            <blockquote className="text-base sm:text-lg md:text-xl font-bold tracking-tight leading-snug" style={{ color: 'var(--text-primary)' }}>
              “{todayQuote.quote_text}”
            </blockquote>
            <div className="flex items-center space-x-3 text-xs">
              <span className="font-bold text-amber-500">— {todayQuote.author || 'Unknown'}</span>
              {todayQuote.context && (
                <span className="italic text-[11px] hidden sm:inline" style={{ color: 'var(--text-muted)' }}>• {todayQuote.context}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Overdue Banner if overdue tasks exist */}
      {overdueCount > 0 && (
        <div className="p-3.5 rounded-xl border border-rose-500/30 flex items-center justify-between gap-3 text-xs" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)' }}>
          <div className="flex items-center space-x-2">
            <span className="text-lg">⚠️</span>
            <span className="font-semibold text-rose-400">
              {overdueCount} study shift{overdueCount > 1 ? 's' : ''} from previous days need attention.
            </span>
          </div>
          <button
            onClick={handleAutoReschedule}
            disabled={autoRescheduling}
            className="btn-primary text-xs font-bold py-1 px-3 shrink-0"
          >
            {autoRescheduling ? 'Rescheduling...' : 'Auto-Reschedule →'}
          </button>
        </div>
      )}

      {/* SECTION C: TODAY'S STUDY TASKS — THE MAIN PRIORITY */}
      <div className="space-y-4">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-2.5" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Today's Mission
              </h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 font-mono">
                {shiftsCompleted} / {totalShiftsCount} Completed
              </span>
            </div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Five 45-minute academic shifts + 15-minute active recall wrap-up.
            </p>
          </div>
          <button
            onClick={() => onNavigate('timetable')}
            className="btn-secondary text-xs font-semibold py-1 px-3 self-start sm:self-center"
          >
            Full 25-Day Timetable →
          </button>
        </div>

        {/* Highlighted NEXT RECOMMENDED TASK */}
        {nextShift && nextShift.status !== 'COMPLETED' && (
          <div className="mission-card-next p-4 sm:p-5 rounded-xl space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded bg-amber-500 text-slate-950 font-mono">
                🚀 Current Focus • Shift {nextShift.shift_number || (nextShift.is_wrapup ? 'Wrap-up' : 1)}
              </span>
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded border border-amber-500/40 text-amber-400">
                ⏱️ {nextShift.remaining_minutes || nextShift.duration_minutes || 45} mins
              </span>
            </div>

            <div>
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                {nextShift.subject_code || 'Academic Course'} • {nextShift.unit_name || 'Unit Study'}
              </span>
              <h3 className="text-base sm:text-lg font-black mt-0.5" style={{ color: 'var(--text-primary)' }}>
                {nextShift.topic_title || nextShift.task_description}
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button
                onClick={() => onStartSession(nextShift)}
                className="btn-primary text-xs font-bold py-2 px-4 flex items-center space-x-1.5 shadow-md"
              >
                <span>▶</span>
                <span>Start Shift Focus</span>
              </button>
              <button
                onClick={() => handleQuickCompleteShift(nextShift, false)}
                className="btn-secondary text-xs font-semibold py-2 px-3"
              >
                ✓ Complete
              </button>
              <button
                onClick={() => handleQuickCompleteShift(nextShift, true)}
                className="btn-secondary text-xs font-semibold py-2 px-3 text-amber-400 hover:text-amber-300"
                title="Complete and add to Redo queue for spaced repetition"
              >
                ✓ + 🔁 Complete & Add to Redo
              </button>
            </div>
          </div>
        )}

        {/* REST OF THE DAY'S SHIFTS LIST */}
        <div className="space-y-2.5">
          {shifts.map((shift, idx) => {
            const isCompleted = shift.status === 'COMPLETED';
            const isCurrent = nextShift && nextShift.id === shift.id;
            return (
              <div
                key={shift.id || idx}
                className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-smooth ${
                  isCompleted ? 'opacity-70' : ''
                }`}
                style={{
                  backgroundColor: 'var(--bg-card)',
                  borderColor: isCurrent ? 'var(--border-focus)' : 'var(--border-color)'
                }}
              >
                <div className="flex items-start sm:items-center space-x-3 min-w-0">
                  <div className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center font-bold text-xs font-mono ${
                    isCompleted ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-800 text-slate-300 border border-slate-700'
                  }`}>
                    {isCompleted ? '✓' : shift.shift_number || (idx + 1)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      <span className="font-bold text-indigo-400">{shift.subject_code}</span>
                      <span>•</span>
                      <span>{shift.unit_name || 'Unit'}</span>
                      <span>•</span>
                      <span>{shift.duration_minutes || 45} mins</span>
                    </div>
                    <div className="font-bold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                      {shift.topic_title || shift.task_description}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 self-end sm:self-center shrink-0">
                  {isCompleted ? (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-bold border border-emerald-500/30">
                      Completed ✓
                    </span>
                  ) : (
                    <>
                      <button
                        onClick={() => onStartSession(shift)}
                        className="btn-secondary text-xs font-semibold py-1.5 px-3"
                      >
                        Start Focus
                      </button>
                      <button
                        onClick={() => handleQuickCompleteShift(shift, false)}
                        className="btn-secondary text-xs font-semibold py-1.5 px-2.5"
                        title="Mark Complete"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => handleQuickCompleteShift(shift, true)}
                        className="btn-secondary text-xs font-semibold py-1.5 px-2.5 text-amber-400"
                        title="Complete & Add to Redo"
                      >
                        🔁
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}

          {/* Daily 15m Wrap-up shift */}
          {wrapup && (
            <div
              className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                wrapup.status === 'COMPLETED' ? 'opacity-70' : ''
              }`}
              style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
            >
              <div className="flex items-center space-x-3">
                <div className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center font-bold text-xs ${
                  wrapup.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {wrapup.status === 'COMPLETED' ? '✓' : '📝'}
                </div>
                <div>
                  <div className="text-[11px] font-bold text-amber-400 uppercase">
                    Shift 6 • Wrap-up (15 mins)
                  </div>
                  <div className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                    Active Recall & Daily Summary
                  </div>
                </div>
              </div>

              <div className="self-end sm:self-center">
                {wrapup.status === 'COMPLETED' ? (
                  <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-bold border border-emerald-500/30">
                    Completed ✓
                  </span>
                ) : (
                  <button
                    onClick={handleQuickCompleteWrapup}
                    className="btn-secondary text-xs font-semibold py-1.5 px-3"
                  >
                    ✓ Complete Wrap-up
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SECTION D: COMPACT PROGRESS OVERVIEW */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          Daily Progress Overview
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Card 1: Academic Study */}
          <div className="p-3.5 rounded-xl border space-y-1.5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] uppercase font-bold text-indigo-400 block">📖 Academic Study</span>
            <div className="text-base sm:text-lg font-black font-mono" style={{ color: 'var(--text-primary)' }}>
              {academicDone} / {academicTarget}m
            </div>
            <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {academicPct}% of 4h commitment
            </div>
          </div>

          {/* Card 2: DSA Questions */}
          <div className="p-3.5 rounded-xl border space-y-1.5 cursor-pointer hover:border-emerald-500/40 transition-smooth"
               onClick={() => onNavigate('dsa')}
               style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] uppercase font-bold text-emerald-400 block">💻 Daily DSA</span>
            <div className="text-base sm:text-lg font-black font-mono text-emerald-400">
              {dsaSolved} / 2 Solved
            </div>
            <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Outside 4h study target →
            </div>
          </div>

          {/* Card 3: English Speaking */}
          <div className="p-3.5 rounded-xl border space-y-1.5 cursor-pointer hover:border-amber-500/40 transition-smooth"
               onClick={() => onNavigate('english')}
               style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] uppercase font-bold text-amber-400 block">🗣️ English Speaking</span>
            <div className="text-base sm:text-lg font-black font-mono text-amber-400">
              {englishMins} / 30m
            </div>
            <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {englishCompleted ? 'Completed today ✓' : 'Practice speaking →'}
            </div>
          </div>

          {/* Card 4: Redo Queue */}
          <div className="p-3.5 rounded-xl border space-y-1.5 cursor-pointer hover:border-rose-500/40 transition-smooth"
               onClick={() => onNavigate('redo')}
               style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] uppercase font-bold text-rose-400 block">🔁 Redo Queue</span>
            <div className="text-base sm:text-lg font-black font-mono text-rose-400">
              {redoCount} Queued
            </div>
            <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Spaced repetition list →
            </div>
          </div>
        </div>
      </div>

      {/* SECTION E: HELPFUL NEXT ACTION */}
      <div className="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <div className="flex items-center space-x-3">
          <span className="text-xl">💡</span>
          <div>
            <span className="font-bold text-amber-500 uppercase tracking-wider text-[10px] block">Helpful Next Step</span>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              {nextShift
                ? `Resume Shift ${nextShift.shift_number || 1}: ${nextShift.topic_title || nextShift.task_description} (${nextShift.remaining_minutes || 45} mins)`
                : 'All scheduled shifts completed for today! Review Redo queue or practice DSA.'}
            </span>
          </div>
        </div>
        {nextShift && (
          <button
            onClick={() => onStartSession(nextShift)}
            className="btn-primary text-xs font-bold py-1.5 px-4 shrink-0"
          >
            Start Now →
          </button>
        )}
      </div>
    </div>
  );
}


function TimetableView({ dates, onStartSession, onRefresh, showToast, showAppreciation }) {
  const [activeSubTab, setActiveSubTab] = useState('daily_plan'); // 'daily_plan' | 'rescheduled' | 'import_review'
  const [selectedDate, setSelectedDate] = useState('2026-10-27');
  const [daySchedule, setDaySchedule] = useState(null);
  const [loadingDay, setLoadingDay] = useState(false);
  const [courseFilter, setCourseFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Rescheduled list state
  const [rescheduledList, setRescheduledList] = useState([]);
  const [loadingRescheduled, setLoadingRescheduled] = useState(false);

  // Timetable import preview state
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);

  // Action modals
  const [partialTask, setPartialTask] = useState(null);
  const [rescheduleTask, setRescheduleTask] = useState(null);

  // All 25 dates from 27 Oct to 20 Nov 2026
  const timetableDates = useMemo(() => {
    const list = [];
    const start = new Date(2026, 9, 27); // Oct 27
    const end = new Date(2026, 10, 20);  // Nov 20
    const cur = new Date(start);
    while (cur <= end) {
      const y = cur.getFullYear();
      const m = String(cur.getMonth() + 1).padStart(2, '0');
      const d = String(cur.getDate()).padStart(2, '0');
      const dStr = `${y}-${m}-${d}`;
      const dayName = cur.toLocaleDateString('en-US', { weekday: 'short' });
      const monthName = cur.toLocaleDateString('en-US', { month: 'short' });
      list.push({ date: dStr, label: `${dayName} ${d} ${monthName}`, day: d, month: monthName });
      cur.setDate(cur.getDate() + 1);
    }
    return list;
  }, []);

  const loadDaySchedule = async (dStr) => {
    setLoadingDay(true);
    try {
      const res = await window.LastChanceAPI.getScheduleDay(dStr);
      setDaySchedule(res);
    } catch (e) {
      console.error(e);
      showToast('Failed to load day schedule: ' + e.message, 'error');
    } finally {
      setLoadingDay(false);
    }
  };

  const loadRescheduledTasks = async () => {
    setLoadingRescheduled(true);
    try {
      const res = await window.LastChanceAPI.getRescheduledTasks();
      setRescheduledList(res.rescheduled_tasks || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingRescheduled(false);
    }
  };

  const loadImportPreview = async () => {
    try {
      const res = await window.LastChanceAPI.previewTimetable();
      setImportPreview(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadDaySchedule(selectedDate);
  }, [selectedDate]);

  useEffect(() => {
    if (activeSubTab === 'rescheduled') {
      loadRescheduledTasks();
    } else if (activeSubTab === 'import_review') {
      loadImportPreview();
    }
  }, [activeSubTab]);

  const handleQuickComplete = async (shift) => {
    try {
      await window.LastChanceAPI.completeShift(shift.id, {
        actual_minutes: shift.duration_minutes || 45,
        confidence_rating: 4,
        notes: 'Completed in study plan view'
      });
      await loadDaySchedule(selectedDate);
      onRefresh();
      showAppreciation("Outstanding progress! Study shift marked complete.");
    } catch (e) {
      showToast('Failed to complete shift: ' + e.message, 'error');
    }
  };

  const handleCompleteAndRedo = async (shift) => {
    try {
      await window.LastChanceAPI.completeShift(shift.id, {
        actual_minutes: shift.duration_minutes || 45,
        confidence_rating: 3,
        notes: 'Completed and scheduled for redo',
        add_to_redo: true,
        redo_reason: 'Flagged for spaced repetition'
      });
      await loadDaySchedule(selectedDate);
      onRefresh();
      showAppreciation("Shift completed and queued into Redo / Practice Again!");
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleAddCompletedToRedo = async (shift) => {
    try {
      await window.LastChanceAPI.addRedoTask({
        topic_name: shift.task_description || shift.topic_title,
        course_name: shift.subject_name || 'Discrete Structures',
        unit_number: shift.unit_number || 1,
        priority: 'HIGH',
        reason: 'Flagged from study plan history for revision'
      });
      showToast('Added topic to Redo queue!', 'success');
      onRefresh();
    } catch (e) {
      showToast('Failed to add to redo: ' + e.message, 'error');
    }
  };

  const handleUndoReschedule = async (historyId) => {
    try {
      const res = await window.LastChanceAPI.undoReschedule(historyId);
      showToast('Reschedule undone! Shift restored to original planned date.', 'success');
      loadRescheduledTasks();
      loadDaySchedule(selectedDate);
      onRefresh();
    } catch (e) {
      showToast('Failed to undo reschedule: ' + e.message, 'error');
    }
  };

  const handleRunOfficialImport = async () => {
    setImporting(true);
    try {
      const res = await window.LastChanceAPI.importOfficialTimetable();
      showToast(res.message, 'success');
      loadImportPreview();
      loadDaySchedule(selectedDate);
      onRefresh();
    } catch (e) {
      showToast('Failed to import timetable: ' + e.message, 'error');
    } finally {
      setImporting(false);
    }
  };

  // Filter shifts
  const shifts = daySchedule?.shifts || [];
  const wrapup = daySchedule?.wrapup || null;

  const filteredShifts = shifts.filter(s => {
    if (courseFilter !== 'ALL' && s.subject_code !== courseFilter) return false;
    if (statusFilter !== 'ALL' && s.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header & Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Official Study Timetable & Daily Plan
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Complete 25-day horizon (27 Oct – 20 Nov 2026). Five 45-min shifts + 15-min wrap-up per day.
          </p>
        </div>

        {/* Sub-tab pills */}
        <div className="flex items-center space-x-1.5 p-1 rounded-lg border text-xs" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => setActiveSubTab('daily_plan')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeSubTab === 'daily_plan' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            📅 Day-by-Day View
          </button>
          <button
            onClick={() => setActiveSubTab('rescheduled')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeSubTab === 'rescheduled' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            🔄 Rescheduled Backlog ({rescheduledList.length})
          </button>
          <button
            onClick={() => setActiveSubTab('import_review')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeSubTab === 'import_review' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            📥 Timetable Review
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: DAY-BY-DAY PLAN */}
      {activeSubTab === 'daily_plan' && (
        <div className="space-y-5">
          {/* Horizontal Date Picker Strip (25 Days) */}
          <div className="lc-card p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-300">Select Date (27 Oct - 20 Nov 2026):</span>
              <span className="text-indigo-400 font-mono font-bold">Selected: {selectedDate}</span>
            </div>
            <div className="flex items-center space-x-2 overflow-x-auto pb-2 pr-2 scrollbar-thin">
              {timetableDates.map(item => {
                const isSelected = item.date === selectedDate;
                const isToday = item.date === dates?.today_str;
                return (
                  <button
                    key={item.date}
                    onClick={() => setSelectedDate(item.date)}
                    className={`px-3 py-2 rounded-lg text-xs shrink-0 flex flex-col items-center transition-smooth border font-mono ${
                      isSelected
                        ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                        : isToday
                        ? 'border-indigo-400 text-indigo-300 bg-indigo-500/10'
                        : 'border-slate-800 text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                    }`}
                  >
                    <span className="text-[10px] uppercase font-bold">{item.month} {item.day}</span>
                    <span className="text-xs font-bold">{item.label.split(' ')[0]}</span>
                    {isToday && <span className="text-[9px] font-sans text-amber-400">Today</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-400">Course Filter:</span>
              {['ALL', 'CSN 3003', 'CSN 3001', 'CSN 3004', 'CSN 3002'].map(c => (
                <button
                  key={c}
                  onClick={() => setCourseFilter(c)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold ${
                    courseFilter === c ? 'btn-primary' : 'btn-secondary text-slate-300'
                  }`}
                >
                  {c === 'ALL' ? 'All Courses' : c}
                </button>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-400">Status:</span>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="text-xs py-1 px-2.5 rounded border"
              >
                <option value="ALL">All Statuses</option>
                <option value="NOT_STARTED">Not Started</option>
                <option value="COMPLETED">Completed</option>
                <option value="OVERDUE">Overdue</option>
                <option value="RESCHEDULED">Rescheduled</option>
              </select>
            </div>
          </div>

          {/* Shifts List for Selected Date */}
          {loadingDay ? (
            <div className="p-8 text-center text-slate-400 text-xs">Loading study shifts for {selectedDate}...</div>
          ) : (
            <div className="space-y-3">
              {filteredShifts.length === 0 ? (
                <div className="lc-card p-8 text-center text-slate-400 text-xs">
                  No shifts match the current filters for {selectedDate}.
                </div>
              ) : (
                filteredShifts.map((shift, idx) => {
                  const isCompleted = shift.status === 'COMPLETED';
                  const isOverdue = shift.status === 'OVERDUE';
                  const isRescheduled = shift.status === 'RESCHEDULED';

                  return (
                    <div
                      key={shift.id}
                      className={`lc-card p-4 space-y-3 border-l-4 ${
                        isCompleted ? 'border-emerald-500' :
                        isOverdue ? 'border-rose-500' :
                        isRescheduled ? 'border-amber-500' : 'border-indigo-500'
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: shift.subject_color || '#4f46e5' }}>
                            SHIFT {shift.shift_number || idx + 1} • {shift.duration_minutes || 45} MIN
                          </span>
                          <span className="text-xs font-bold text-slate-200">
                            {shift.subject_name} ({shift.subject_code})
                          </span>
                          {shift.unit_name && (
                            <span className="text-xs px-2 py-0.5 rounded text-slate-300" style={{ backgroundColor: 'var(--bg-card-elevated)' }}>
                              {shift.unit_name}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center space-x-2">
                          {shift.original_date && shift.original_date !== shift.scheduled_date && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              Orig: {shift.original_date}
                            </span>
                          )}
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                            isCompleted ? 'badge-success badge' :
                            isOverdue ? 'badge-error badge' :
                            isRescheduled ? 'badge-warning badge' : 'badge-info badge'
                          }`}>
                            {shift.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>

                      <div className="text-sm font-bold text-slate-100">
                        {shift.task_description || shift.topic_title}
                      </div>

                      <div className="flex flex-wrap items-center justify-between pt-2 gap-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => onStartSession(shift)}
                            className="btn-primary text-xs font-bold py-1 px-3"
                          >
                            ⏱️ Launch 45m Focus Session
                          </button>
                          {!isCompleted ? (
                            <>
                              <button
                                onClick={() => handleQuickComplete(shift)}
                                className="px-3 py-1 rounded-md text-xs font-bold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30"
                              >
                                ✓ Complete
                              </button>
                              <button
                                onClick={() => handleCompleteAndRedo(shift)}
                                className="px-2.5 py-1 rounded-md text-xs font-bold text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30"
                                title="Complete shift & immediately queue for revision"
                              >
                                ✓ + 🔁 Redo
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => handleAddCompletedToRedo(shift)}
                              className="px-2.5 py-1 rounded-md text-xs font-semibold text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30"
                              title="Queue completed task for redo revision"
                            >
                              🔁 Add to Redo
                            </button>
                          )}
                        </div>

                        <div className="flex items-center space-x-2">
                          {!isCompleted && (
                            <button
                              onClick={() => setPartialTask(shift)}
                              className="btn-secondary text-xs py-1 px-2.5"
                            >
                              Partial Stop
                            </button>
                          )}
                          <button
                            onClick={() => setRescheduleTask(shift)}
                            className="btn-secondary text-xs py-1 px-2.5"
                          >
                            Reschedule
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}

              {/* Wrap-up card if applicable */}
              {wrapup && (
                <div className="lc-card p-4 space-y-2 border-l-4 border-cyan-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black px-2 py-0.5 rounded bg-cyan-600 text-white">
                      WRAP-UP BLOCK • 15 MIN
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      wrapup.status === 'COMPLETED' ? 'badge-success badge' : 'badge-warning badge'
                    }`}>
                      {wrapup.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300">
                    {wrapup.task_description}
                  </p>
                  <div className="pt-2 border-t flex justify-end" style={{ borderColor: 'var(--border-color)' }}>
                    {wrapup.status !== 'COMPLETED' && (
                      <button
                        onClick={() => handleQuickComplete(wrapup)}
                        className="btn-primary text-xs py-1 px-3"
                      >
                        ✓ Complete Wrap-up
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 2: RESCHEDULED BACKLOG */}
      {activeSubTab === 'rescheduled' && (
        <div className="space-y-4">
          <div className="lc-card p-4 space-y-2 border-l-4 border-amber-500">
            <h3 className="text-sm font-bold text-slate-100">
              Rescheduled Tasks & Audit History
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Whenever an unfinished or interrupted shift is moved, the system preserves the original date and records an audit log. You can review all movements and undo any rescheduling action safely.
            </p>
          </div>

          {loadingRescheduled ? (
            <p className="p-8 text-center text-xs text-slate-400">Loading rescheduled tasks...</p>
          ) : rescheduledList.length === 0 ? (
            <div className="lc-card p-8 text-center text-xs text-slate-400">
              No tasks currently rescheduled. All study shifts are on their planned schedule.
            </div>
          ) : (
            <div className="space-y-3">
              {rescheduledList.map(item => (
                <div key={item.id} className="lc-card p-4 space-y-2.5 border-l-4 border-amber-500">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: item.subject_color || '#4f46e5' }}>
                        {item.subject_code} • SHIFT {item.shift_number || 1}
                      </span>
                      <span className="text-xs font-bold text-slate-200">{item.subject_name}</span>
                    </div>
                    <span className="badge badge-warning text-[10px]">Rescheduled</span>
                  </div>

                  <div className="text-sm font-bold text-slate-100">
                    {item.task_description || item.topic_title}
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs font-mono p-2.5 rounded border" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div>
                      <span className="text-slate-400 block text-[10px]">ORIGINAL PLANNED:</span>
                      <strong className="text-indigo-400">{item.original_date}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">CURRENT SCHEDULED:</span>
                      <strong className="text-amber-400">{item.scheduled_date}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">REASON / NOTES:</span>
                      <span className="text-slate-300 font-sans">{item.rescheduled_reason || 'Unfinished shift automatically rescheduled'}</span>
                    </div>
                  </div>

                  <div className="flex justify-end pt-1">
                    <button
                      onClick={() => handleUndoReschedule(item.latest_history_id || item.id)}
                      className="btn-secondary text-xs font-bold py-1 px-3 text-rose-400 hover:text-rose-300"
                    >
                      ↩ Undo Reschedule (Restore to {item.original_date})
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: TIMETABLE IMPORT REVIEW */}
      {activeSubTab === 'import_review' && (
        <div className="space-y-4">
          <div className="lc-card p-5 space-y-3 border-l-4 border-indigo-500">
            <h3 className="text-base font-bold text-slate-100">
              Official Study Timetable Specification
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Source: Word document Study Timetable (27 Oct – 20 Nov 2026).
              Preserves exact course topics, daily 5x 45-min shifts + 15-min wrap-up (240m target), 2 DSA questions, and 30-min English practice.
            </p>

            {importPreview && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Covered Days</div>
                  <div className="text-xl font-black text-indigo-400 font-mono">{importPreview.days_count}</div>
                  <div className="text-[10px] text-slate-400">27 Oct - 20 Nov</div>
                </div>
                <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Total Shifts</div>
                  <div className="text-xl font-black text-emerald-400 font-mono">{importPreview.total_shifts}</div>
                  <div className="text-[10px] text-slate-400">5 per day</div>
                </div>
                <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Wrap-up Sessions</div>
                  <div className="text-xl font-black text-cyan-400 font-mono">{importPreview.total_wrapup_sessions}</div>
                  <div className="text-[10px] text-slate-400">15 min each</div>
                </div>
                <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="text-[10px] font-bold text-slate-400 uppercase">Existing in Database</div>
                  <div className="text-xl font-black text-amber-400 font-mono">{importPreview.already_imported_count}</div>
                  <div className="text-[10px] text-slate-400">Safe duplicate-checked</div>
                </div>
              </div>
            )}

            <div className="pt-3 border-t flex flex-wrap items-center justify-between gap-3" style={{ borderColor: 'var(--border-color)' }}>
              <div className="text-xs text-slate-300">
                Prevent duplicate tasks: Running import only creates missing schedules and never overwrites completed study sessions.
              </div>
              <button
                onClick={handleRunOfficialImport}
                disabled={importing}
                className="btn-primary text-xs font-bold py-2 px-4"
              >
                {importing ? 'Syncing...' : '📥 Sync Official Timetable'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Partial Complete Modal */}
      {partialTask && (
        <PartialCompleteModal
          task={partialTask}
          onClose={() => setPartialTask(null)}
          onSuccess={async () => {
            setPartialTask(null);
            await loadDaySchedule(selectedDate);
            onRefresh();
            showAppreciation("Recorded completed study duration and scheduled remaining work safely!");
          }}
          showToast={showToast}
        />
      )}

      {/* Reschedule Modal */}
      {rescheduleTask && (
        <RescheduleModal
          task={rescheduleTask}
          onClose={() => setRescheduleTask(null)}
          onSuccess={async () => {
            setRescheduleTask(null);
            await loadDaySchedule(selectedDate);
            onRefresh();
            showToast('Shift rescheduled to future date.', 'success');
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}


function StudyCalendarView({ dates, onStartSession, onRefresh, showToast, showAppreciation }) {
  const [currentYear, setCurrentYear] = useState(2026);
  const [currentMonth, setCurrentMonth] = useState(10); // 10 = Nov (0-indexed: 9=Oct, 10=Nov, 11=Dec)
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDayEvents, setSelectedDayEvents] = useState(null);

  const EXAM_DATES = {
    '2026-11-26': 'CSN 3001 Exam: Data Structures',
    '2026-11-28': 'CSN 3003 Exam: Discrete Structures',
    '2026-12-01': 'CSN 3004 Exam: Object-Oriented Prog',
    '2026-12-04': 'CSN 3002 Exam: Data Science & ML'
  };

  const loadCalendarEvents = async () => {
    setLoading(true);
    try {
      const y = currentYear;
      const m = currentMonth + 1;
      const start = `${y}-${String(m).padStart(2, '0')}-01`;
      const lastDay = new Date(y, m, 0).getDate();
      const end = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;

      const res = await window.LastChanceAPI.getCalendarEvents(start, end);
      setEvents(res.events || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalendarEvents();
  }, [currentYear, currentMonth]);

  // Calendar Grid Builder
  const calendarCells = useMemo(() => {
    const firstDayIndex = new Date(currentYear, currentMonth, 1).getDay(); // 0 = Sun
    const totalDaysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const cells = [];

    // Leading empty days from prev month
    for (let i = 0; i < firstDayIndex; i++) {
      cells.push({ isPadding: true, dayNumber: null, dateStr: null });
    }

    // Days in current month
    for (let d = 1; d <= totalDaysInMonth; d++) {
      const mStr = String(currentMonth + 1).padStart(2, '0');
      const dStr = String(d).padStart(2, '0');
      const dateStr = `${currentYear}-${mStr}-${dStr}`;
      const dayEvts = events.filter(e => e.date === dateStr);
      const isExam = EXAM_DATES[dateStr];
      const isToday = dateStr === dates?.today_str;

      // Calculate total study time on this day
      const studyMinutes = dayEvts.reduce((acc, ev) => acc + (ev.actual_minutes || (ev.status === 'COMPLETED' ? (ev.duration || 45) : 0)), 0);

      cells.push({
        isPadding: false,
        dayNumber: d,
        dateStr: dateStr,
        events: dayEvts,
        isExam: isExam,
        isToday: isToday,
        studyMinutes: studyMinutes
      });
    }

    return cells;
  }, [currentYear, currentMonth, events, dates]);

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(y => y - 1);
    } else {
      setCurrentMonth(m => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(y => y + 1);
    } else {
      setCurrentMonth(m => m + 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Month Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Study Calendar & Exam Milestones
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Track scheduled study shifts, completed daily targets, and official examination dates
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button onClick={handlePrevMonth} className="btn-secondary text-xs py-1.5 px-3">
            ← Prev
          </button>
          <span className="text-sm font-bold font-mono px-3 py-1 rounded border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
            {monthNames[currentMonth]} {currentYear}
          </span>
          <button onClick={handleNextMonth} className="btn-secondary text-xs py-1.5 px-3">
            Next →
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="lc-card p-4 space-y-3">
        {/* Days of week header */}
        <div className="grid grid-cols-7 gap-1 text-center font-bold text-xs uppercase tracking-wider text-slate-400 py-1 border-b" style={{ borderColor: 'var(--border-color)' }}>
          <div>Sun</div>
          <div>Mon</div>
          <div>Tue</div>
          <div>Wed</div>
          <div>Thu</div>
          <div>Fri</div>
          <div>Sat</div>
        </div>

        {/* Month Cells Grid */}
        <div className="calendar-grid">
          {calendarCells.map((cell, idx) => {
            if (cell.isPadding) {
              return (
                <div key={idx} className="calendar-cell inactive-month min-h-[90px] opacity-40"></div>
              );
            }

            const targetMet = cell.studyMinutes >= 240;

            return (
              <div
                key={idx}
                onClick={() => setSelectedDayEvents(cell)}
                className={`calendar-cell min-h-[105px] p-2 flex flex-col justify-between transition-smooth cursor-pointer ${
                  cell.isToday ? 'is-today' : ''
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold font-mono ${cell.isToday ? 'text-indigo-400 font-black' : 'text-slate-300'}`}>
                      {cell.dayNumber}
                    </span>
                    {cell.studyMinutes > 0 && (
                      <span className={`text-[10px] font-bold px-1.5 rounded font-mono ${
                        targetMet ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-indigo-500/20 text-indigo-300'
                      }`}>
                        {cell.studyMinutes}m {targetMet ? '✓' : ''}
                      </span>
                    )}
                  </div>

                  {cell.isExam && (
                    <div className="mt-1 p-1 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 truncate">
                      🎯 {cell.isExam}
                    </div>
                  )}

                  {/* Task Pills */}
                  <div className="mt-1 space-y-1">
                    {cell.events?.slice(0, 2).map((ev, i) => (
                      <div
                        key={i}
                        className="calendar-event-pill text-[10px] truncate"
                        style={{
                          backgroundColor: ev.subject_color ? `${ev.subject_color}25` : 'rgba(79, 70, 229, 0.2)',
                          color: ev.subject_color || '#818cf8',
                          border: `1px solid ${ev.subject_color || '#6366f1'}40`
                        }}
                      >
                        {ev.title || ev.topic_title}
                      </div>
                    ))}
                    {cell.events?.length > 2 && (
                      <div className="text-[9px] text-slate-400 font-mono">
                        +{cell.events.length - 2} more shifts
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day Details Modal */}
      {selectedDayEvents && (
        <div className="modal-overlay" onClick={() => setSelectedDayEvents(null)}>
          <div className="modal-dialog p-5 space-y-4 max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Day Details</span>
                <h3 className="text-base font-bold text-slate-100 font-mono">{selectedDayEvents.dateStr}</h3>
              </div>
              <button onClick={() => setSelectedDayEvents(null)} className="text-slate-400 hover:text-white text-lg">✕</button>
            </div>

            {selectedDayEvents.isExam && (
              <div className="p-3 rounded-lg border bg-rose-500/10 border-rose-500/30 text-rose-400 text-xs font-bold">
                🎯 {selectedDayEvents.isExam}
              </div>
            )}

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {selectedDayEvents.events?.length === 0 ? (
                <p className="text-xs text-slate-400 py-6 text-center">No study shifts scheduled for this date.</p>
              ) : (
                selectedDayEvents.events.map((ev, i) => (
                  <div key={i} className="p-3 rounded-lg border space-y-2 text-xs" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200">{ev.title || ev.topic_title}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        ev.status === 'COMPLETED' ? 'badge-success badge' : 'badge-warning badge'
                      }`}>
                        {ev.status || 'SCHEDULED'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400 text-[11px]">
                      <span>⏱️ Planned: {ev.duration || 45} mins</span>
                      {ev.actual_minutes && <span>Actual: {ev.actual_minutes} mins</span>}
                    </div>
                    {ev.status !== 'COMPLETED' && (
                      <button
                        onClick={() => {
                          setSelectedDayEvents(null);
                          onStartSession(ev);
                        }}
                        className="btn-primary text-xs py-1 px-3 w-full"
                      >
                        ⏱️ Start Focus Session
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button onClick={() => setSelectedDayEvents(null)} className="btn-secondary text-xs">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 4. COURSES & SYLLABUS VIEW -----------------

function CoursesUnitsView({ subjects, onRefresh, showToast, showAppreciation }) {
  const [trackerData, setTrackerData] = useState(null);
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [difficultyFilter, setDifficultyFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  const loadSyllabusTracker = async () => {
    setLoading(true);
    try {
      const res = await window.LastChanceAPI.getSyllabusTracker();
      setTrackerData(res);
      if (!activeCourseId && res.courses?.length > 0) {
        setActiveCourseId(res.courses[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSyllabusTracker();
  }, []);

  const courses = trackerData?.courses || [];
  const activeCourse = courses.find(c => c.id === activeCourseId) || courses[0];

  const handleUpdateTopic = async (topicId, newStatus, newDiff = null, needsRev = null) => {
    try {
      await window.LastChanceAPI.updateTopicStatusAudit(
        topicId,
        newStatus,
        newDiff,
        needsRev
      );
      await loadSyllabusTracker();
      onRefresh();
      if (newStatus === 'COMPLETED') {
        showAppreciation("Topic completed! Course and unit progress updated.");
      } else {
        showToast('Topic status updated successfully!');
      }
    } catch (e) {
      showToast('Failed to update topic: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          Courses & Verified Syllabus Tracker
        </h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Verified progress tracking for all 4 courses based on confirmed topic completion records, not scheduled time alone.
        </p>
      </div>

      {/* 4 Course Selection Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {courses.map(course => {
          const isSelected = course.id === activeCourseId;
          const pct = course.completion_percent || 0;
          return (
            <div
              key={course.id}
              onClick={() => setActiveCourseId(course.id)}
              className={`lc-card p-4 cursor-pointer transition-smooth border-l-4 ${
                isSelected ? 'shadow-md border-indigo-500' : 'opacity-85 hover:opacity-100'
              }`}
              style={{
                borderLeftColor: course.color || '#4f46e5',
                backgroundColor: isSelected ? 'var(--bg-card-elevated)' : 'var(--bg-card)'
              }}
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono font-bold text-white px-2 py-0.5 rounded text-[10px]" style={{ backgroundColor: course.color || '#4f46e5' }}>
                  {course.code}
                </span>
                <span className="font-bold text-indigo-400 font-mono">{pct}%</span>
              </div>
              <h4 className="text-sm font-bold text-slate-100 mt-2 truncate">{course.name}</h4>
              <div className="mt-2 space-y-1">
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-smooth"
                    style={{ width: `${pct}%`, backgroundColor: course.color || '#4f46e5' }}
                  ></div>
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>{course.topics_completed} / {course.total_topics} Topics</span>
                  <span>{course.total_units} Units</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Course Syllabus Tree */}
      {activeCourse && (
        <div className="lc-card p-5 space-y-5">
          {/* Active Course Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono">
                {activeCourse.code} • {activeCourse.total_units} Units
              </span>
              <h3 className="text-base font-bold text-slate-100 mt-0.5">{activeCourse.name}</h3>
              <p className="text-xs text-slate-400">
                Topics: <strong className="text-emerald-400">{activeCourse.topics_completed} Completed</strong> • {activeCourse.topics_remaining} Remaining • {activeCourse.study_hours_formatted} Studied
              </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <input
                type="text"
                placeholder="Search topics..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="py-1 px-2.5 rounded border text-xs"
              />
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="py-1 px-2.5 rounded border text-xs"
              >
                <option value="ALL">All Statuses</option>
                <option value="NOT_STARTED">Not Started</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="NEEDS_REVISION">Needs Revision</option>
              </select>
              <select
                value={difficultyFilter}
                onChange={e => setDifficultyFilter(e.target.value)}
                className="py-1 px-2.5 rounded border text-xs"
              >
                <option value="ALL">All Difficulties</option>
                <option value="EASY">Easy</option>
                <option value="MODERATE">Moderate</option>
                <option value="DIFFICULT">Difficult</option>
              </select>
            </div>
          </div>

          {/* Units Accordion */}
          <div className="space-y-4">
            {activeCourse.units?.map(unit => {
              const unitTopics = (unit.topics || []).filter(t => {
                if (searchTerm && !t.title.toLowerCase().includes(searchTerm.toLowerCase())) return false;
                if (statusFilter !== 'ALL' && t.mastery_level !== statusFilter) return false;
                if (difficultyFilter !== 'ALL' && t.difficulty_level !== difficultyFilter) return false;
                return true;
              });

              if (searchTerm && unitTopics.length === 0) return null;

              const unitPct = unit.completion_percent || 0;

              return (
                <div key={unit.unit_number} className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-card-elevated)' }}>
                  {/* Unit Header */}
                  <div className="p-3.5 flex flex-wrap items-center justify-between gap-3 border-b" style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-card)' }}>
                    <div className="space-y-0.5">
                      <span className="text-[10px] font-bold text-indigo-400 font-mono">UNIT {unit.unit_number}</span>
                      <h4 className="text-sm font-bold text-slate-100">{unit.title}</h4>
                    </div>
                    <div className="flex items-center space-x-3 text-xs">
                      <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${unitPct}%` }}></div>
                      </div>
                      <span className="font-mono font-bold text-indigo-400">{unitPct}%</span>
                      <span className="text-slate-400">({unit.completed_count}/{unit.topics_count} Topics)</span>
                    </div>
                  </div>

                  {/* Topics List */}
                  <div className="divide-y" style={{ borderColor: 'var(--border-color)' }}>
                    {unitTopics.length === 0 ? (
                      <p className="p-4 text-xs text-slate-400 text-center">No topics match filters in this unit.</p>
                    ) : (
                      unitTopics.map(topic => {
                        const isDone = topic.mastery_level === 'COMPLETED' || topic.mastery_level === 'MASTERED';
                        const isRev = topic.needs_revision || topic.mastery_level === 'NEEDS_REVISION';

                        return (
                          <div key={topic.id} className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 hover:bg-slate-800/20 transition-smooth">
                            <div className="space-y-1">
                              <div className="flex items-center space-x-2">
                                <span className="text-xs font-semibold text-slate-200">{topic.title}</span>
                                {isRev && (
                                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                    Needs Revision
                                  </span>
                                )}
                              </div>
                              {topic.learning_objectives && (
                                <p className="text-[11px] text-slate-400 line-clamp-1">{topic.learning_objectives}</p>
                              )}
                            </div>

                            {/* Controls: Status, Difficulty, Needs Revision */}
                            <div className="flex items-center space-x-2 shrink-0 text-xs">
                              <select
                                value={topic.difficulty_level || 'MODERATE'}
                                onChange={e => handleUpdateTopic(topic.id, topic.mastery_level, e.target.value, topic.needs_revision)}
                                className="py-1 px-2 rounded border text-[11px]"
                              >
                                <option value="EASY">Easy</option>
                                <option value="MODERATE">Moderate</option>
                                <option value="DIFFICULT">Difficult</option>
                              </select>

                              <select
                                value={topic.mastery_level || 'NOT_STARTED'}
                                onChange={e => handleUpdateTopic(topic.id, e.target.value, topic.difficulty_level, topic.needs_revision)}
                                className={`py-1 px-2.5 rounded border text-[11px] font-bold ${
                                  isDone ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' : 'text-slate-300'
                                }`}
                              >
                                <option value="NOT_STARTED">Not Started</option>
                                <option value="IN_PROGRESS">In Progress</option>
                                <option value="COMPLETED">Completed</option>
                                <option value="NEEDS_REVISION">Needs Revision</option>
                              </select>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


function HandoutsView({ subjects, showToast }) {
  const [hierarchy, setHierarchy] = useState([]);
  const [loading, setLoading] = useState(true);

  // Navigation flow: 'courses' -> 'units' -> 'topics'
  const [viewLevel, setViewLevel] = useState('courses');
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedUnit, setSelectedUnit] = useState(null);

  // Preview Modal
  const [previewHandout, setPreviewHandout] = useState(null);

  const loadHierarchy = async () => {
    setLoading(true);
    try {
      const res = await window.LastChanceAPI.getHandoutsHierarchy();
      const courses = res.courses || [];
      setHierarchy(courses);

      // Keep selectedCourse and selectedUnit up to date if currently open
      if (selectedCourse) {
        const updatedC = courses.find(c => c.id === selectedCourse.id);
        if (updatedC) {
          setSelectedCourse(updatedC);
          if (selectedUnit) {
            const updatedU = updatedC.units.find(u => u.id === selectedUnit.id);
            if (updatedU) setSelectedUnit(updatedU);
          }
        }
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to load course handouts: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHierarchy();
  }, []);

  const handleToggleTopic = async (topic) => {
    const newStatus = topic.is_completed ? 'NOT_STARTED' : 'COMPLETED';
    try {
      await window.LastChanceAPI.updateTopicStatus(topic.id, newStatus);
      showToast(newStatus === 'COMPLETED' ? `Marked "${topic.title}" as completed!` : `Marked "${topic.title}" as not completed`);
      await loadHierarchy();
    } catch (e) {
      showToast('Failed to update topic: ' + e.message, 'error');
    }
  };

  const getCourseIcon = (code) => {
    if (code.includes('3003')) return '📐'; // Discrete Structures
    if (code.includes('3001')) return '🌲'; // Data Structures
    if (code.includes('3004')) return '☕'; // OOP
    if (code.includes('3002')) return '🤖'; // DSML
    return '📚';
  };

  return (
    <div className="space-y-6">
      {/* LEVEL 1: ALL FOUR COURSES */}
      {viewLevel === 'courses' && (
        <div className="space-y-5">
          {/* Header */}
          <div className="border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <h2 className="text-lg font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Handouts
            </h2>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Course syllabus outlines, lecture notes, and learning materials across all 4 university subjects.
            </p>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs text-slate-400">Loading course handouts...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {hierarchy.map(c => {
                const icon = getCourseIcon(c.code);
                return (
                  <div
                    key={c.id}
                    className="p-5 rounded-xl border space-y-4 hover:border-indigo-500/40 transition-smooth shadow-sm flex flex-col justify-between"
                    style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-2xl">{icon}</span>
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded border" style={{ borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
                          {c.code}
                        </span>
                      </div>
                      <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                        {c.name}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                        <span>{c.total_units} Units</span>
                        <span>•</span>
                        <span className={c.units_with_materials > 0 ? 'text-emerald-400 font-semibold' : ''}>
                          {c.units_with_materials > 0 ? `${c.units_with_materials} Units with Handouts` : 'Syllabus Outline Available'}
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1.5 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                      <div className="flex items-center justify-between text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        <span>Syllabus Completion</span>
                        <span className="font-bold text-indigo-400 font-mono">
                          {c.completed_topics} / {c.total_topics} Topics ({c.progress_percent}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border" style={{ borderColor: 'var(--border-color)' }}>
                        <div
                          className="h-full rounded-full transition-smooth bg-indigo-500"
                          style={{ width: `${c.progress_percent}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-2">
                      {c.course_materials && c.course_materials.length > 0 ? (
                        <button
                          onClick={() => setPreviewHandout(c.course_materials[0])}
                          className="text-xs text-amber-500 hover:text-amber-400 font-semibold flex items-center space-x-1"
                        >
                          <span>👁️</span>
                          <span>View Official Syllabus Outline</span>
                        </button>
                      ) : <span />}

                      <button
                        onClick={() => {
                          setSelectedCourse(c);
                          setViewLevel('units');
                        }}
                        className="btn-primary text-xs font-bold py-1.5 px-3.5 flex items-center space-x-1.5"
                      >
                        <span>Open Course</span>
                        <span>→</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 2: UNITS IN SELECTED COURSE */}
      {viewLevel === 'units' && selectedCourse && (
        <div className="space-y-5">
          {/* Breadcrumb & Back */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={() => setViewLevel('courses')}
                className="font-bold text-indigo-400 hover:underline flex items-center space-x-1"
              >
                <span>← All Courses</span>
              </button>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                {selectedCourse.code}: {selectedCourse.name}
              </span>
            </div>

            {selectedCourse.course_materials && selectedCourse.course_materials.length > 0 && (
              <button
                onClick={() => setPreviewHandout(selectedCourse.course_materials[0])}
                className="btn-secondary text-xs font-semibold py-1 px-3 flex items-center space-x-1 text-amber-400"
              >
                <span>👁️</span>
                <span>View Full Syllabus Outline</span>
              </button>
            )}
          </div>

          {/* Units Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {selectedCourse.units.map(unit => {
              const hasHandouts = unit.handouts && unit.handouts.length > 0;
              return (
                <div
                  key={unit.id}
                  className="p-4 rounded-xl border space-y-3 hover:border-indigo-500/30 transition-smooth"
                  style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono">
                        Unit {unit.unit_number}
                      </span>
                      <h4 className="text-sm font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>
                        {unit.title}
                      </h4>
                    </div>
                    {hasHandouts && (
                      <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shrink-0">
                        📄 {unit.handouts.length} Handout{unit.handouts.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <div className="flex justify-between">
                      <span>{unit.total_topics} Topics</span>
                      <span className="font-mono">{unit.completed_topics} Completed ({unit.progress_percent}%)</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden border" style={{ borderColor: 'var(--border-color)' }}>
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${unit.progress_percent}%` }}></div>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
                    <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      {hasHandouts ? 'Lecture notes available' : 'Syllabus topics loaded'}
                    </span>
                    <button
                      onClick={() => {
                        setSelectedUnit(unit);
                        setViewLevel('topics');
                      }}
                      className="btn-primary text-xs font-bold py-1 px-3"
                    >
                      View Topics & Materials →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* LEVEL 3: TOPICS & HANDOUTS FOR SELECTED UNIT */}
      {viewLevel === 'topics' && selectedCourse && selectedUnit && (
        <div className="space-y-5">
          {/* Breadcrumb Navigation */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <button
                onClick={() => setViewLevel('courses')}
                className="text-indigo-400 hover:underline font-semibold"
              >
                Handouts
              </button>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <button
                onClick={() => setViewLevel('units')}
                className="text-indigo-400 hover:underline font-semibold"
              >
                {selectedCourse.code}
              </button>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                Unit {selectedUnit.unit_number}: {selectedUnit.title}
              </span>
            </div>

            <button
              onClick={() => setViewLevel('units')}
              className="btn-secondary text-xs font-semibold py-1 px-3 self-start sm:self-center"
            >
              ← Back to Units
            </button>
          </div>

          {/* Unit Materials Banner */}
          {selectedUnit.handouts && selectedUnit.handouts.length > 0 ? (
            <div className="p-4 rounded-xl border border-emerald-500/30 space-y-2.5" style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)' }}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                  📄 Available Unit Materials ({selectedUnit.handouts.length})
                </span>
              </div>
              <div className="space-y-2">
                {selectedUnit.handouts.map(h => (
                  <div key={h.id} className="p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-2" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                    <div>
                      <div className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                        {h.original_filename || h.filename}
                      </div>
                      <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        Type: {h.file_type?.toUpperCase()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0">
                      <button
                        onClick={() => setPreviewHandout(h)}
                        className="btn-primary text-xs font-bold py-1 px-3"
                      >
                        👁️ Preview Handout
                      </button>
                      <a
                        href={`/api/handouts/${h.id}/download`}
                        download
                        className="btn-secondary text-xs font-semibold py-1 px-3"
                      >
                        ⬇️ Download
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl border border-amber-500/30 text-xs flex items-center space-x-2.5" style={{ backgroundColor: 'rgba(245, 158, 11, 0.06)' }}>
              <span className="text-lg">ℹ️</span>
              <span style={{ color: 'var(--text-secondary)' }}>
                Official syllabus topics loaded. Lecture notes/slides for this unit have not been uploaded yet. You can track topic completion directly below.
              </span>
            </div>
          )}

          {/* Topics Checklist */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
                Unit Topics ({selectedUnit.topics.length})
              </h3>
              <span className="text-xs font-mono font-bold text-indigo-400">
                {selectedUnit.completed_topics} / {selectedUnit.total_topics} Completed
              </span>
            </div>

            <div className="space-y-2">
              {selectedUnit.topics.map((t, idx) => {
                const isDone = t.is_completed;
                return (
                  <div
                    key={t.id}
                    className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 transition-smooth ${
                      isDone ? 'opacity-75' : ''
                    }`}
                    style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <button
                        onClick={() => handleToggleTopic(t)}
                        className={`w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs shrink-0 transition-smooth ${
                          isDone ? 'bg-emerald-500 text-white' : 'border border-slate-600 hover:border-emerald-500'
                        }`}
                        title={isDone ? 'Mark as Not Completed' : 'Mark as Completed'}
                      >
                        {isDone ? '✓' : ''}
                      </button>
                      <div className="min-w-0">
                        <span className={`text-sm font-bold block ${isDone ? 'line-through' : ''}`} style={{ color: 'var(--text-primary)' }}>
                          {t.title}
                        </span>
                        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          Topic #{idx + 1} • Est. {t.estimated_minutes || 60}m
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      {isDone ? (
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold border border-emerald-500/30">
                          Completed ✓
                        </span>
                      ) : (
                        <button
                          onClick={() => handleToggleTopic(t)}
                          className="btn-secondary text-xs font-semibold py-1 px-2.5"
                        >
                          Mark Complete
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* PREVIEW MODAL */}
      {previewHandout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-4xl max-h-[90vh] rounded-2xl border flex flex-col overflow-hidden shadow-2xl" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
              <div>
                <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                  {previewHandout.original_filename || previewHandout.filename}
                </h3>
                <span className="text-xs text-slate-400">{previewHandout.file_type?.toUpperCase()} Document</span>
              </div>
              <button
                onClick={() => setPreviewHandout(null)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white bg-slate-800 text-sm font-bold"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 p-4 overflow-auto min-h-[400px] flex items-center justify-center bg-slate-950">
              {previewHandout.file_type === 'pdf' ? (
                <iframe
                  src={`/api/handouts/${previewHandout.id}/preview`}
                  className="w-full h-[65vh] border-0 rounded-lg"
                  title="PDF Document Preview"
                />
              ) : (
                <img
                  src={`/api/handouts/${previewHandout.id}/preview`}
                  alt={previewHandout.original_filename}
                  className="max-w-full max-h-[65vh] object-contain rounded-lg"
                />
              )}
            </div>
            <div className="p-3 border-t flex justify-end space-x-2" style={{ borderColor: 'var(--border-color)' }}>
              <a
                href={`/api/handouts/${previewHandout.id}/download`}
                download
                className="btn-primary text-xs font-bold py-1.5 px-4"
              >
                ⬇️ Download File
              </a>
              <button
                onClick={() => setPreviewHandout(null)}
                className="btn-secondary text-xs font-semibold py-1.5 px-4"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function AnalyticsView({ feasibility, onRefresh, showToast, showAppreciation }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const canvasRefA = useRef(null);
  const canvasRefB = useRef(null);
  const canvasRefC = useRef(null);
  const canvasRefE = useRef(null);
  const chartInstances = useRef({});

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await window.LastChanceAPI.getAnalytics();
      setData(res);
    } catch (e) {
      console.error(e);
      showToast('Failed to load analytics: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  // Initialize Chart.js Graphs
  useEffect(() => {
    if (!data || !window.Chart) return;

    // Helper to safely destroy old charts
    const destroyChart = (key) => {
      if (chartInstances.current[key]) {
        chartInstances.current[key].destroy();
        delete chartInstances.current[key];
      }
    };

    // Graph A: Daily Study Time (Actual vs 240m Target Line)
    if (canvasRefA.current && data.daily_study_graph) {
      destroyChart('chartA');
      const g = data.daily_study_graph;
      chartInstances.current['chartA'] = new window.Chart(canvasRefA.current, {
        type: 'bar',
        data: {
          labels: g.labels,
          datasets: [
            {
              label: 'Actual Academic Study (mins)',
              data: g.actual_minutes,
              backgroundColor: '#4f46e5',
              borderRadius: 6
            },
            {
              label: 'Target (240 mins)',
              data: g.labels.map(() => 240),
              type: 'line',
              borderColor: '#10b981',
              borderDash: [5, 5],
              fill: false,
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              suggestedMax: 260,
              grid: { color: 'rgba(255,255,255,0.06)' },
              ticks: { color: '#94a3b8' }
            },
            x: {
              grid: { display: false },
              ticks: {
                color: '#94a3b8',
                autoSkip: true,
                maxTicksLimit: 8,
                maxRotation: 35,
                font: { size: 10 }
              }
            }
          },
          plugins: {
            legend: { labels: { color: '#cbd5e1' } },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} mins (${(ctx.raw / 60).toFixed(1)} hrs)`
              }
            }
          }
        }
      });
    }

    // Graph B: Daily Progress (% Target Capped at 100%)
    if (canvasRefB.current && data.daily_progress_graph) {
      destroyChart('chartB');
      const g = data.daily_progress_graph;
      chartInstances.current['chartB'] = new window.Chart(canvasRefB.current, {
        type: 'line',
        data: {
          labels: g.labels,
          datasets: [
            {
              label: 'Daily Target Progress (%)',
              data: g.progress_percent,
              borderColor: '#06b6d4',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              fill: true,
              tension: 0.3,
              pointBackgroundColor: '#06b6d4'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              min: 0,
              max: 100,
              ticks: {
                callback: (val) => `${val}%`,
                color: '#94a3b8'
              },
              grid: { color: 'rgba(255,255,255,0.06)' }
            },
            x: {
              grid: { display: false },
              ticks: {
                color: '#94a3b8',
                autoSkip: true,
                maxTicksLimit: 8,
                maxRotation: 35,
                font: { size: 10 }
              }
            }
          },
          plugins: {
            legend: { labels: { color: '#cbd5e1' } }
          }
        }
      });
    }

    // Graph C: Wasted Time (Confirmed vs Shortfall Separated)
    if (canvasRefC.current && data.wasted_time_graph) {
      destroyChart('chartC');
      const g = data.wasted_time_graph;
      chartInstances.current['chartC'] = new window.Chart(canvasRefC.current, {
        type: 'bar',
        data: {
          labels: g.labels,
          datasets: [
            {
              label: 'Confirmed Wasted (mins)',
              data: g.confirmed_wasted,
              backgroundColor: '#f97316',
              borderRadius: 4
            },
            {
              label: 'Academic Target Shortfall (mins)',
              data: g.shortfall,
              backgroundColor: '#ef4444',
              borderRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255,255,255,0.06)' },
              ticks: { color: '#94a3b8' }
            },
            x: {
              grid: { display: false },
              ticks: {
                color: '#94a3b8',
                autoSkip: true,
                maxTicksLimit: 8,
                maxRotation: 35,
                font: { size: 10 }
              }
            }
          },
          plugins: {
            legend: { labels: { color: '#cbd5e1' } }
          }
        }
      });
    }

    // Graph E: Course-Wise Progress
    if (canvasRefE.current && data.course_progress) {
      destroyChart('chartE');
      const g = data.course_progress;
      chartInstances.current['chartE'] = new window.Chart(canvasRefE.current, {
        type: 'bar',
        data: {
          labels: g.labels,
          datasets: [
            {
              label: 'Completion %',
              data: g.completion_percents,
              backgroundColor: g.colors || ['#6366f1', '#10b981', '#f59e0b', '#ec4899'],
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              min: 0,
              max: 100,
              ticks: {
                callback: (v) => `${v}%`,
                color: '#94a3b8'
              },
              grid: { color: 'rgba(255,255,255,0.06)' }
            },
            x: {
              grid: { display: false },
              ticks: {
                color: '#94a3b8',
                autoSkip: true,
                maxTicksLimit: 8,
                maxRotation: 35,
                font: { size: 10 }
              }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    return () => {
      Object.keys(chartInstances.current).forEach(k => {
        chartInstances.current[k]?.destroy();
      });
    };
  }, [data]);

  const week = data?.weekly_summary || {};
  const cons = data?.consistency || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Real-Time Study Analytics & Graphs
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Populated exclusively from real stored session records. Evaluates daily targets, weekly summaries, course completion, and honesty metrics.
          </p>
        </div>
        <button onClick={loadAnalytics} className="btn-secondary text-xs py-1 px-3">
          🔄 Refresh Graphs
        </button>
      </div>

      {/* Graph D: Weekly Study Summary (Monday-to-Sunday) */}
      <div className="lc-card p-5 space-y-4 border-l-4 border-indigo-500">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono">
              GRAPH D • WEEKLY SUMMARY (MON - SUN)
            </span>
            <h3 className="text-base font-bold text-slate-100">Weekly Performance Card</h3>
          </div>
          <span className="badge badge-info text-xs">{week.week_label || 'Current Week'}</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Academic Studied</span>
            <span className="font-bold text-base text-indigo-400 font-mono">{week.total_academic_hours || '0h 0m'}</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Planned Academic</span>
            <span className="font-bold text-base text-slate-200 font-mono">{week.total_planned_hours || '0h 0m'}</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Shifts Completed</span>
            <span className="font-bold text-base text-emerald-400 font-mono">{week.completed_shifts || 0}</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Daily Average</span>
            <span className="font-bold text-base text-cyan-400 font-mono">{week.daily_average_minutes || 0}m/day</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Target Achieved</span>
            <span className="font-bold text-base text-amber-400 font-mono">{week.target_rate_percent || 0}%</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="block text-[10px] text-slate-400 uppercase font-bold">Confirmed Wasted</span>
            <span className="font-bold text-base text-rose-400 font-mono">{week.total_confirmed_wasted || 0}m</span>
          </div>
        </div>
      </div>

      {/* 2-Column Grid for Charts A & B */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Graph A: Daily Study Time */}
        <div className="lc-card p-4.5 space-y-3">
          <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider font-mono">GRAPH A</span>
              <h4 className="text-sm font-bold text-slate-100">Daily Academic Study Time (vs 240m Target)</h4>
            </div>
            <span className="text-[10px] text-slate-400">Actual mins</span>
          </div>
          <div className="h-64 relative">
            <canvas ref={canvasRefA}></canvas>
          </div>
        </div>

        {/* Graph B: Daily Progress % */}
        <div className="lc-card p-4.5 space-y-3">
          <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider font-mono">GRAPH B</span>
              <h4 className="text-sm font-bold text-slate-100">Daily Target Completion Rate (%)</h4>
            </div>
            <span className="text-[10px] text-slate-400">Capped at 100%</span>
          </div>
          <div className="h-64 relative">
            <canvas ref={canvasRefB}></canvas>
          </div>
        </div>
      </div>

      {/* 2-Column Grid for Charts C & E */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Graph C: Wasted Time vs Target Shortfall */}
        <div className="lc-card p-4.5 space-y-3 border-rose-500/30">
          <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider font-mono">GRAPH C</span>
              <h4 className="text-sm font-bold text-slate-100">Confirmed Wasted Time vs Target Shortfall</h4>
            </div>
            <span className="text-[10px] text-slate-400">Distinguished metrics</span>
          </div>
          <div className="h-64 relative">
            <canvas ref={canvasRefC}></canvas>
          </div>
        </div>

        {/* Graph E: Course-Wise Progress */}
        <div className="lc-card p-4.5 space-y-3">
          <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider font-mono">GRAPH E</span>
              <h4 className="text-sm font-bold text-slate-100">Course-Wise Verified Completion</h4>
            </div>
            <span className="text-[10px] text-slate-400">4 Subjects</span>
          </div>
          <div className="h-64 relative">
            <canvas ref={canvasRefE}></canvas>
          </div>
        </div>
      </div>

      {/* Graph F: Study Consistency Summary Card */}
      <div className="lc-card p-5 space-y-3">
        <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider font-mono">GRAPH F</span>
            <h4 className="text-sm font-bold text-slate-100">Study Consistency & Target Milestones</h4>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Days with Active Study (≥1 Session)</span>
            <span className="text-2xl font-black text-indigo-400 font-mono mt-1 block">{cons.days_with_session || 0} Days</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Days Reaching Full 240m Target</span>
            <span className="text-2xl font-black text-emerald-400 font-mono mt-1 block">{cons.days_target_achieved || 0} Days</span>
          </div>
          <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Active English Speaking Streak</span>
            <span className="text-2xl font-black text-amber-400 font-mono mt-1 block">🔥 {cons.streak_days || 0} Days</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- 7. WASTED TIME TRACKER VIEW -----------------

function WastedTimeView({ dates, onRefresh, showToast }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // Manual Log Form State
  const [logMins, setLogMins] = useState(30);
  const [logDate, setLogDate] = useState(dates?.today_str || new Date().toISOString().split('T')[0]);
  const [logCategory, setLogCategory] = useState('Avoidable Distraction');
  const [logNotes, setLogNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const res = await window.LastChanceAPI.getWastedTimeSummary();
      setSummary(res);
    } catch (e) {
      console.error(e);
      showToast('Failed to load wasted time summary: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const handleLogSubmit = async (e) => {
    e.preventDefault();
    if (logMins <= 0) {
      showToast('Please enter a duration greater than 0', 'error');
      return;
    }
    setSaving(true);
    try {
      await window.LastChanceAPI.logWastedTime({
        wasted_date: logDate,
        minutes: logMins,
        category: logCategory,
        notes: logNotes
      });
      showToast('Confirmed wasted time logged honestly.', 'success');
      setLogNotes('');
      await loadSummary();
      onRefresh();
    } catch (e) {
      showToast('Failed to log wasted time: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLog = async (logId) => {
    if (!window.confirm('Delete this wasted time entry?')) return;
    try {
      await window.LastChanceAPI.deleteWastedLog(logId);
      showToast('Entry deleted.', 'info');
      await loadSummary();
      onRefresh();
    } catch (e) {
      showToast('Failed to delete entry: ' + e.message, 'error');
    }
  };

  const today = summary?.today || {};
  const week = summary?.week || {};
  const month = summary?.month || {};
  const logs = summary?.recent_logs || [];

  return (
    <div className="space-y-6">
      <div className="border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          Wasted Time & Honesty Tracker
        </h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Understand where your study time is lost without misrepresenting shortfall as wasted time.
        </p>
      </div>

      {/* Clear Distinction Explanatory Banner */}
      <div className="lc-card p-4 space-y-2 border-l-4 border-amber-500 text-xs">
        <h4 className="font-bold text-slate-100">Strict Metric Separation Principles:</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-slate-300">
          <div className="p-2.5 rounded border" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <strong className="text-orange-400 block mb-0.5">1. Confirmed Wasted Time</strong>
            Time you explicitly acknowledge losing to distractions, social media, phone scrolling, or procrastination.
          </div>
          <div className="p-2.5 rounded border" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <strong className="text-rose-400 block mb-0.5">2. Academic Target Shortfall</strong>
            The difference between the 240m target and actual study (e.g. 180m studied = 60m shortfall). Never auto-labeled as wasted!
          </div>
          <div className="p-2.5 rounded border" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <strong className="text-indigo-400 block mb-0.5">3. Unfinished Work</strong>
            Incomplete 45-minute shifts that are automatically rescheduled to future study windows.
          </div>
        </div>
      </div>

      {/* Top 3 Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="lc-card p-4 space-y-1.5 border-l-4 border-orange-500">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Confirmed Wasted Today</span>
          <div className="text-2xl font-black text-orange-400 font-mono">
            {today.confirmed_wasted_minutes || 0} <span className="text-xs font-normal text-slate-400">mins</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Target Shortfall: <strong className="text-rose-400">{today.academic_shortfall_minutes || 0}m</strong>
          </div>
        </div>

        <div className="lc-card p-4 space-y-1.5 border-l-4 border-amber-500">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Confirmed Wasted This Week</span>
          <div className="text-2xl font-black text-amber-400 font-mono">
            {week.confirmed_wasted_minutes || 0} <span className="text-xs font-normal text-slate-400">mins</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Week Shortfall: <strong className="text-rose-400">{week.academic_shortfall_minutes || 0}m</strong>
          </div>
        </div>

        <div className="lc-card p-4 space-y-1.5 border-l-4 border-rose-500">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Confirmed Wasted This Month</span>
          <div className="text-2xl font-black text-rose-400 font-mono">
            {month.confirmed_wasted_minutes || 0} <span className="text-xs font-normal text-slate-400">mins</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Month Shortfall: <strong className="text-rose-400">{month.academic_shortfall_minutes || 0}m</strong>
          </div>
        </div>
      </div>

      {/* Manual Logging Form & History Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Log Form */}
        <div className="lc-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            Log Unproductive Time
          </h3>

          <form onSubmit={handleLogSubmit} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Duration (minutes):</label>
              <input
                type="number"
                min="5"
                max="480"
                value={logMins}
                onChange={e => setLogMins(Number(e.target.value))}
                required
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Date:</label>
              <input
                type="date"
                value={logDate}
                onChange={e => setLogDate(e.target.value)}
                required
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Category / Reason:</label>
              <select
                value={logCategory}
                onChange={e => setLogCategory(e.target.value)}
                className="w-full"
              >
                <option value="Avoidable Distraction">Avoidable Distraction</option>
                <option value="Social Media Scrolling">Social Media Scrolling</option>
                <option value="Phone Call / Messaging">Phone Call / Messaging</option>
                <option value="Daydreaming / Inattention">Daydreaming / Inattention</option>
                <option value="Unplanned Long Break">Unplanned Long Break</option>
                <option value="Fatigue / Brain Fog">Fatigue / Brain Fog</option>
                <option value="Other">Other Unproductive Time</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Reflection Notes (Optional):</label>
              <textarea
                rows="3"
                value={logNotes}
                onChange={e => setLogNotes(e.target.value)}
                placeholder="What triggered this distraction? What can you do differently next time?"
                className="w-full text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="btn-primary text-xs font-bold w-full py-2"
            >
              {saving ? 'Logging...' : 'Save Wasted Time Entry'}
            </button>
          </form>
        </div>

        {/* Right: History Log Table */}
        <div className="lg:col-span-2 lc-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            Logged Wasted Time History
          </h3>

          {logs.length === 0 ? (
            <p className="p-8 text-center text-xs text-slate-400">No wasted time logs recorded yet.</p>
          ) : (
            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1 text-xs">
              {logs.map(log => (
                <div key={log.id} className="p-3 rounded-lg border flex items-center justify-between gap-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-200">{log.wasted_date}</span>
                      <span className="badge badge-warning text-[10px]">{log.category}</span>
                      <span className="font-mono font-bold text-orange-400">{log.minutes} mins</span>
                    </div>
                    {log.notes && (
                      <p className="text-[11px] text-slate-400 italic">{log.notes}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteLog(log.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 text-xs"
                    title="Delete log"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function DailyDSAView({ dailyDSA, onRefresh, showToast, showAppreciation }) {
  const [topics, setTopics] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [topicNotes, setTopicNotes] = useState({});

  // Question replacement modal state
  const [isReplaceModalOpen, setIsReplaceModalOpen] = useState(false);
  const [replacingAssignment, setReplacingAssignment] = useState(null);
  const [allQuestions, setAllQuestions] = useState([]);
  const [selectedReplacementId, setSelectedReplacementId] = useState('');

  const loadDSAData = async () => {
    setLoading(true);
    try {
      const [tRes, hRes] = await Promise.all([
        window.LastChanceAPI.getDSATopics(),
        window.LastChanceAPI.getAllDSA().catch(() => ({ assignments: [] }))
      ]);
      setTopics(tRes.topics || []);
      setHistory(hRes.assignments || []);
    } catch (e) {
      console.error(e);
      showToast('Failed to load DSA data: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDSAData();
  }, []);

  const handleReplaceSubmit = async () => {
    if (!replacingAssignment || !selectedReplacementId) return;
    try {
      await window.LastChanceAPI.replaceDSAQuestion(replacingAssignment.id, parseInt(selectedReplacementId));
      showToast('DSA question successfully replaced and saved!', 'success');
      setIsReplaceModalOpen(false);
      setReplacingAssignment(null);
      await loadDSAData();
      if (onRefresh) onRefresh();
    } catch (e) {
      showToast('Failed to replace question: ' + e.message, 'error');
    }
  };

  const openReplaceModal = async (assignment) => {
    setReplacingAssignment(assignment);
    try {
      const res = await window.LastChanceAPI.getAllDSAQuestions();
      setAllQuestions(res.questions || []);
      if (res.questions?.length > 0) setSelectedReplacementId(res.questions[0].id);
      setIsReplaceModalOpen(true);
    } catch (e) {
      showToast('Failed to load alternative questions: ' + e.message, 'error');
    }
  };

  const handleToggle = async (topic) => {
    const newStatus = topic.status === 'Completed' ? 'Pending' : 'Completed';
    try {
      await window.LastChanceAPI.updateDSATopic(topic.id, {
        status: newStatus,
        time_spent_minutes: topic.time_spent_minutes || 25,
        notes: topicNotes[topic.id] || topic.notes || ''
      });
      await loadDSAData();
      onRefresh();
      if (newStatus === 'Completed') {
        showAppreciation("Consistency milestone! DSA question completed.");
      } else {
        showToast('DSA topic updated.');
      }
    } catch (e) {
      showToast('Failed to update: ' + e.message, 'error');
    }
  };

  const solvedCount = topics.filter(t => t.status === 'Completed').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Daily DSA Commitment (2 Questions)
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Solve 2 questions daily from different Data Structures topics. Tracked separately outside the 4-hour academic target.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className={`text-xs px-3 py-1 rounded-full font-bold font-mono ${
            solvedCount >= 2 ? 'badge-success badge' : 'badge-warning badge'
          }`}>
            Today: {solvedCount} / 2 Solved
          </span>
        </div>
      </div>

      {/* Today's 2 Specific DSA Assignments Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {topics.map((t, idx) => {
          const isDone = t.status === 'Completed';
          return (
            <div
              key={t.id}
              className={`lc-card card-3d p-5 space-y-4 border-l-4 transition-smooth ${
                isDone ? 'border-emerald-500' : 'border-indigo-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider text-white bg-indigo-600 font-mono">
                    Slot #{t.slot_number || idx + 1}
                  </span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded text-indigo-300 bg-indigo-500/15 border border-indigo-500/30">
                    {t.syllabus_topic || t.topic_name}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase font-mono ${
                    t.difficulty === 'Easy' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    t.difficulty === 'Hard' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                    'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}>
                    {t.difficulty || 'Medium'}
                  </span>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase font-mono ${
                  isDone ? 'badge-success badge' : 'badge-warning badge'
                }`}>
                  {isDone ? '✓ Solved' : 'Pending'}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-100">{t.question_title || t.topic_name}</h3>
                {t.goal && (
                  <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                    Goal: {t.goal}
                  </p>
                )}
              </div>

              {t.problem_url && (
                <div>
                  <a
                    href={t.problem_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline"
                  >
                    <span>🔗 Open Verified Problem (LeetCode / GFG)</span>
                    <span>↗</span>
                  </a>
                </div>
              )}

              <div className="space-y-2 text-xs">
                <label className="block text-slate-300 font-medium">Problem Link / Solution Notes:</label>
                <input
                  type="text"
                  placeholder="Record solution approach, time complexity, or edge cases..."
                  value={topicNotes[t.id] !== undefined ? topicNotes[t.id] : (t.notes || '')}
                  onChange={e => setTopicNotes({ ...topicNotes, [t.id]: e.target.value })}
                  className="w-full"
                />
              </div>

              <div className="pt-2 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
                <button
                  type="button"
                  onClick={() => {
                    setReplacingAssignment(t);
                    setIsReplaceModalOpen(true);
                  }}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center space-x-1 text-slate-300 hover:text-white"
                  title="Replace with another syllabus question"
                >
                  <span>🔄</span>
                  <span>Replace Question</span>
                </button>

                <button
                  onClick={() => handleToggle(t)}
                  className={`px-4 py-2 rounded-lg text-xs font-bold transition-smooth ${
                    isDone
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
                      : 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-md'
                  }`}
                >
                  {isDone ? '✓ Mark as Unsolved' : 'Mark Question Solved'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* History Table */}
      <div className="lc-card p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
          DSA Completion History
        </h3>
        {history.length === 0 ? (
          <p className="p-6 text-center text-xs text-slate-400">No past DSA records yet.</p>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1 text-xs">
            {history.slice(0, 20).map(h => (
              <div key={h.id} className="p-2.5 rounded border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div className="space-y-0.5">
                  <span className="font-bold text-slate-200">{h.topic_name}</span>
                  <span className="block text-[10px] text-slate-400">{h.assigned_date}</span>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  h.status === 'Completed' ? 'badge-success badge' : 'badge-warning badge'
                }`}>
                  {h.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Replace Question Modal */}
      {isReplaceModalOpen && (
        <div className="modal-overlay" onClick={() => setIsReplaceModalOpen(false)}>
          <div className="modal-dialog p-5 space-y-4 max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <div>
                <h3 className="text-sm font-bold text-slate-100">Replace DSA Question</h3>
                <p className="text-[11px] text-slate-400">Select an alternative problem from the official syllabus repository</p>
              </div>
              <button onClick={() => setIsReplaceModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Choose Replacement Problem:</label>
                <select
                  value={selectedReplacementId}
                  onChange={e => setSelectedReplacementId(e.target.value)}
                  className="w-full text-xs"
                >
                  {allQuestions.map(q => (
                    <option key={q.id} value={q.id}>
                      [{q.syllabus_topic}] {q.question_title} ({q.difficulty})
                    </option>
                  ))}
                </select>
              </div>

              {selectedReplacementId && (() => {
                const q = allQuestions.find(item => String(item.id) === String(selectedReplacementId));
                if (!q) return null;
                return (
                  <div className="p-3 rounded-lg border space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-amber-400">{q.syllabus_topic}</span>
                      <span className="badge badge-info text-[9px]">{q.difficulty}</span>
                    </div>
                    <div className="font-bold text-sm text-slate-100">{q.question_title}</div>
                    <p className="text-slate-400 text-[11px]">{q.goal}</p>
                    {q.problem_url && (
                      <a href={q.problem_url} target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline block pt-1">
                        View Problem Description ↗
                      </a>
                    )}
                  </div>
                );
              })()}

              <div className="flex justify-end space-x-2 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
                <button type="button" onClick={() => setIsReplaceModalOpen(false)} className="btn-secondary">Cancel</button>
                <button type="button" onClick={handleReplaceSubmit} className="btn-primary">Confirm & Save Replacement</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 9. ENGLISH SPEAKING VIEW -----------------

function EnglishSpeakingView({ englishToday, onRefresh, showToast, showAppreciation }) {
  const [actualMinutes, setActualMinutes] = useState(
    englishToday?.log?.actual_minutes !== undefined ? englishToday.log.actual_minutes : (englishToday?.log?.time_spent_seconds ? Math.floor(englishToday.log.time_spent_seconds / 60) : 30)
  );
  const [practised, setPractised] = useState(englishToday?.log?.is_completed ? 'yes' : null);
  const [notes, setNotes] = useState(englishToday?.log?.topic_practiced || '');
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState([]);

  // Active Timer state
  const [timerRunning, setTimerRunning] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const loadHistory = async () => {
    try {
      const res = await window.LastChanceAPI.getEnglishHistory();
      setHistory(res.logs || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Timer Tick
  useEffect(() => {
    let interval = null;
    if (timerRunning) {
      interval = setInterval(() => {
        setElapsedSeconds(s => {
          const next = s + 1;
          setActualMinutes(Math.max(1, Math.round(next / 60)));
          return next;
        });
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [timerRunning]);

  const shortfall = Math.max(0, 30 - actualMinutes);

  const handleSave = async () => {
    setSaving(true);
    try {
      await window.LastChanceAPI.saveEnglishSimple({
        actual_minutes: actualMinutes,
        notes: notes || 'Daily practice'
      });
      await loadHistory();
      onRefresh();
      showAppreciation("Excellent dedication! English speaking practice saved.");
    } catch (e) {
      showToast('Failed to save: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const PROMPTS = [
    "Explain the concept of Proof by Induction as if teaching a classmate.",
    "Describe the difference between an Array and a Linked List.",
    "Explain how Prim's Algorithm finds a Minimum Spanning Tree.",
    "Discuss why polymorphism is useful in Object-Oriented Programming.",
    "Explain the difference between Supervised and Unsupervised Learning."
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            English Speaking Practice (Daily 30 Mins)
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Daily fluency and active explanation practice outside the 4-hour academic target. Explain concepts aloud or speak on a topic.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="badge badge-warning text-xs font-mono font-bold">
            🔥 {englishToday?.streak_days || 0} Days Streak
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Timer & Practice Log Form */}
        <div className="lg:col-span-2 lc-card p-5 space-y-5">
          {/* Active Speaking Timer Display */}
          <div className="p-6 rounded-2xl border text-center space-y-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 font-mono">
              Live Speaking Timer (Target: 30 Mins)
            </span>
            <div className="text-5xl font-black font-mono text-amber-400">
              {formatTimeSec(elapsedSeconds)}
            </div>
            <div className="flex justify-center space-x-3">
              <button
                onClick={() => {
                  setTimerRunning(!timerRunning);
                  setPractised('yes');
                }}
                className={`px-5 py-2 rounded-lg text-xs font-bold transition-smooth ${
                  timerRunning ? 'bg-amber-600 text-white' : 'btn-primary'
                }`}
              >
                {timerRunning ? '⏸️ Pause Timer' : '▶️ Start Speaking Timer'}
              </button>
              {elapsedSeconds > 0 && (
                <button
                  onClick={() => {
                    setTimerRunning(false);
                    setElapsedSeconds(0);
                  }}
                  className="btn-secondary text-xs py-2 px-3"
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Practice Entry */}
          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Actual Practice Minutes:</label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={actualMinutes}
                  onChange={e => setActualMinutes(Math.max(0, Number(e.target.value)))}
                  className="w-24 text-center font-mono font-bold"
                />
                <span className="text-slate-400">minutes</span>
                <span className={`font-mono font-bold ml-2 ${shortfall > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {shortfall > 0 ? `(${shortfall}m remaining)` : '(Target Achieved! ✓)'}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Topic Practiced / Reflection Notes:</label>
              <input
                type="text"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="e.g. Explained Binary Tree traversals and Dijkstra's algorithm aloud"
                className="w-full text-xs"
              />
            </div>

            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary text-xs font-bold w-full py-2.5"
            >
              {saving ? 'Saving...' : '✓ Save English Speaking Record'}
            </button>
          </div>
        </div>

        {/* Right 1 Col: Suggested Practice Prompts */}
        <div className="lc-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
            Suggested Speaking Topics
          </h3>
          <p className="text-xs text-slate-400">
            Pick one of these syllabus concepts and explain it aloud in clear English for 5 to 10 minutes:
          </p>
          <div className="space-y-2.5">
            {PROMPTS.map((p, i) => (
              <div
                key={i}
                onClick={() => setNotes(p)}
                className="p-3 rounded-lg border text-xs text-slate-200 hover:border-amber-500/50 cursor-pointer transition-smooth"
                style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}
              >
                <span className="text-amber-400 font-bold block mb-1">Topic #{i + 1}</span>
                {p}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}


function RevisionPlannerView({ dates, onRefresh, showToast }) {
  const [activeTab, setActiveTab] = useState('revision'); // 'revision' | 'doubts' | 'weekly_review'
  const [revisionData, setRevisionData] = useState(null);
  const [doubts, setDoubts] = useState([]);
  const [weeklyReview, setWeeklyReview] = useState(null);
  const [newDoubtText, setNewDoubtText] = useState('');
  const [newDoubtCourse, setNewDoubtCourse] = useState('Discrete Structures');
  const [savingDoubt, setSavingDoubt] = useState(false);

  const loadData = async () => {
    try {
      const [rRes, dRes, wRes] = await Promise.all([
        window.LastChanceAPI.getRevision().catch(() => null),
        window.LastChanceAPI.getDoubts('OPEN').catch(() => ({ doubts: [] })),
        window.LastChanceAPI.getWeeklyReview().catch(() => null)
      ]);
      setRevisionData(rRes);
      setDoubts(dRes.doubts || []);
      setWeeklyReview(wRes);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleResolveDoubt = async (doubtId) => {
    try {
      await window.LastChanceAPI.resolveDoubt(doubtId, 'Resolved in study session');
      showToast('Doubt marked resolved!', 'success');
      loadData();
    } catch (e) {
      showToast('Failed to resolve doubt: ' + e.message, 'error');
    }
  };

  const handleCreateDoubt = async (e) => {
    e.preventDefault();
    if (!newDoubtText.trim()) return;
    setSavingDoubt(true);
    try {
      await window.LastChanceAPI.addDoubt({
        doubt_text: newDoubtText.trim(),
        subject_name: newDoubtCourse
      });
      showToast('Doubt logged successfully!', 'success');
      setNewDoubtText('');
      loadData();
    } catch (e) {
      showToast('Failed to add doubt: ' + e.message, 'error');
    } finally {
      setSavingDoubt(false);
    }
  };

  const weakTopics = revisionData?.weak_topics || [];
  const bufferSessions = revisionData?.buffer_sessions || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Revision Queue, Doubts & Weekly Review
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Spaced review scheduling, weak-topic tracker, doubt resolution, and weekly consolidation reviews.
          </p>
        </div>

        <div className="flex items-center space-x-1.5 p-1 rounded-lg border text-xs" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('revision')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeTab === 'revision' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            🔄 Revision Queue ({weakTopics.length})
          </button>
          <button
            onClick={() => setActiveTab('doubts')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeTab === 'doubts' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            ❓ Doubts Log ({doubts.length})
          </button>
          <button
            onClick={() => setActiveTab('weekly_review')}
            className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
              activeTab === 'weekly_review' ? 'btn-primary' : 'text-slate-400 hover:text-white'
            }`}
          >
            📊 Weekly Review
          </button>
        </div>
      </div>

      {/* TAB 1: REVISION QUEUE & BUFFER */}
      {activeTab === 'revision' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="lc-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
              Weak Topics & Revision Queue
            </h3>
            <p className="text-xs text-slate-400">
              Topics rated Difficult, low-confidence, or explicitly flagged for review before first-pass deadline (19 Nov).
            </p>

            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {weakTopics.length === 0 ? (
                <p className="p-8 text-center text-xs text-slate-400">No topics currently flagged as weak. Keep up the high standards!</p>
              ) : (
                weakTopics.map(t => (
                  <div key={t.id} className="p-3 rounded-lg border space-y-1.5 text-xs" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200">{t.title}</span>
                      <span className="badge badge-warning text-[10px]">{t.mastery_level}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{t.subject_name}</span>
                      <span>Confidence: {t.lowest_confidence || 3}/5</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="lc-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
              Protected 7-Day Pre-Exam Revision Buffer
            </h3>
            <p className="text-xs text-slate-400">
              Guarantees zero new syllabus topics are scheduled during the final 7 days before exams (19 Nov - 26 Nov).
            </p>

            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {bufferSessions.length === 0 ? (
                <p className="p-8 text-center text-xs text-slate-400">Buffer sessions active in final 7-day period.</p>
              ) : (
                bufferSessions.map((b, i) => (
                  <div key={i} className="p-3 rounded-lg border text-xs space-y-1" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between font-bold text-indigo-400">
                      <span>{b.scheduled_date}</span>
                      <span>{b.subject_name}</span>
                    </div>
                    <div className="text-slate-200 font-semibold">{b.topic_title}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DOUBTS LOG */}
      {activeTab === 'doubts' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lc-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
              Log an Unresolved Doubt
            </h3>
            <form onSubmit={handleCreateDoubt} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Course:</label>
                <select
                  value={newDoubtCourse}
                  onChange={e => setNewDoubtCourse(e.target.value)}
                  className="w-full"
                >
                  <option value="Discrete Structures">Discrete Structures (CSN 3003)</option>
                  <option value="Data Structures">Data Structures (CSN 3001)</option>
                  <option value="Object-Oriented Programming">Object-Oriented Prog (CSN 3004)</option>
                  <option value="Data Science & ML">Data Science & ML (CSN 3002)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Doubt / Question Description:</label>
                <textarea
                  rows="4"
                  value={newDoubtText}
                  onChange={e => setNewDoubtText(e.target.value)}
                  placeholder="Describe what concept, proof, or code problem you got stuck on..."
                  required
                  className="w-full"
                />
              </div>

              <button
                type="submit"
                disabled={savingDoubt}
                className="btn-primary text-xs font-bold w-full py-2"
              >
                {savingDoubt ? 'Saving...' : '+ Add Doubt to Queue'}
              </button>
            </form>
          </div>

          <div className="lg:col-span-2 lc-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-100 border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
              Open Unresolved Doubts ({doubts.length})
            </h3>

            {doubts.length === 0 ? (
              <p className="p-8 text-center text-xs text-slate-400">All doubts resolved! Zero pending questions.</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto pr-1 text-xs">
                {doubts.map(d => (
                  <div key={d.id} className="p-3.5 rounded-lg border space-y-2" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-indigo-400">{d.subject_name || 'General'}</span>
                      <span className="badge badge-warning text-[10px]">{d.status}</span>
                    </div>
                    <p className="text-slate-200 font-medium leading-relaxed">{d.doubt_text}</p>
                    <div className="flex justify-between items-center pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                      <span className="text-[10px] text-slate-400">Logged on {d.created_at?.split('T')[0]}</span>
                      <button
                        onClick={() => handleResolveDoubt(d.id)}
                        className="btn-primary text-xs py-1 px-3"
                      >
                        ✓ Mark Resolved
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: WEEKLY REVIEW */}
      {activeTab === 'weekly_review' && (
        <div className="lc-card p-5 space-y-5 border-l-4 border-indigo-500">
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono">End-of-Week Review</span>
              <h3 className="text-base font-bold text-slate-100">{weeklyReview?.week_label || 'Current Week'}</h3>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-[10px] font-bold text-slate-400 uppercase">Academic Completed</span>
              <div className="text-xl font-black text-indigo-400 font-mono mt-1">{weeklyReview?.total_academic_hours || '0h'}</div>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-[10px] font-bold text-slate-400 uppercase">Shifts Completed</span>
              <div className="text-xl font-black text-emerald-400 font-mono mt-1">{weeklyReview?.completed_shifts || 0}</div>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-[10px] font-bold text-slate-400 uppercase">Confirmed Wasted</span>
              <div className="text-xl font-black text-rose-400 font-mono mt-1">{weeklyReview?.total_confirmed_wasted || 0}m</div>
            </div>
            <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-[10px] font-bold text-slate-400 uppercase">Daily Average</span>
              <div className="text-xl font-black text-amber-400 font-mono mt-1">{weeklyReview?.daily_average_minutes || 0}m</div>
            </div>
          </div>

          <div className="p-4 rounded-xl border space-y-2 text-xs" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <h4 className="font-bold text-indigo-400">Suggested Priorities for Coming Days:</h4>
            <ul className="list-disc list-inside space-y-1 text-slate-300">
              {weeklyReview?.suggested_priorities?.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- 10. STUDY HISTORY VIEW -----------------

function StudyHistoryView({ showToast }) {
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'TODAY' | 'WEEK' | 'MONTH'
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const res = await window.LastChanceAPI.getHistory();
      setHistory(res.sessions || []);
    } catch (e) {
      console.error(e);
      showToast('Failed to load history: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredHistory = history.filter(s => {
    if (filter === 'ALL') return true;
    const sessionDate = s.start_time?.split('T')[0] || s.scheduled_date;
    const today = new Date().toISOString().split('T')[0];
    if (filter === 'TODAY') return sessionDate === today;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            Recorded Study Sessions History
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Audit log of all completed academic focus sessions, durations, and confidence ratings
          </p>
        </div>

        <div className="flex items-center space-x-1.5 p-1 rounded-lg border text-xs" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          {['ALL', 'TODAY'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md font-semibold transition-smooth ${
                filter === f ? 'btn-primary' : 'text-slate-400 hover:text-white'
              }`}
            >
              {f === 'ALL' ? 'All Sessions' : 'Today'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="p-8 text-center text-xs text-slate-400">Loading session history...</p>
      ) : filteredHistory.length === 0 ? (
        <div className="lc-card p-12 text-center text-xs text-slate-400">
          No study sessions found for the selected filter.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredHistory.map(s => (
            <div key={s.id} className="lc-card p-4 space-y-2 border-l-4 border-indigo-500 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-white px-2 py-0.5 rounded text-[10px]" style={{ backgroundColor: s.subject_color || '#4f46e5' }}>
                    {s.subject_code || 'STUDY'}
                  </span>
                  <span className="font-bold text-slate-200">{s.topic_title || s.subject_name}</span>
                </div>
                <span className="font-mono text-indigo-400 font-bold">
                  ⏱️ {s.duration_minutes || s.actual_minutes} actual mins
                </span>
              </div>

              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400">
                <span>Start: {s.start_time ? s.start_time.replace('T', ' ') : s.scheduled_date}</span>
                {s.confidence_rating && <span>Confidence: {s.confidence_rating}/5</span>}
              </div>

              {s.notes && (
                <p className="text-[11px] text-slate-300 italic pt-1 border-t" style={{ borderColor: 'var(--border-color)' }}>
                  "{s.notes}"
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ----------------- 11. SETTINGS VIEW -----------------

function SettingsView({ settings, onRefresh, showToast }) {
  const [priorityRules, setPriorityRules] = useState([
    "1. Discrete Structures (CSN 3003) is #1 highest priority after 27 Oct OOP Quiz.",
    "2. Focus on unfinished Discrete Structures Unit 2 onward, then cover earlier gaps.",
    "3. Keep all 4 courses active: Discrete Structures, Data Structures, OOP, DSML.",
    "4. Target first complete syllabus pass by 19 November 2026.",
    "5. Use 20 November for consolidation, error-log repair, and closing gaps."
  ]);
  const [exporting, setExporting] = useState(false);
  const [restoreFile, setRestoreFile] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [syncingTimetable, setSyncingTimetable] = useState(false);

  const handleExportBackup = async () => {
    setExporting(true);
    try {
      const data = await window.LastChanceAPI.exportBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `lastchance_backup_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Database backup exported successfully!', 'success');
    } catch (e) {
      showToast('Export failed: ' + e.message, 'error');
    } finally {
      setExporting(false);
    }
  };

  const handleRestoreBackup = async () => {
    if (!restoreFile) {
      showToast('Please select a backup JSON file first', 'error');
      return;
    }
    if (!window.confirm('Restore database from this backup? Current data will be safely backed up first.')) return;
    setRestoring(true);
    try {
      const text = await restoreFile.text();
      const data = JSON.parse(text);
      await window.LastChanceAPI.restoreBackup(data);
      showToast('Backup restored successfully!', 'success');
      onRefresh();
      setRestoreFile(null);
    } catch (e) {
      showToast('Restore failed: ' + e.message, 'error');
    } finally {
      setRestoring(false);
    }
  };

  const handleReimportTimetable = async () => {
    if (!window.confirm('Sync/Re-import the official 25-day timetable? Existing completed sessions will be preserved.')) return;
    setSyncingTimetable(true);
    try {
      const res = await window.LastChanceAPI.importOfficialTimetable();
      showToast(res.message, 'success');
      onRefresh();
    } catch (e) {
      showToast('Sync failed: ' + e.message, 'error');
    } finally {
      setSyncingTimetable(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          Application Settings & System Preferences
        </h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Configure study priorities, safe local data backups, and timetable synchronisation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Priority Rules Card */}
        <div className="lc-card p-5 space-y-4 border-l-4 border-indigo-500">
          <h3 className="text-sm font-bold text-slate-100">
            Personalized Academic Priority System
          </h3>
          <p className="text-xs text-slate-400">
            These rules govern automatic rescheduling and timetable workload allocation:
          </p>
          <div className="p-3 rounded-lg border space-y-2 text-xs" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            {priorityRules.map((r, i) => (
              <div key={i} className="text-slate-200 font-medium">
                {r}
              </div>
            ))}
          </div>
        </div>

        {/* Timetable Sync & Reset Card */}
        <div className="lc-card p-5 space-y-4 border-l-4 border-emerald-500">
          <h3 className="text-sm font-bold text-slate-100">
            Official Word Timetable Management
          </h3>
          <p className="text-xs text-slate-400">
            Sync or repair the imported timetable (27 Oct – 20 Nov 2026). Prevents duplicates and preserves your completed sessions.
          </p>
          <button
            onClick={handleReimportTimetable}
            disabled={syncingTimetable}
            className="btn-primary text-xs font-bold py-2 px-4"
          >
            {syncingTimetable ? 'Syncing Timetable...' : '📥 Re-Sync Official Timetable'}
          </button>
        </div>

        {/* Data Backup & Restore Card */}
        <div className="lg:col-span-2 lc-card p-5 space-y-4 border-l-4 border-amber-500">
          <h3 className="text-sm font-bold text-slate-100">
            Data Safety, Backup & Restore
          </h3>
          <p className="text-xs text-slate-400">
            Export a full JSON backup of your database records, or restore from a previous backup file. A safe local copy is always preserved.
          </p>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 pt-2">
            <button
              onClick={handleExportBackup}
              disabled={exporting}
              className="btn-primary text-xs font-bold py-2 px-4"
            >
              {exporting ? 'Exporting...' : '💾 Export Complete JSON Backup'}
            </button>

            <div className="flex items-center space-x-2">
              <input
                type="file"
                accept=".json"
                onChange={e => setRestoreFile(e.target.files[0])}
                className="text-xs"
              />
              <button
                onClick={handleRestoreBackup}
                disabled={restoring || !restoreFile}
                className="btn-secondary text-xs font-bold py-1.5 px-3"
              >
                {restoring ? 'Restoring...' : 'Restore from File'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


function FocusModeModal({ task, onClose, showToast, showAppreciation }) {
  const targetMinutes = task.duration_minutes || 45;
  const targetSeconds = targetMinutes * 60;

  const [isRunning, setIsRunning] = useState(true);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isBreak, setIsBreak] = useState(false);
  const [breakSeconds, setBreakSeconds] = useState(300); // 5 min break
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(4);
  const [showOvertimePrompt, setShowOvertimePrompt] = useState(false);

  // Timestamp-based accurate elapsed tracking
  const startTimeRef = useRef(Date.now());
  const pausedTimeRef = useRef(0);
  const pauseStartRef = useRef(null);

  useEffect(() => {
    let animId = null;

    const tick = () => {
      if (isRunning && !isBreak) {
        const now = Date.now();
        const totalElapsed = Math.floor((now - startTimeRef.current - pausedTimeRef.current) / 1000);
        setElapsedSeconds(totalElapsed);

        if (totalElapsed >= targetSeconds && !showOvertimePrompt) {
          setShowOvertimePrompt(true);
        }
      } else if (isRunning && isBreak) {
        setBreakSeconds(s => Math.max(0, s - 1));
      }
      animId = setTimeout(tick, 500);
    };

    animId = setTimeout(tick, 500);
    return () => clearTimeout(animId);
  }, [isRunning, isBreak, showOvertimePrompt, targetSeconds]);

  const togglePause = () => {
    if (isRunning) {
      pauseStartRef.current = Date.now();
      setIsRunning(false);
    } else {
      if (pauseStartRef.current) {
        pausedTimeRef.current += (Date.now() - pauseStartRef.current);
        pauseStartRef.current = null;
      }
      setIsRunning(true);
    }
  };

  const handleFinishSession = async (customMins = null) => {
    try {
      const actualMinutes = customMins || Math.max(1, Math.round(elapsedSeconds / 60));
      await window.LastChanceAPI.completeShift(task.id, {
        actual_minutes: actualMinutes,
        confidence_rating: confidence,
        notes: notes || 'Completed via Focus Mode'
      });
      showAppreciation("Outstanding focus! Study session completed and verified in records.");
      onClose();
    } catch (e) {
      showToast('Failed to save session: ' + e.message, 'error');
    }
  };

  const handleStopEarly = async () => {
    const actualMinutes = Math.max(1, Math.round(elapsedSeconds / 60));
    if (actualMinutes >= targetMinutes) {
      handleFinishSession();
      return;
    }
    const remaining = targetMinutes - actualMinutes;
    if (window.confirm(`Stop early after ${actualMinutes} mins? The remaining ${remaining} mins will be scheduled to your backlog.`)) {
      try {
        await window.LastChanceAPI.partialShift(task.id, {
          actual_minutes: actualMinutes,
          reschedule_date: null,
          reason: 'Stopped early from focus mode'
        });
        showToast(`Recorded ${actualMinutes}m completed and scheduled remaining ${remaining}m.`, 'success');
        onClose();
      } catch (e) {
        showToast('Notice: ' + e.message, 'error');
      }
    }
  };

  const remainingSeconds = Math.max(0, targetSeconds - elapsedSeconds);
  const isOvertime = elapsedSeconds > targetSeconds;

  return (
    <div className="modal-overlay">
      <div className="modal-dialog p-6 space-y-5 text-center max-w-lg">
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 font-mono">
              45-Minute Focus Session
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 font-mono">
              Timestamp-Accurate
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        {/* Task Details */}
        <div className="space-y-1">
          <span className="text-xs font-bold px-2 py-0.5 rounded text-white" style={{ backgroundColor: task.subject_color || '#4f46e5' }}>
            {task.subject_code || 'STUDY'} • Unit {task.unit_number || 1}
          </span>
          <h3 className="text-base font-bold text-slate-100 mt-1">
            {task.task_description || task.topic_title}
          </h3>
        </div>

        {/* Big Timer Display */}
        <div className="p-6 rounded-2xl border text-center space-y-2" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
          {isBreak ? (
            <div>
              <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Short Rest Break</span>
              <div className="text-5xl font-black font-mono text-cyan-400">
                {formatTimeSec(breakSeconds)}
              </div>
            </div>
          ) : (
            <div>
              <div className={`text-5xl font-black font-mono tracking-tight ${isOvertime ? 'text-amber-400' : 'text-indigo-400'}`}>
                {isOvertime ? `+${formatTimeSec(elapsedSeconds - targetSeconds)}` : formatTimeSec(remainingSeconds)}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Elapsed: <strong className="font-mono text-slate-200">{formatTimeSec(elapsedSeconds)}</strong> • Target: {targetMinutes}m
              </div>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={togglePause}
            className={`px-5 py-2 rounded-lg text-xs font-bold transition-smooth ${
              isRunning ? 'bg-amber-600 text-white hover:bg-amber-500' : 'btn-primary'
            }`}
          >
            {isRunning ? '⏸️ Pause' : '▶️ Resume'}
          </button>

          <button
            onClick={() => {
              setIsBreak(!isBreak);
              if (!isBreak) setBreakSeconds(300);
            }}
            className="btn-secondary text-xs py-2 px-3.5 font-semibold"
          >
            {isBreak ? 'End Break' : '☕ 5m Break'}
          </button>

          <button
            onClick={handleStopEarly}
            className="btn-secondary text-xs py-2 px-3.5 font-semibold text-rose-400 hover:text-rose-300"
          >
            ⏹️ Stop Early
          </button>
        </div>

        {/* Overtime notification if applicable */}
        {showOvertimePrompt && (
          <div className="p-3 rounded-lg border bg-amber-500/10 border-amber-500/30 text-amber-300 text-xs text-left">
            <strong>Target 45m Reached!</strong> Would you like to complete and save now, or continue studying in overtime?
          </div>
        )}

        {/* Observations & Confidence Rating */}
        <div className="space-y-3 text-left text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">Confidence Rating (1 to 5):</label>
            <select
              value={confidence}
              onChange={e => setConfidence(Number(e.target.value))}
              className="w-full text-xs"
            >
              <option value="1">1 - Struggled / Confused</option>
              <option value="2">2 - Partially Understood</option>
              <option value="3">3 - Moderate Comprehension</option>
              <option value="4">4 - Confident & Clear</option>
              <option value="5">5 - Mastered</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Session Recall Notes / Mistakes:</label>
            <textarea
              rows="2"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Record key definitions, formulas, or proof steps..."
              className="w-full text-xs"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
          <button onClick={onClose} className="btn-secondary text-xs">Cancel</button>
          <button
            onClick={() => handleFinishSession()}
            className="btn-primary text-xs font-bold py-2 px-4"
          >
            ✓ Complete & Save Shift
          </button>
        </div>
      </div>
    </div>
  );
}

// ----------------- PARTIAL COMPLETE MODAL -----------------

function PartialCompleteModal({ task, onClose, onSuccess, showToast }) {
  const plannedMinutes = task.duration_minutes || 45;
  const [actualMinutes, setActualMinutes] = useState(20);
  const [reason, setReason] = useState('College schedule / shortage of time');
  const [saving, setSaving] = useState(false);

  const remaining = Math.max(0, plannedMinutes - actualMinutes);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (actualMinutes <= 0 || actualMinutes >= plannedMinutes) {
      showToast('Actual minutes must be less than planned duration', 'error');
      return;
    }
    setSaving(true);
    try {
      await window.LastChanceAPI.partialShift(task.id, {
        actual_minutes: actualMinutes,
        reschedule_date: null,
        reason: reason
      });
      onSuccess();
    } catch (e) {
      showToast('Failed to record partial session: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-sm font-bold text-slate-100">Record Partial Shift (Stop Early)</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        <div className="space-y-1">
          <div className="text-xs text-indigo-400 font-bold">{task.subject_code} • SHIFT {task.shift_number || 1}</div>
          <div className="text-sm font-bold text-slate-200">{task.task_description || task.topic_title}</div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">
              Actual Minutes Studied (Planned: {plannedMinutes}m):
            </label>
            <input
              type="number"
              min="5"
              max={plannedMinutes - 1}
              value={actualMinutes}
              onChange={e => setActualMinutes(Number(e.target.value))}
              required
              className="w-full text-center font-mono font-bold"
            />
          </div>

          <div className="p-3 rounded-lg border bg-indigo-500/10 border-indigo-500/30 text-indigo-300">
            <strong>Automatic Split:</strong> {actualMinutes} mins will be credited to today's study records. The remaining <strong className="text-amber-400 font-mono font-bold">{remaining} mins</strong> will be scheduled to future study slots.
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Reason for Stopping Early:</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="w-full"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <button type="button" onClick={onClose} className="btn-secondary text-xs">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary text-xs font-bold">
              {saving ? 'Saving...' : 'Save & Reschedule Remaining'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ----------------- RESCHEDULE MODAL -----------------

function RescheduleModal({ task, onClose, onSuccess, showToast }) {
  const [newDate, setNewDate] = useState('2026-10-28');
  const [reason, setReason] = useState('Heavy college schedule');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newDate) return;
    setSaving(true);
    try {
      await window.LastChanceAPI.rescheduleShift(task.id, {
        new_date: newDate,
        reason: reason
      });
      onSuccess();
    } catch (e) {
      showToast('Failed to reschedule: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-sm font-bold text-slate-100">Reschedule Study Shift</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        <div className="space-y-1 text-xs">
          <div className="text-indigo-400 font-bold">{task.subject_code} • SHIFT {task.shift_number || 1}</div>
          <div className="text-sm font-bold text-slate-200">{task.task_description || task.topic_title}</div>
          <div className="text-slate-400">Original Planned Date: <strong className="font-mono text-slate-300">{task.original_date || task.scheduled_date}</strong></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">Select New Scheduled Date:</label>
            <input
              type="date"
              value={newDate}
              onChange={e => setNewDate(e.target.value)}
              required
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Reason for Moving Shift:</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="e.g. Lab assignment, college event, fatigue"
              className="w-full"
            />
          </div>

          <div className="p-2.5 rounded border text-[11px] text-slate-400" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            Note: Original planned date is preserved in history and can be undone at any time.
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <button type="button" onClick={onClose} className="btn-secondary text-xs">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary text-xs font-bold">
              {saving ? 'Moving...' : 'Reschedule Shift'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ----------------- INTERRUPTION MODAL -----------------

function InterruptionModal({ task, onClose, onSuccess, showToast }) {
  const [interruptionNotes, setInterruptionNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await window.LastChanceAPI.completeTask(task.id, {
        status: 'PARTIALLY_COMPLETED',
        actual_minutes: 15,
        notes: `Interrupted: ${interruptionNotes}`
      });
      onSuccess();
    } catch (e) {
      showToast('Notice: ' + e.message, 'info');
      onSuccess();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-sm" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-bold text-slate-100">Report Shift Interruption</h3>
        <p className="text-xs text-slate-400">Record unexpected disruptions (power cut, phone call, emergency) to account for time honestly.</p>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">Interruption Note:</label>
            <textarea
              rows="3"
              value={interruptionNotes}
              onChange={e => setInterruptionNotes(e.target.value)}
              placeholder="What interrupted this session?"
              required
              className="w-full text-xs"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-xs">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary text-xs font-bold">Log Interruption</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ----------------- DOUBT MODAL -----------------

function DoubtModal({ task, onClose, onSuccess, showToast }) {
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    try {
      await window.LastChanceAPI.addDoubt({
        doubt_text: text.trim(),
        subject_name: task.subject_name || 'General',
        topic_id: task.topic_id || null,
        schedule_id: task.id || null
      });
      onSuccess();
    } catch (e) {
      showToast('Failed to save doubt: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-sm font-bold text-slate-100">Attach Doubt / Recall Note</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <div className="text-xs text-indigo-400 font-bold">
          {task.subject_code} • {task.task_description || task.topic_title}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <textarea
            rows="3"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Write down what you got stuck on or need to clarify with professor..."
            required
            className="w-full text-xs"
          />

          <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <button type="button" onClick={onClose} className="btn-secondary text-xs">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary text-xs font-bold">Save Doubt</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ----------------- FAVORITE QUOTES MODAL -----------------

function FavoriteQuotesModal({ onClose, showToast }) {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadFavs = async () => {
    try {
      const res = await window.LastChanceAPI.getFavoriteQuotes();
      setFavorites(res.favorites || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFavs();
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-lg" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <h3 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <span>⭐</span>
            <span>Saved Favorite Quotes</span>
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        {loading ? (
          <p className="p-6 text-center text-xs text-slate-400">Loading saved quotes...</p>
        ) : favorites.length === 0 ? (
          <p className="p-8 text-center text-xs text-slate-400">No favorite quotes saved yet. Click the star icon on any daily quote to bookmark it!</p>
        ) : (
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1 text-xs">
            {favorites.map(f => (
              <div key={f.id} className="p-3.5 rounded-lg border space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <p className="text-slate-200 italic font-medium leading-relaxed">"{f.quote_text}"</p>
                <div className="text-[10px] text-indigo-400 text-right">— {f.author || 'Anonymous'}</div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
          <button onClick={onClose} className="btn-secondary text-xs">Close</button>
        </div>
      </div>
    </div>
  );
}

// ----------------- SESSION HISTORY AUDIT MODAL -----------------

function SessionHistoryModal({ onClose }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    window.LastChanceAPI.getHistory().then(res => {
      setSessions(res.sessions || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-5 space-y-4 max-w-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono">Audited Session Log</span>
            <h3 className="text-base font-bold text-slate-100">Calculated Study Time Verification</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        <p className="text-xs text-slate-400">
          Every completed study session is persistently recorded with exact start/end timestamps and active duration (excluding pauses).
        </p>

        {loading ? (
          <p className="p-8 text-center text-xs text-slate-400">Loading audit records...</p>
        ) : sessions.length === 0 ? (
          <p className="p-8 text-center text-xs text-slate-400">No completed sessions logged yet. Your study history will appear here as you complete shifts.</p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1 text-xs">
            {sessions.map(s => (
              <div key={s.id} className="p-3 rounded-lg border flex items-center justify-between gap-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div className="space-y-0.5">
                  <div className="font-bold text-slate-200">{s.topic_title || s.subject_name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {s.start_time ? s.start_time.replace('T', ' ') : s.scheduled_date}
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-mono font-bold text-indigo-400 text-sm">
                    {s.duration_minutes || s.actual_minutes} mins
                  </span>
                  {s.confidence_rating && (
                    <span className="block text-[10px] text-slate-400">Confidence: {s.confidence_rating}/5</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
          <button onClick={onClose} className="btn-secondary text-xs">Close</button>
        </div>
      </div>
    </div>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("[Last Chance ErrorBoundary caught an error]", error, errorInfo);
    if (typeof window.displayFatalError === 'function') {
      window.displayFatalError(error);
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-slate-950 text-slate-100 font-sans">
          <div className="max-w-lg w-full p-6 rounded-xl border border-rose-500/30 bg-slate-900 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <span className="text-2xl">⚠️</span>
              <h2 className="text-lg font-bold">Component Render Error</h2>
            </div>
            <p className="text-xs text-slate-300">
              An error occurred while rendering this view. The application caught it safely.
            </p>
            <pre className="p-3 rounded bg-slate-950 text-rose-300 font-mono text-xs overflow-x-auto border border-rose-900/40 whitespace-pre-wrap break-all">
              {this.state.error?.stack || this.state.error?.message || String(this.state.error)}
            </pre>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-semibold text-white transition-colors"
              >
                Reload Dashboard
              </button>
              <button
                onClick={() => { localStorage.clear(); window.location.reload(); }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-xs text-slate-300 border border-slate-700 transition-colors"
              >
                Clear Cache & Reload
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// Render into DOM
const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
  window.__appRendered = true;
}



// =========================================================================
// REDO / PRACTICE AGAIN QUEUE VIEW
// =========================================================================
function RedoQueueView({ onStartSession, onRefresh, showToast, showAppreciation }) {
  const [redoTasks, setRedoTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [courseFilter, setCourseFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    topic_name: '',
    course_name: 'Discrete Structures',
    unit_number: 1,
    priority: 'HIGH',
    reason: 'Exam preparation revision'
  });

  const loadRedo = async () => {
    setLoading(true);
    try {
      const c = courseFilter === 'ALL' ? null : courseFilter;
      const s = statusFilter === 'ALL' ? null : statusFilter;
      const res = await window.LastChanceAPI.getRedoTasks(s, c);
      setRedoTasks(res.redo_tasks || []);
    } catch (e) {
      console.error(e);
      showToast('Failed to load redo queue: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRedo();
  }, [courseFilter, statusFilter]);

  const handleComplete = async (id, taskName) => {
    try {
      await window.LastChanceAPI.completeRedoTask(id);
      showAppreciation(`Redo completed for "${taskName}"! Solid revision progress.`);
      loadRedo();
      if (onRefresh) onRefresh();
    } catch (e) {
      showToast('Failed to complete redo task: ' + e.message, 'error');
    }
  };

  const handlePostpone = async (id) => {
    try {
      await window.LastChanceAPI.updateRedoTask(id, { status: 'POSTPONED' });
      showToast('Task postponed to later date.', 'info');
      loadRedo();
    } catch (e) {
      showToast('Failed to postpone: ' + e.message, 'error');
    }
  };

  const handleDelete = async (id, taskName) => {
    if (!window.confirm(`Are you sure you want to remove "${taskName}" from the Redo queue?`)) return;
    try {
      await window.LastChanceAPI.deleteRedoTask(id);
      showToast('Removed from redo queue.', 'info');
      loadRedo();
    } catch (e) {
      showToast('Failed to delete: ' + e.message, 'error');
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!addForm.topic_name.trim()) {
      showToast('Please enter a topic name', 'error');
      return;
    }
    try {
      await window.LastChanceAPI.addRedoTask({
        topic_name: addForm.topic_name.trim(),
        course_name: addForm.course_name,
        unit_number: parseInt(addForm.unit_number) || 1,
        priority: addForm.priority,
        reason: addForm.reason
      });
      showToast('Task queued for Redo!', 'success');
      setIsAddModalOpen(false);
      setAddForm({ topic_name: '', course_name: 'Discrete Structures', unit_number: 1, priority: 'HIGH', reason: 'Exam preparation revision' });
      loadRedo();
    } catch (err) {
      showToast('Failed to add redo task: ' + err.message, 'error');
    }
  };

  const pendingCount = redoTasks.filter(t => t.status === 'PENDING' || t.status === 'IN_PROGRESS').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30 uppercase tracking-wider font-mono">
              Spaced Repetition & Revision
            </span>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>• Zero Syllabus Inflation</span>
          </div>
          <h2 className="text-lg font-bold mt-0.5" style={{ color: 'var(--text-primary)' }}>
            Redo / Practice Again Queue
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Topics flagged for deliberate second-pass practice. Preserves original completion history without double-counting academic syllabus hours.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="badge badge-redo text-xs px-3 py-1 font-mono font-bold">
            {pendingCount} Pending Redo{pendingCount !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="btn-primary text-xs font-bold py-1.5 px-3 flex items-center space-x-1"
          >
            <span>+</span>
            <span>Add Custom Redo</span>
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setCourseFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-smooth ${courseFilter === 'ALL' ? 'btn-primary' : 'btn-secondary text-slate-300'}`}
          >
            All Courses
          </button>
          {['Discrete Structures', 'Data Structures', 'OOP', 'Data Science & ML'].map(c => (
            <button
              key={c}
              onClick={() => setCourseFilter(c)}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-smooth ${courseFilter === c ? 'btn-primary' : 'btn-secondary text-slate-300'}`}
            >
              {c.split(' ')[0]}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-slate-400">Status:</span>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="py-1 px-2.5 rounded border text-xs"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
            <option value="POSTPONED">Postponed</option>
          </select>
        </div>
      </div>

      {/* Redo Items List */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-400">Loading Redo queue...</div>
      ) : redoTasks.length === 0 ? (
        <div className="lc-card p-12 text-center space-y-3">
          <div className="text-4xl">🔁</div>
          <h3 className="text-sm font-bold text-slate-200">Redo Queue is Clear</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            When completing any study shift, choose "Complete & Add to Redo" to schedule hard topics for revision.
          </p>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="btn-primary text-xs font-bold py-2 px-4"
          >
            + Add First Redo Topic
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {redoTasks.map(t => {
            const isCompleted = t.status === 'COMPLETED';
            return (
              <div
                key={t.id}
                className={`lc-card card-3d p-4 space-y-3 flex flex-col justify-between border-l-4 ${
                  isCompleted ? 'border-emerald-500 opacity-70' :
                  t.priority === 'HIGH' ? 'border-rose-500' : 'border-amber-500'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded text-white bg-indigo-600 font-mono">
                      {t.course_name} • Unit {t.unit_number}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase font-mono ${
                      isCompleted ? 'badge-success badge' :
                      t.status === 'IN_PROGRESS' ? 'badge-info badge' : 'badge-warning badge'
                    }`}>
                      {t.status}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-slate-100">{t.topic_name}</h4>
                    {t.reason && (
                      <p className="text-xs text-amber-300/90 mt-1 italic">
                        Reason: {t.reason}
                      </p>
                    )}
                  </div>

                  <div className="text-[10px] text-slate-400 space-y-0.5 pt-1 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    <div>Added: {t.added_date}</div>
                    {t.original_completed_date && <div>First Completed: {t.original_completed_date}</div>}
                    <div>Revision Attempts: <span className="font-bold text-slate-200">{t.attempts_count || 1}</span></div>
                  </div>
                </div>

                <div className="pt-2 border-t flex items-center justify-between gap-2" style={{ borderColor: 'var(--border-color)' }}>
                  {!isCompleted ? (
                    <>
                      <button
                        onClick={() => onStartSession({
                          title: `[Redo] ${t.topic_name}`,
                          topic_title: t.topic_name,
                          subject_name: t.course_name,
                          duration_minutes: 45
                        })}
                        className="btn-primary text-xs font-bold py-1 px-2.5 flex-1"
                      >
                        ⏱️ Start Redo
                      </button>
                      <button
                        onClick={() => handleComplete(t.id, t.topic_name)}
                        className="btn-secondary text-xs font-bold py-1 px-2.5 text-emerald-400 hover:text-emerald-300"
                        title="Mark Redo Complete"
                      >
                        ✓ Done
                      </button>
                      <button
                        onClick={() => handlePostpone(t.id)}
                        className="btn-secondary text-xs py-1 px-2 text-slate-400"
                        title="Postpone"
                      >
                        Later
                      </button>
                    </>
                  ) : (
                    <span className="text-xs font-bold text-emerald-400">✓ Revision Completed</span>
                  )}
                  <button
                    onClick={() => handleDelete(t.id, t.topic_name)}
                    className="text-xs text-rose-400 hover:text-rose-300 p-1"
                    title="Remove from queue"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Custom Redo Modal */}
      {isAddModalOpen && (
        <div className="modal-overlay" onClick={() => setIsAddModalOpen(false)}>
          <div className="modal-dialog p-5 space-y-4 max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-sm font-bold text-slate-100">Add Topic to Redo Queue</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Topic Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Master Theorem or Dijkstra Algorithm"
                  value={addForm.topic_name}
                  onChange={e => setAddForm({ ...addForm, topic_name: e.target.value })}
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Course</label>
                  <select
                    value={addForm.course_name}
                    onChange={e => setAddForm({ ...addForm, course_name: e.target.value })}
                    className="w-full"
                  >
                    <option value="Discrete Structures">Discrete Structures (CSN 3003)</option>
                    <option value="Data Structures">Data Structures (CSN 3001)</option>
                    <option value="OOP">OOP (CSN 3004)</option>
                    <option value="Data Science & ML">Data Science & ML (CSN 3002)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Unit Number</label>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    value={addForm.unit_number}
                    onChange={e => setAddForm({ ...addForm, unit_number: e.target.value })}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Priority</label>
                <select
                  value={addForm.priority}
                  onChange={e => setAddForm({ ...addForm, priority: e.target.value })}
                  className="w-full"
                >
                  <option value="HIGH">HIGH (Urgent Revision)</option>
                  <option value="MEDIUM">MEDIUM (Standard Practice)</option>
                  <option value="LOW">LOW (Casual Review)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Reason for Redo</label>
                <input
                  type="text"
                  placeholder="e.g. Needs proof practice before exams"
                  value={addForm.reason}
                  onChange={e => setAddForm({ ...addForm, reason: e.target.value })}
                  className="w-full"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
                <button type="button" onClick={() => setIsAddModalOpen(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Queue for Redo</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// AUTH / USER PROFILE MODAL (CROSS-DEVICE PERSISTENCE)
// =========================================================================
function AuthModal({ currentUser, onLoginSuccess, onLogout, onClose, showToast }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      showToast('Please provide both username and password', 'error');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'login') {
        const res = await window.LastChanceAPI.login(username.trim(), password);
        localStorage.setItem('lc_token', res.access_token);
        onLoginSuccess(res.user);
      } else {
        const res = await window.LastChanceAPI.register({
          username: username.trim(),
          password: password,
          full_name: fullName.trim() || username.trim()
        });
        localStorage.setItem('lc_token', res.access_token);
        onLoginSuccess(res.user);
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog p-6 space-y-4 max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <div className="flex items-center space-x-2.5">
            <img src="/static/assets/logo_badge.png" alt="Logo" className="w-7 h-7 rounded-lg" />
            <div>
              <h3 className="text-base font-bold text-slate-100">
                {currentUser ? 'User Account & Sync' : mode === 'login' ? 'Sign In to Last Chance' : 'Create Personal Account'}
              </h3>
              <p className="text-[10px] text-amber-500 font-semibold">DURABLE CLOUD PERSISTENCE</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        {currentUser ? (
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl border space-y-2" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Logged in as:</span>
                <span className="font-bold text-amber-400 text-sm">{currentUser.username}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Full Name:</span>
                <span className="text-slate-200">{currentUser.full_name || 'Personal Study Admin'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Database Engine:</span>
                <span className="font-mono text-emerald-400">SQLite (Dev) / PostgreSQL (Prod)</span>
              </div>
            </div>

            <p className="text-slate-400 leading-relaxed text-[11px]">
              Your study timetable, progress, completed tasks, and redo queue are automatically synced to the server database.
            </p>

            <div className="flex justify-between items-center pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button onClick={onClose} className="btn-secondary">Close</button>
              <button onClick={onLogout} className="px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/40">
                Sign Out
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            {mode === 'register' && (
              <div>
                <label className="block text-slate-300 font-medium mb-1">Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. Aman"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  className="w-full"
                />
              </div>
            )}

            <div>
              <label className="block text-slate-300 font-medium mb-1">Username *</label>
              <input
                type="text"
                required
                placeholder="Choose username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Password *</label>
              <input
                type="password"
                required
                placeholder="Enter secure password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full"
              />
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full py-2 font-bold"
              >
                {loading ? 'Authenticating...' : mode === 'login' ? 'Sign In & Sync' : 'Register Account'}
              </button>

              <div className="text-center text-[11px] text-slate-400 pt-1">
                {mode === 'login' ? (
                  <span>
                    No account yet?{' '}
                    <button type="button" onClick={() => setMode('register')} className="text-amber-400 font-bold hover:underline">
                      Create personal account
                    </button>
                  </span>
                ) : (
                  <span>
                    Already registered?{' '}
                    <button type="button" onClick={() => setMode('login')} className="text-amber-400 font-bold hover:underline">
                      Sign in here
                    </button>
                  </span>
                )}
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
