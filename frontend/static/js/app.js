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

  const APPRECIATION_MESSAGES = [
    "Great work! One step closer to your goal.",
    "Well done. Your consistency is building.",
    "Excellent progress. Keep moving forward.",
    "Your effort today matters.",
    "One more task completed. Keep going!",
    "Your parents will be proud of the effort you're putting in.",
    "Stay consistent and trust the process.",
    "Discipline today creates freedom tomorrow.",
    "Every minute of honest practice adds up. Keep shining!",
    "With patience and perseverance, success is inevitable."
  ];

  const showAppreciation = (customMsg) => {
    const msg = customMsg || APPRECIATION_MESSAGES[Math.floor(Math.random() * APPRECIATION_MESSAGES.length)];
    setToast({ message: msg, type: 'appreciation' });
    setTimeout(() => setToast(null), 4500);
  };

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
        <div className="p-5 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <div className="flex items-center space-x-2.5">
              <img src="/static/assets/logo.svg" alt="Last Chance" className="w-8 h-8 rounded-lg shadow-sm" />
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
            {/* Live Time Left Today Countdown */}
            {timeData?.time_left_today && (
              <div className="px-3 py-1.5 rounded-lg border flex items-center space-x-2 text-xs font-mono font-bold shadow-sm" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
                <span className="text-amber-400 animate-pulse">⏳</span>
                <span>{timeData.time_left_today.formatted} left today</span>
              </div>
            )}

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
              timeData={timeData}
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

          {activeTab === 'dsa' && (
            <DailyDSAView
              dailyDSA={dailyDSA}
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
              showAppreciation={showAppreciation}
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
              showAppreciation={showAppreciation}
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

function DashboardView({ todaySchedule, dates, timeData, feasibility, todayQuote, dailyDSA, englishToday, onStartSession, onNavigate, onRefresh, showToast, showAppreciation }) {
  const [extraRecs, setExtraRecs] = useState([]);
  const [quoteFav, setQuoteFav] = useState(todayQuote?.is_favorite || false);
  const [rescheduleModalTask, setRescheduleModalTask] = useState(null);
  const [completePct, setCompletePct] = useState(100);
  const [actualMins, setActualMins] = useState(60);
  const [confidence, setConfidence] = useState(4);
  const [notes, setNotes] = useState('');

  // Wasted Time & Shortfall tracking state
  const [wastedSummary, setWastedSummary] = useState(null);
  const [isLogWastedModalOpen, setIsLogWastedModalOpen] = useState(false);
  const [wastedLogMins, setWastedLogMins] = useState(30);
  const [wastedCategory, setWastedCategory] = useState('Avoidable Distraction');
  const [wastedNotes, setWastedNotes] = useState('');

  // 2 DSA Syllabus Topics state
  const [dsaTopics, setDsaTopics] = useState([]);
  const [dsaTimeSpent, setDsaTimeSpent] = useState({});

  // English Simple Practice state
  const [practisedEnglish, setPractisedEnglish] = useState(englishToday?.log?.is_completed ? 'yes' : null);
  const [actualEnglishMinutes, setActualEnglishMinutes] = useState(
    englishToday?.log?.actual_minutes !== undefined ? englishToday.log.actual_minutes : (englishToday?.log?.time_spent_seconds ? Math.floor(englishToday.log.time_spent_seconds / 60) : 30)
  );
  const [savingEnglish, setSavingEnglish] = useState(false);

  useEffect(() => {
    window.LastChanceAPI.getExtraTime().then(res => {
      setExtraRecs(res.recommendations || []);
    }).catch(() => {});

    // Load wasted time summary
    window.LastChanceAPI.getWastedTimeSummary().then(res => {
      setWastedSummary(res);
    }).catch(() => {});

    // Load daily 2 DSA syllabus topics
    window.LastChanceAPI.getDSATopics().then(res => {
      setDsaTopics(res.topics || []);
    }).catch(() => {});
  }, []);

  const academicDone = todaySchedule?.academic_completed_minutes || 0;
  const academicTarget = todaySchedule?.academic_target_minutes || 240;
  const academicPct = Math.min(100, Math.round((academicDone / academicTarget) * 100));

  const dsaSolved = dsaTopics.filter(t => t.status === 'Completed').length || dailyDSA?.solved_count || 0;
  const englishCompleted = englishToday?.log?.is_completed || false;
  const englishMins = actualEnglishMinutes || Math.floor((englishToday?.log?.time_spent_seconds || 0) / 60);
  const englishShortfall = Math.max(0, 30 - englishMins);

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
      if (showAppreciation) {
        showAppreciation("Outstanding effort! Academic task completed and schedule preserved.");
      } else {
        showToast('Task marked 100% completed!', 'success');
      }
    } catch (e) {
      showToast('Failed to update task: ' + e.message, 'error');
    }
  };

  const handleLogWastedTime = async () => {
    if (wastedLogMins <= 0) {
      showToast('Please enter a valid duration', 'error');
      return;
    }
    try {
      await window.LastChanceAPI.logWastedTime({
        wasted_date: dates?.today_str || new Date().toISOString().split('T')[0],
        minutes: wastedLogMins,
        category: wastedCategory,
        notes: wastedNotes
      });
      setIsLogWastedModalOpen(false);
      setWastedNotes('');
      const res = await window.LastChanceAPI.getWastedTimeSummary();
      setWastedSummary(res);
      showToast('Unproductive time logged for transparency.');
    } catch (e) {
      showToast('Failed to log wasted time: ' + e.message, 'error');
    }
  };

  const handleCompleteDSATopic = async (assignmentId, currentStatus) => {
    try {
      const newStatus = currentStatus === 'Completed' ? 'Pending' : 'Completed';
      const timeSpent = dsaTimeSpent[assignmentId] || 25;
      await window.LastChanceAPI.updateDSATopic(assignmentId, {
        status: newStatus,
        time_spent_minutes: timeSpent
      });
      const res = await window.LastChanceAPI.getDSATopics();
      setDsaTopics(res.topics || []);
      if (newStatus === 'Completed' && showAppreciation) {
        showAppreciation("Great consistency! DSA topic commitment completed.");
      } else {
        showToast('DSA topic status updated.');
      }
      onRefresh();
    } catch (e) {
      showToast('Failed to update DSA topic: ' + e.message, 'error');
    }
  };

  const handleSaveEnglishPractice = async () => {
    setSavingEnglish(true);
    try {
      await window.LastChanceAPI.saveEnglishSimple(
        dates?.today_str || new Date().toISOString().split('T')[0],
        actualEnglishMinutes,
        'Logged from dashboard'
      );
      await onRefresh();
      const wRes = await window.LastChanceAPI.getWastedTimeSummary();
      setWastedSummary(wRes);
      if (showAppreciation) {
        showAppreciation("Consistency is key! English speaking practice logged.");
      } else {
        showToast('English speaking practice saved!', 'success');
      }
    } catch (e) {
      showToast('Failed to save English practice: ' + e.message, 'error');
    } finally {
      setSavingEnglish(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Live Time Left Today Breakdown Card */}
      {timeData?.time_left_today && (
        <div className="lc-card p-4.5 border-l-4 border-amber-500 flex flex-col md:flex-row items-start md:items-center justify-between gap-4" style={{ backgroundColor: 'var(--bg-card)' }}>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-xl">⏳</span>
              <h3 className="text-base font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Time Left Today: <span className="font-mono text-amber-500">{timeData.time_left_today.formatted}</span>
              </h3>
            </div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Countdown to midnight IST ({timeData.formatted_time}) • Academic target, DSA, and English tracked separately.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="px-3 py-1.5 rounded-lg border font-mono" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-slate-400">📖 Academic:</span> <strong className="text-indigo-400">{academicDone}m</strong> / {academicTarget}m
            </div>
            <div className="px-3 py-1.5 rounded-lg border font-mono" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-slate-400">🗣️ English:</span> <strong className="text-amber-400">{englishMins}m</strong> / 30m
            </div>
            <div className="px-3 py-1.5 rounded-lg border font-mono" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
              <span className="text-slate-400">💻 DSA:</span> <strong className="text-emerald-400">{dsaSolved}/2</strong>
            </div>
          </div>
        </div>
      )}

      {/* 4 Core Daily Targets Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Academic Study (240m target) */}
        <div className="lc-card p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>📖 Academic Study</span>
            <span className="text-indigo-400 font-bold">{academicPct}%</span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {academicDone} <span className="text-xs font-medium text-slate-400">/ {academicTarget} mins</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-indigo-500 h-2 rounded-full transition-smooth" style={{ width: `${academicPct}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Strict 240m target for 4 university semester courses.
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
            {dsaSolved} <span className="text-xs font-medium text-slate-400">/ 2 topics</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-emerald-500 h-2 rounded-full transition-smooth" style={{ width: `${(dsaSolved / 2) * 100}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Syllabus topic practice outside the 240m target.
          </p>
        </div>

        {/* Metric 3: English Speaking (30 min) */}
        <div className="lc-card p-4 space-y-2 cursor-pointer hover:border-amber-500/50" onClick={() => onNavigate('english')}>
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>🗣️ English Speaking</span>
            <span className={englishMins >= 30 ? 'badge-success badge' : 'badge-warning badge'}>
              {englishMins >= 30 ? 'Done' : 'Shortfall'}
            </span>
          </div>
          <div className="text-2xl font-black" style={{ color: 'var(--text-primary)' }}>
            {englishMins} <span className="text-xs font-medium text-slate-400">/ 30 mins</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-amber-500 h-2 rounded-full transition-smooth" style={{ width: `${Math.min(100, (englishMins / 30) * 100)}%` }}></div>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {englishShortfall > 0 ? `Shortfall: ${englishShortfall}m unmet` : 'Daily 30m target fully met!'}
          </p>
        </div>

        {/* Metric 4: Wasted & Shortfall Accounting */}
        <div className="lc-card p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            <span>⏱️ Unproductive / Shortfall</span>
            <button
              onClick={() => setIsLogWastedModalOpen(true)}
              className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20"
            >
              + Log Time
            </button>
          </div>
          <div className="text-2xl font-black text-rose-400">
            {wastedSummary?.today?.total_unproductive_minutes || 0} <span className="text-xs font-medium text-slate-400">mins today</span>
          </div>
          <div className="text-[11px] text-slate-400 space-y-0.5">
            <div>Confirmed: {wastedSummary?.today?.confirmed_wasted_minutes || 0}m • English: {wastedSummary?.today?.english_shortfall_minutes || 0}m</div>
            <div>Week Total: <strong className="text-rose-400 font-bold">{wastedSummary?.week?.total_unproductive_minutes || 0} mins</strong></div>
          </div>
        </div>
      </div>

      {/* Compulsory Commitments Row: Today's 2 DSA Syllabus Topics & English Simple Check */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card A: 2 DSA Syllabus Topics */}
        <div className="lc-card p-4.5 space-y-3 border-emerald-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-base">💻</span>
              <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                Today's Compulsory DSA Topics (Syllabus Rotation)
              </h3>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Topic Names Only
            </span>
          </div>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Compulsory daily algorithm practice from CSN 3001 Data Structures curriculum:
          </p>

          <div className="space-y-2.5">
            {dsaTopics.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 text-center">Loading today's syllabus topics...</p>
            ) : (
              dsaTopics.map((topic, idx) => {
                const isDone = topic.status === 'Completed';
                return (
                  <div key={topic.id} className="p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-2.5" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div className="space-y-0.5">
                      <div className="text-[10px] font-bold text-emerald-400">Topic #{idx + 1}</div>
                      <div className="font-bold text-sm text-slate-200">{topic.topic_name}</div>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0">
                      <span className="text-[11px] text-slate-400">⏱️ {topic.time_spent_minutes || 25}m</span>
                      <button
                        onClick={() => handleCompleteDSATopic(topic.id, topic.status)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-smooth ${
                          isDone
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm'
                        }`}
                      >
                        {isDone ? '✓ Completed' : 'Mark Done'}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Card B: English Speaking Simple Tracking */}
        <div className="lc-card p-4.5 space-y-3 border-amber-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-base">🗣️</span>
              <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                English Speaking Practice (Daily 30m)
              </h3>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              🔥 {englishToday?.streak_days || 0}d streak
            </span>
          </div>

          <div className="p-3.5 rounded-lg border space-y-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
            <div className="text-xs font-semibold text-slate-200">
              Did you practise English speaking today?
            </div>

            <div className="flex items-center space-x-3 text-xs">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="practised"
                  checked={practisedEnglish === 'yes'}
                  onChange={() => setPractisedEnglish('yes')}
                  className="accent-indigo-600"
                />
                <span className="font-bold text-emerald-400">Yes, I practised</span>
              </label>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="practised"
                  checked={practisedEnglish === 'no'}
                  onChange={() => {
                    setPractisedEnglish('no');
                    setActualEnglishMinutes(0);
                  }}
                  className="accent-indigo-600"
                />
                <span className="font-bold text-rose-400">No, missed today</span>
              </label>
            </div>

            {practisedEnglish === 'yes' && (
              <div className="space-y-2 pt-1 border-t" style={{ borderColor: 'var(--border-color)' }}>
                <div className="flex items-center justify-between text-xs">
                  <label className="font-medium text-slate-300">Actual practice duration:</label>
                  <div className="flex items-center space-x-1">
                    <input
                      type="number"
                      min="1"
                      max="120"
                      value={actualEnglishMinutes}
                      onChange={e => setActualEnglishMinutes(Math.max(0, Number(e.target.value)))}
                      className="w-16 px-2 py-1 text-xs rounded border text-center font-mono font-bold"
                    />
                    <span className="text-slate-400">minutes</span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 flex justify-between">
                  <span>Target: 30 minutes</span>
                  <span className={englishShortfall > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                    {englishShortfall > 0 ? `Shortfall: ${englishShortfall} mins (counted in wasted time)` : 'Target achieved! Shortfall: 0m'}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={handleSaveEnglishPractice}
              disabled={savingEnglish || practisedEnglish === null}
              className="w-full py-2 rounded-lg text-xs font-bold btn-primary disabled:opacity-50"
            >
              {savingEnglish ? 'Saving...' : 'Save English Practice Record'}
            </button>
          </div>
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

      {/* Log Unproductive / Wasted Time Modal */}
      {isLogWastedModalOpen && (
        <div className="modal-overlay" onClick={() => setIsLogWastedModalOpen(false)}>
          <div className="modal-dialog p-5 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
              <h3 className="text-base font-bold text-slate-100">Log Unproductive / Wasted Time</h3>
              <button onClick={() => setIsLogWastedModalOpen(false)} className="text-slate-400 text-lg">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Duration Wasted (minutes):</label>
                <input
                  type="number"
                  min="5"
                  max="480"
                  value={wastedLogMins}
                  onChange={e => setWastedLogMins(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Category:</label>
                <select value={wastedCategory} onChange={e => setWastedCategory(e.target.value)} className="w-full">
                  <option value="Avoidable Distraction">Avoidable Distraction</option>
                  <option value="Social Media Scrolling">Social Media Scrolling</option>
                  <option value="Daydreaming / Inattention">Daydreaming / Inattention</option>
                  <option value="Phone Call / Messaging">Phone Call / Messaging</option>
                  <option value="Unplanned Break">Unplanned Long Break</option>
                  <option value="Other Unproductive Time">Other Unproductive Time</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Notes / Reflection (Optional):</label>
                <textarea
                  rows="2"
                  value={wastedNotes}
                  onChange={e => setWastedNotes(e.target.value)}
                  placeholder="What triggered this distraction? How to avoid tomorrow?"
                  className="w-full"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button onClick={() => setIsLogWastedModalOpen(false)} className="btn-secondary text-xs">Cancel</button>
              <button onClick={handleLogWastedTime} className="btn-primary text-xs font-bold">
                Save Wasted Time Entry
              </button>
            </div>
          </div>
        </div>
      )}

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
                  <option value="1">1 - Struggled / Confused</option>
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
                    if (completePct >= 100 && showAppreciation) {
                      showAppreciation();
                    } else {
                      showToast('Task progress saved and future schedule updated!', 'success');
                    }
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
  const [horizonDays, setHorizonDays] = useState([]);
  const [selectedDate, setSelectedDate] = useState(dates?.today_str || new Date().toISOString().split('T')[0]);
  const [viewMode, setViewMode] = useState('month'); // 'month', 'week', 'day', 'horizon'
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
      const hData = await window.LastChanceAPI.getFullSchedule();
      setHorizonDays(hData.schedule || []);
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
            <button
              onClick={() => setViewMode('horizon')}
              className={`px-3 py-1.5 text-xs font-semibold ${viewMode === 'horizon' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Full Plan (Exams Horizon)
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

        {/* Full Plan (Exams Horizon) Day-by-Day View */}
        {viewMode === 'horizon' && (
          <div className="lg:col-span-2 lc-card p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b gap-2" style={{ borderColor: 'var(--border-color)' }}>
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span>Complete Day-by-Day Horizon</span>
                  <span className="badge badge-accent text-[11px] font-mono">{horizonDays.length} Days Planned Through Exams</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Strict 240m daily academic study target across all 4 subjects, plus 2 DSA topics and 30m English.
                </p>
              </div>
              <div className="text-xs text-right font-mono text-slate-400">
                Oct 25 – Dec 04, 2026
              </div>
            </div>

            <div className="space-y-4 max-h-[680px] overflow-y-auto pr-1">
              {horizonDays.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <p>Loading complete exam horizon schedule...</p>
                </div>
              ) : (
                horizonDays.map((day, idx) => {
                  const dStr = day.date;
                  const isOOPPrep = dStr >= '2026-10-25' && dStr <= '2026-10-27';
                  const isRevision = dStr >= '2026-11-19' && dStr <= '2026-11-25';
                  const isExam = dStr >= '2026-11-26';
                  const isToday = dStr === (dates?.today_str || '2026-10-25');
                  const isSelected = dStr === selectedDate;

                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedDate(dStr)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected ? 'border-indigo-500 bg-indigo-950/20' : 'hover:border-slate-600'
                      }`}
                      style={{
                        backgroundColor: isSelected ? undefined : 'var(--bg-card-elevated)',
                        borderColor: isSelected ? undefined : 'var(--border-color)'
                      }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 mb-2.5 border-b border-slate-700/60">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-slate-100">{dStr}</span>
                          <span className="text-xs text-slate-400 font-semibold">({day.day_of_week})</span>
                          {isToday && <span className="badge badge-primary text-[10px]">TODAY</span>}
                          {isOOPPrep && <span className="badge badge-warning text-[10px]">OOP Test Prep (Units 5 & 6)</span>}
                          {isRevision && <span className="badge badge-accent text-[10px]">7-Day Revision Buffer</span>}
                          {isExam && <span className="badge badge-danger text-[10px]">Exam Period</span>}
                        </div>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="font-semibold text-emerald-400 font-mono">Academic: {day.total_academic_minutes} / 240m</span>
                          <span className="text-slate-400 font-mono">|</span>
                          <span className="text-indigo-300">DSA: 2 Topics</span>
                          <span className="text-slate-400 font-mono">|</span>
                          <span className="text-amber-300">English: 30m</span>
                        </div>
                      </div>

                      {/* Multi-subject scheduled sessions */}
                      <div className="space-y-1.5">
                        {day.sessions.map((sess, sIdx) => {
                          const isOOP = sess.course_code === 'CSN 3004';
                          const isDiscrete = sess.course_code === 'CSN 3003';
                          const isDS = sess.course_code === 'CSN 3001';
                          const isDSML = sess.course_code === 'CSN 3002';

                          return (
                            <div
                              key={sIdx}
                              className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-900/40 border border-slate-800"
                            >
                              <div className="flex items-center gap-2 overflow-hidden">
                                <span
                                  className="px-2 py-0.5 rounded text-[10px] font-bold shrink-0 text-white"
                                  style={{
                                    backgroundColor: isOOP ? '#ef4444' :
                                                     isDiscrete ? '#8b5cf6' :
                                                     isDS ? '#06b6d4' :
                                                     isDSML ? '#10b981' : '#64748b'
                                  }}
                                >
                                  {sess.course_code}
                                </span>
                                <span className="font-semibold text-slate-300 truncate" title={sess.topic_title || sess.title}>
                                  {sess.topic_title || sess.title}
                                </span>
                              </div>
                              <span className="font-mono text-slate-300 shrink-0 ml-3">
                                {sess.duration_minutes}m
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
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

// ----------------- 3. COURSES & UNITS VIEW (COMPLETE INTERACTIVE CHECKLISTS) -----------------

function CoursesUnitsView({ subjects, onRefresh, showToast, showAppreciation }) {
  const [coursesData, setCoursesData] = useState([]);
  const [activeCourseId, setActiveCourseId] = useState(subjects[0]?.id || null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loadingCourses, setLoadingCourses] = useState(true);

  const loadCoursesTree = async () => {
    try {
      const res = await window.LastChanceAPI.getCourses();
      setCoursesData(res.courses || []);
      if (!activeCourseId && res.courses?.length > 0) {
        setActiveCourseId(res.courses[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCourses(false);
    }
  };

  useEffect(() => {
    loadCoursesTree();
  }, []);

  const activeCourse = coursesData.find(c => c.id === activeCourseId) || subjects.find(s => s.id === activeCourseId);

  const handleUpdateTopicStatus = async (topicId, newStatus) => {
    try {
      await window.LastChanceAPI.updateTopicStatus(topicId, newStatus);
      await loadCoursesTree();
      if ((newStatus === 'COMPLETED' || newStatus === 'MASTERED') && showAppreciation) {
        showAppreciation("Topic completed! Progress updated across unit and course.");
      } else {
        showToast(`Topic updated to ${newStatus.replace('_', ' ')}!`);
      }
      onRefresh();
    } catch (e) {
      showToast('Failed to update topic status: ' + e.message, 'error');
    }
  };

  const handleToggleCheckbox = (topic) => {
    const isCompleted = topic.mastery_level === 'COMPLETED' || topic.mastery_level === 'MASTERED';
    const newStatus = isCompleted ? 'NOT_STARTED' : 'COMPLETED';
    handleUpdateTopicStatus(topic.id, newStatus);
  };

  return (
    <div className="space-y-6">
      {/* 4 Course Tabs with Completion Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {(coursesData.length > 0 ? coursesData : subjects).map(subj => {
          const isSelected = subj.id === activeCourseId;
          const pct = subj.progress_percent !== undefined ? subj.progress_percent : 0;
          return (
            <div
              key={subj.id}
              onClick={() => setActiveCourseId(subj.id)}
              className={`lc-card p-4 cursor-pointer transition-smooth border-l-4 ${
                isSelected ? 'shadow-md border-indigo-500' : 'opacity-85 hover:opacity-100'
              }`}
              style={{
                borderLeftColor: subj.color || '#4f46e5',
                backgroundColor: isSelected ? 'var(--bg-card-elevated)' : 'var(--bg-card)'
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold font-mono" style={{ color: subj.color || '#4f46e5' }}>
                  {subj.code}
                </span>
                <span className="text-[11px] font-bold text-slate-300 font-mono">{pct}%</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100 truncate mt-1">{subj.name}</h3>

              <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2.5 overflow-hidden">
                <div className="h-1.5 rounded-full transition-smooth" style={{ width: `${pct}%`, backgroundColor: subj.color || '#4f46e5' }}></div>
              </div>

              <div className="text-[11px] text-slate-400 mt-2 flex justify-between">
                <span>{subj.completed_topics_count || 0}/{subj.total_topics_count || subj.total_lectures || 0} topics</span>
                <span>Exam: {subj.exam_date || 'Nov 26'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Course Details & Unit Topics Hierarchy */}
      <div className="lc-card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-base font-bold text-slate-100">{activeCourse?.name} ({activeCourse?.code})</span>
              <span className="badge badge-info text-xs font-bold">{activeCourse?.progress_percent || 0}% Completed</span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Authoritative university unit & topic syllabus checklist</p>
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
              <option value="ALL">All Topics</option>
              <option value="UNFINISHED">Unfinished Only</option>
              <option value="COMPLETED">Completed Only</option>
              <option value="NEEDS_REVISION">Needs Revision</option>
            </select>
          </div>
        </div>

        {/* Units Accordion */}
        <div className="space-y-4">
          {loadingCourses ? (
            <p className="text-xs text-slate-400 py-8 text-center">Loading university course units...</p>
          ) : (
            (activeCourse?.units || []).map(unit => {
              const filteredTopics = (unit.topics || []).filter(t => {
                const matchSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase());
                let matchStatus = true;
                if (statusFilter === 'UNFINISHED') {
                  matchStatus = t.mastery_level !== 'COMPLETED' && t.mastery_level !== 'MASTERED';
                } else if (statusFilter === 'COMPLETED') {
                  matchStatus = t.mastery_level === 'COMPLETED' || t.mastery_level === 'MASTERED';
                } else if (statusFilter === 'NEEDS_REVISION') {
                  matchStatus = t.mastery_level === 'NEEDS_REVISION';
                }
                return matchSearch && matchStatus;
              });

              if (filteredTopics.length === 0 && searchTerm) return null;

              return (
                <div key={unit.id} className="p-4 rounded-xl border space-y-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-2.5" style={{ borderColor: 'var(--border-color)' }}>
                    <div>
                      <div className="font-bold text-sm text-slate-200">
                        Unit {unit.unit_number}: {unit.title}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {unit.completed_topics_count || 0} of {unit.total_topics_count || unit.topics?.length || 0} topics completed ({unit.progress_percent || 0}%)
                      </div>
                    </div>
                    <div className="w-32 bg-slate-800 rounded-full h-2 overflow-hidden shrink-0">
                      <div className="bg-emerald-500 h-2 rounded-full transition-smooth" style={{ width: `${unit.progress_percent || 0}%` }}></div>
                    </div>
                  </div>

                  {/* Topic Checklists */}
                  <div className="space-y-2">
                    {filteredTopics.map(t => {
                      const isDone = t.mastery_level === 'COMPLETED' || t.mastery_level === 'MASTERED';
                      return (
                        <div
                          key={t.id}
                          className="p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-smooth"
                          style={{
                            backgroundColor: 'var(--bg-card)',
                            borderColor: isDone ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-color)'
                          }}
                        >
                          <div className="flex items-start space-x-3">
                            <input
                              type="checkbox"
                              checked={isDone}
                              onChange={() => handleToggleCheckbox(t)}
                              className="mt-1 w-4 h-4 rounded border-slate-700 accent-emerald-500 cursor-pointer"
                              title="Toggle Topic Completion"
                            />
                            <div>
                              <div className={`font-bold text-sm ${isDone ? 'text-emerald-300 line-through' : 'text-slate-100'}`}>
                                {t.title}
                              </div>
                              {t.subtopics?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {t.subtopics.map((st, sIdx) => (
                                    <span key={sIdx} className="code-pill text-[10px]">{st}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
                            <span className="font-mono text-slate-400 text-[11px]">⏱️ {t.estimated_minutes}m</span>
                            <select
                              value={t.mastery_level}
                              onChange={e => handleUpdateTopicStatus(t.id, e.target.value)}
                              className="text-xs font-semibold px-2 py-1 rounded border"
                            >
                              <option value="NOT_STARTED">Not started</option>
                              <option value="IN_PROGRESS">In progress</option>
                              <option value="COMPLETED">Completed</option>
                              <option value="NEEDS_REVISION">Needs revision</option>
                              <option value="MASTERED">Mastered</option>
                            </select>
                          </div>
                        </div>
                      );
                    })}
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

// ----------------- 4. DAILY DSA VIEW (2 SYLLABUS TOPIC RECOMMENDATIONS ONLY) -----------------

function DailyDSAView({ dailyDSA, onRefresh, showToast, showAppreciation }) {
  const [dsaTopics, setDsaTopics] = useState([]);
  const [timeSpentState, setTimeSpentState] = useState({});
  const [notesState, setNotesState] = useState({});
  const [loading, setLoading] = useState(true);

  const loadTopics = async () => {
    try {
      const res = await window.LastChanceAPI.getDSATopics();
      setDsaTopics(res.topics || []);
    } catch (e) {
      showToast('Failed to load DSA topics: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, []);

  const handleUpdateTopic = async (assignmentId, currentStatus) => {
    try {
      const newStatus = currentStatus === 'Completed' ? 'Pending' : 'Completed';
      const timeSpent = timeSpentState[assignmentId] || 25;
      const notes = notesState[assignmentId] || '';
      await window.LastChanceAPI.updateDSATopic(assignmentId, {
        status: newStatus,
        time_spent_minutes: timeSpent,
        notes: notes
      });
      await loadTopics();
      await onRefresh();
      if (newStatus === 'Completed' && showAppreciation) {
        showAppreciation("Consistency builds mastery! DSA topic practice logged.");
      } else {
        showToast('DSA topic updated.');
      }
    } catch (e) {
      showToast('Failed to update DSA topic: ' + e.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Daily DSA (Topic Recommendations Only)</h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Exactly two Data Structures topics assigned daily from CSN 3001 syllabus. Topic names only, no generated questions.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-full">
            Target: 2 Topics Daily
          </span>
        </div>
      </div>

      {/* 2 Topic Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-2 lc-card p-8 text-center text-xs text-slate-400">
            Loading today's syllabus recommendations...
          </div>
        ) : (
          dsaTopics.map((item, idx) => {
            const isDone = item.status === 'Completed';
            return (
              <div key={item.id} className="lc-card p-5 space-y-4 flex flex-col justify-between border-t-4 border-emerald-500">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      Recommendation #{idx + 1}
                    </span>
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded ${
                      isDone ? 'badge-success badge' : 'badge-warning badge'
                    }`}>
                      {item.status}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">CSN 3001 Syllabus Topic</span>
                    <h3 className="text-lg font-black text-slate-100 mt-0.5">{item.topic_name}</h3>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    Practice coding or solving academic problems for <strong>{item.topic_name}</strong> on LeetCode, university handouts, or notebook.
                  </p>

                  <div className="space-y-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    <div className="flex items-center justify-between text-xs">
                      <label className="text-slate-300 font-medium">Time spent practicing:</label>
                      <div className="flex items-center space-x-1">
                        <input
                          type="number"
                          min="5"
                          max="120"
                          defaultValue={item.time_spent_minutes || 25}
                          onChange={e => setTimeSpentState(p => ({ ...p, [item.id]: Number(e.target.value) }))}
                          className="w-16 px-2 py-1 text-xs rounded border text-center font-mono font-bold"
                        />
                        <span className="text-slate-400">mins</span>
                      </div>
                    </div>

                    <textarea
                      rows="2"
                      placeholder="Notes on approach, algorithms, or edge cases handled..."
                      defaultValue={item.notes || ''}
                      onChange={e => setNotesState(p => ({ ...p, [item.id]: e.target.value }))}
                      className="w-full text-xs"
                    />
                  </div>
                </div>

                <div className="pt-3 border-t flex justify-end" style={{ borderColor: 'var(--border-color)' }}>
                  <button
                    onClick={() => handleUpdateTopic(item.id, item.status)}
                    className={`w-full py-2 rounded-lg text-xs font-bold transition-smooth ${
                      isDone
                        ? 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        : 'btn-primary'
                    }`}
                  >
                    {isDone ? 'Reopen Practice Commitment' : '✓ Mark DSA Topic Commitment Completed'}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Rotation Info Card */}
      <div className="lc-card p-4 text-xs space-y-1.5" style={{ backgroundColor: 'var(--bg-card-elevated)' }}>
        <div className="font-bold text-indigo-400">ℹ️ About DSA Topic Rotation:</div>
        <p className="text-slate-300 leading-relaxed">
          Daily recommendations are selected from the 8 official units of CSN 3001 (Arrays, Linked Lists, Stacks, Queues, Trees, Binary Search Trees, Graphs, Heaps/Hashing). The scheduler rotates topics systematically to ensure comprehensive coverage before exams without forcing specific problem URLs.
        </p>
      </div>
    </div>
  );
}

// ----------------- 5. ENGLISH SPEAKING IMPROVEMENT (SIMPLE DAILY TRACKING) -----------------

function EnglishSpeakingView({ englishToday, onRefresh, showToast, showAppreciation }) {
  const [practised, setPractised] = useState(englishToday?.log?.is_completed ? 'yes' : null);
  const [actualMinutes, setActualMinutes] = useState(
    englishToday?.log?.actual_minutes !== undefined ? englishToday.log.actual_minutes : (englishToday?.log?.time_spent_seconds ? Math.floor(englishToday.log.time_spent_seconds / 60) : 30)
  );
  const [notes, setNotes] = useState(englishToday?.log?.notes || '');
  const [history, setHistory] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    window.LastChanceAPI.getEnglishHistory().then(res => setHistory(res.history || [])).catch(() => {});
  }, []);

  const targetMinutes = 30;
  const shortfallMinutes = Math.max(0, targetMinutes - (actualMinutes || 0));

  const handleSave = async () => {
    if (practised === null) {
      showToast('Please confirm whether you practised today', 'error');
      return;
    }
    setSaving(true);
    try {
      const minsToSave = practised === 'yes' ? actualMinutes : 0;
      await window.LastChanceAPI.saveEnglishSimple(
        englishToday?.date || new Date().toISOString().split('T')[0],
        minsToSave,
        notes
      );
      await onRefresh();
      const hRes = await window.LastChanceAPI.getEnglishHistory();
      setHistory(hRes.history || []);
      if (showAppreciation && minsToSave > 0) {
        showAppreciation("Every day counts! English speaking practice saved.");
      } else {
        showToast('English speaking log updated.');
      }
    } catch (e) {
      showToast('Failed to save English practice: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>English Speaking (Daily 30m Tracking)</h2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Simple completion tracking. Confirmed shortfall time is transparently accounted in daily unmet targets.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-3 py-1 rounded-full">
            🔥 {englishToday?.streak_days || 0} Day Streak
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Simple Interaction Form */}
        <div className="lg:col-span-2 lc-card p-6 space-y-5">
          <div className="border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
            <h3 className="text-base font-bold text-slate-100">Did you practise English speaking today?</h3>
            <p className="text-xs text-slate-400 mt-0.5">Separate compulsory commitment outside 4-hour academic target.</p>
          </div>

          <div className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <label className={`p-4 rounded-xl border flex items-center space-x-3 cursor-pointer transition-smooth flex-1 ${
                practised === 'yes' ? 'bg-emerald-500/10 border-emerald-500 shadow-sm' : 'bg-slate-800/40 border-slate-700'
              }`}>
                <input
                  type="radio"
                  name="practised"
                  checked={practised === 'yes'}
                  onChange={() => setPractised('yes')}
                  className="w-4 h-4 accent-emerald-500"
                />
                <div>
                  <div className="font-bold text-sm text-emerald-400">Yes, I practised today</div>
                  <div className="text-[11px] text-slate-400">I spent dedicated speaking time aloud</div>
                </div>
              </label>

              <label className={`p-4 rounded-xl border flex items-center space-x-3 cursor-pointer transition-smooth flex-1 ${
                practised === 'no' ? 'bg-rose-500/10 border-rose-500 shadow-sm' : 'bg-slate-800/40 border-slate-700'
              }`}>
                <input
                  type="radio"
                  name="practised"
                  checked={practised === 'no'}
                  onChange={() => {
                    setPractised('no');
                    setActualMinutes(0);
                  }}
                  className="w-4 h-4 accent-rose-500"
                />
                <div>
                  <div className="font-bold text-sm text-rose-400">No, missed today</div>
                  <div className="text-[11px] text-slate-400">30 minutes unmet shortfall</div>
                </div>
              </label>
            </div>

            {practised === 'yes' && (
              <div className="p-4 rounded-xl border space-y-3" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-bold text-slate-200">How many minutes did you actually practise?</label>
                  <div className="flex items-center space-x-1.5">
                    <input
                      type="number"
                      min="1"
                      max="180"
                      value={actualMinutes}
                      onChange={e => setActualMinutes(Math.max(0, Number(e.target.value)))}
                      className="w-20 px-3 py-1.5 text-sm rounded border text-center font-mono font-bold"
                    />
                    <span className="text-xs text-slate-400 font-medium">mins</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg border text-xs space-y-1" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <div className="flex justify-between font-semibold">
                    <span>Target: 30 minutes</span>
                    <span>Actual: {actualMinutes} minutes</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400">Accounting:</span>
                    <span className={shortfallMinutes > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                      {shortfallMinutes > 0
                        ? `Shortfall: ${shortfallMinutes} mins (added to unmet target time)`
                        : 'Zero shortfall! Target fully satisfied.'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-300">Notes / Fluency Observations (Optional):</label>
              <textarea
                rows="2"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="What topic did you speak on? Any pronunciation or vocabulary doubts?"
                className="w-full text-xs"
              />
            </div>

            <button
              onClick={handleSave}
              disabled={saving || practised === null}
              className="w-full py-2.5 rounded-lg text-xs font-bold btn-primary disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save English Speaking Record'}
            </button>
          </div>
        </div>

        {/* Right 1 Col: Practice History & Shortfall Accounting */}
        <div className="space-y-6">
          <div className="lc-card p-5 space-y-3">
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Practice Summary</h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b" style={{ borderColor: 'var(--border-color)' }}>
                <span className="text-slate-400">Daily Target:</span>
                <span className="font-bold text-slate-200">30 minutes</span>
              </div>
              <div className="flex justify-between py-1 border-b" style={{ borderColor: 'var(--border-color)' }}>
                <span className="text-slate-400">Today's Actual:</span>
                <span className="font-bold text-amber-400">{actualMinutes} minutes</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Unmet Shortfall:</span>
                <span className="font-bold text-rose-400">{shortfallMinutes} minutes</span>
              </div>
            </div>
          </div>

          <div className="lc-card p-5 space-y-3">
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Recent Practice History</h4>
            <div className="space-y-2 text-xs max-h-56 overflow-y-auto pr-1">
              {history.length === 0 ? (
                <p className="text-slate-500 text-center py-4">No logs recorded yet.</p>
              ) : (
                history.map((h, i) => (
                  <div key={i} className="p-2.5 rounded-lg border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-card-elevated)', borderColor: 'var(--border-color)' }}>
                    <div>
                      <div className="font-semibold text-slate-200">{h.log_date}</div>
                      <div className="text-[10px] text-slate-400">Shortfall: {h.shortfall_minutes || 0}m</div>
                    </div>
                    <span className={`text-xs font-bold ${h.is_completed ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {h.actual_minutes || Math.floor((h.time_spent_seconds || 0) / 60)} mins
                    </span>
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

function AnalyticsView({ feasibility, onRefresh, showToast, showAppreciation }) {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [wastedGraphData, setWastedGraphData] = useState([]);
  const [wastedFilter, setWastedFilter] = useState('ALL');
  const [selectedDayDetail, setSelectedDayDetail] = useState(null);

  useEffect(() => {
    window.LastChanceAPI.getAnalytics().then(res => setAnalyticsData(res)).catch(() => {});
    window.LastChanceAPI.getWastedTimeGraph().then(res => {
      setWastedGraphData(res.days || []);
      if (res.days?.length > 0) {
        setSelectedDayDetail(res.days[0]);
      }
    }).catch(e => console.error(e));
  }, []);

  const subjectsStats = analyticsData?.subjects_stats || [];
  const dailyHistory = analyticsData?.daily_history || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Progress & Learning Analytics</h2>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Real stored metrics: academic study time vs commitments, course completion, and wasted-time accounting
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

      {/* Dedicated Wasted Time & Shortfall Day-Wise Graph (Section 13) */}
      <div className="lc-card p-5 space-y-4 border-rose-500/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" style={{ borderColor: 'var(--border-color)' }}>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>⏱️ Wasted & Unmet Target Time (Day-Wise Graph)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Transparent daily accounting: Confirmed Wasted Time, English Speaking Shortfall, and Missed Scheduled Study
            </p>
          </div>
          <div className="flex items-center space-x-1.5 text-xs">
            <button
              onClick={() => setWastedFilter('ALL')}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold ${wastedFilter === 'ALL' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              All Categories
            </button>
            <button
              onClick={() => setWastedFilter('CONFIRMED')}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold ${wastedFilter === 'CONFIRMED' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Confirmed
            </button>
            <button
              onClick={() => setWastedFilter('ENGLISH')}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold ${wastedFilter === 'ENGLISH' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              English
            </button>
            <button
              onClick={() => setWastedFilter('MISSED')}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold ${wastedFilter === 'MISSED' ? 'btn-primary' : 'bg-slate-800 text-slate-300'}`}
            >
              Missed Study
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 text-xs pt-1">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-orange-500"></span>
            <span className="text-slate-300">Confirmed Wasted</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-amber-500"></span>
            <span className="text-slate-300">English Shortfall</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-rose-500"></span>
            <span className="text-slate-300">Missed Study</span>
          </div>
        </div>

        {/* Day-Wise Horizontal Bar Timeline Container */}
        <div className="space-y-2 overflow-x-auto max-h-72 overflow-y-auto pr-2">
          {wastedGraphData.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No wasted time records logged yet.</p>
          ) : (
            wastedGraphData.slice(0, 21).map((day, idx) => {
              const maxScale = 120; // 120 minutes max scale
              const confirmed = day.confirmed_wasted_minutes || 0;
              const english = day.english_shortfall_minutes || 0;
              const missed = day.missed_scheduled_study_minutes || 0;
              const total = day.total_unproductive_minutes || 0;

              const isSelected = selectedDayDetail?.date === day.date;

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedDayDetail(day)}
                  className={`p-2.5 rounded-lg border flex items-center justify-between gap-3 cursor-pointer transition-smooth ${
                    isSelected ? 'border-rose-500 bg-rose-500/10' : 'hover:bg-slate-800/30'
                  }`}
                  style={{ backgroundColor: isSelected ? undefined : 'var(--bg-card-elevated)', borderColor: isSelected ? undefined : 'var(--border-color)' }}
                >
                  <div className="w-24 shrink-0 font-mono text-xs font-bold text-slate-300">
                    {day.date}
                    {day.is_future && <span className="block text-[9px] text-indigo-400 font-sans">Projection</span>}
                  </div>

                  <div className="flex-1 bg-slate-900 rounded h-4 flex overflow-hidden">
                    {(wastedFilter === 'ALL' || wastedFilter === 'CONFIRMED') && confirmed > 0 && (
                      <div
                        style={{ width: `${Math.min(100, (confirmed / maxScale) * 100)}%` }}
                        className="bg-orange-500 h-full transition-smooth"
                        title={`Confirmed Wasted: ${confirmed}m`}
                      ></div>
                    )}
                    {(wastedFilter === 'ALL' || wastedFilter === 'ENGLISH') && english > 0 && (
                      <div
                        style={{ width: `${Math.min(100, (english / maxScale) * 100)}%` }}
                        className="bg-amber-500 h-full transition-smooth"
                        title={`English Shortfall: ${english}m`}
                      ></div>
                    )}
                    {(wastedFilter === 'ALL' || wastedFilter === 'MISSED') && missed > 0 && (
                      <div
                        style={{ width: `${Math.min(100, (missed / maxScale) * 100)}%` }}
                        className="bg-rose-500 h-full transition-smooth"
                        title={`Missed Study: ${missed}m`}
                      ></div>
                    )}
                  </div>

                  <div className="w-20 text-right shrink-0 font-mono text-xs font-bold" style={{ color: total > 0 ? '#fb7185' : '#10b981' }}>
                    {total} mins
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Day Inspector */}
        {selectedDayDetail && (
          <div className="p-3.5 rounded-lg border text-xs flex flex-wrap items-center justify-between gap-4 mt-2" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <div>
              <span className="font-bold text-slate-200">Selected Date: {selectedDayDetail.date}</span>
              <span className="text-[11px] text-slate-400 ml-2">({selectedDayDetail.is_future ? 'Upcoming Day' : 'Recorded Actual'})</span>
            </div>
            <div className="flex items-center space-x-4">
              <span>Confirmed: <strong className="text-orange-400">{selectedDayDetail.confirmed_wasted_minutes || 0}m</strong></span>
              <span>English Shortfall: <strong className="text-amber-400">{selectedDayDetail.english_shortfall_minutes || 0}m</strong></span>
              <span>Missed Study: <strong className="text-rose-400">{selectedDayDetail.missed_scheduled_study_minutes || 0}m</strong></span>
              <span className="border-l pl-3" style={{ borderColor: 'var(--border-color)' }}>
                Total: <strong className="text-rose-400 font-bold">{selectedDayDetail.total_unproductive_minutes || 0}m</strong>
              </span>
            </div>
          </div>
        )}
      </div>

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
