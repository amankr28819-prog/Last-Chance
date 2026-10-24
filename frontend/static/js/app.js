// StudyPilot — Your Personal Exam Planning System
// Modern, Local-first, Deterministic, Adaptive Frontend Application
const { useState, useEffect, useMemo, useRef } = React;

function App() {
  const [activeTab, setActiveTab] = useState('today');
  const [theme, setTheme] = useState(localStorage.getItem('studypilot_theme') || 'dark');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  // Core Data States
  const [dates, setDates] = useState(null);
  const [feasibility, setFeasibility] = useState(null);
  const [settings, setSettings] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [todaySchedule, setTodaySchedule] = useState(null);

  // Focus Session Modal State
  const [focusSessionTask, setFocusSessionTask] = useState(null);
  const [isFocusModalOpen, setIsFocusModalOpen] = useState(false);

  // Onboarding State
  const [showOnboarding, setShowOnboarding] = useState(false);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('studypilot_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [dInfo, fInfo, stg, subjs, tSched] = await Promise.all([
        window.StudyPilotAPI.getDates(),
        window.StudyPilotAPI.getFeasibility(),
        window.StudyPilotAPI.getSettings(),
        window.StudyPilotAPI.getSubjects(),
        window.StudyPilotAPI.getTodaySchedule()
      ]);
      setDates(dInfo);
      setFeasibility(fInfo);
      setSettings(stg);
      setSubjects(subjs);
      setTodaySchedule(tSched);

      if (!stg.onboarding_completed) {
        setShowOnboarding(true);
      }
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
      const [dInfo, fInfo, subjs, tSched] = await Promise.all([
        window.StudyPilotAPI.getDates(),
        window.StudyPilotAPI.getFeasibility(),
        window.StudyPilotAPI.getSubjects(),
        window.StudyPilotAPI.getTodaySchedule()
      ]);
      setDates(dInfo);
      setFeasibility(fInfo);
      setSubjects(subjs);
      setTodaySchedule(tSched);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-medium tracking-wide text-slate-400">Initializing StudyPilot Personal Planner...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-primary text-primary transition-smooth">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg border text-sm flex items-center space-x-3 transition-smooth ${
          toast.type === 'error' ? 'bg-rose-950/90 text-rose-200 border-rose-800' :
          toast.type === 'success' ? 'bg-emerald-950/90 text-emerald-200 border-emerald-800' :
          'bg-slate-900/90 text-slate-200 border-slate-700'
        }`}>
          <span>{toast.message}</span>
        </div>
      )}

      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-subtle glass-panel px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-md">
            <span className="font-bold text-white text-base tracking-wider">SP</span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-base tracking-tight">StudyPilot</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                Semester Prep
              </span>
            </div>
            <p className="text-xs text-muted">Adaptive Exam Planning & Syllabus Coverage</p>
          </div>
        </div>

        {/* Status / Feasibility Pill */}
        {feasibility && (
          <div className="hidden md:flex items-center space-x-3">
            <div className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-2 border ${
              feasibility.status_label === 'ON_TRACK' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
              feasibility.status_label === 'TIGHT' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
              'bg-rose-500/10 text-rose-400 border-rose-500/30 animate-subtle-pulse'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                feasibility.status_label === 'ON_TRACK' ? 'bg-emerald-400' :
                feasibility.status_label === 'TIGHT' ? 'bg-amber-400' : 'bg-rose-400'
              }`}></span>
              <span>{feasibility.status_label.replace('_', ' ')}: {feasibility.capacity_utilization_percent}% Used</span>
            </div>

            {dates && (
              <div className="text-xs text-muted">
                Exam in <strong className="text-slate-200">{dates.days_to_exam}d</strong> | Deadline in <strong className="text-slate-200">{dates.days_to_deadline}d</strong>
              </div>
            )}
          </div>
        )}

        {/* Global Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-surface-elevated hover:bg-slate-700 text-slate-300 transition-smooth"
            title="Toggle Theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            onClick={() => setShowOnboarding(true)}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-smooth"
          >
            Setup Wizard
          </button>
        </div>
      </header>

      {/* Main Tab Navigation */}
      <nav className="border-b border-subtle bg-secondary px-6 overflow-x-auto flex space-x-1 scrollbar-none">
        {[
          { id: 'today', label: 'Today', icon: '📅' },
          { id: 'calendar', label: 'Study Calendar', icon: '🗓️' },
          { id: 'syllabus', label: 'Syllabus Explorer', icon: '📚' },
          { id: 'subjects', label: 'Subjects', icon: '🎓' },
          { id: 'revision', label: 'Revision', icon: '🔄' },
          { id: 'analytics', label: 'Analytics', icon: '📊' },
          { id: 'history', label: 'Study History', icon: '📜' },
          { id: 'import', label: 'Import Handouts', icon: '📥' },
          { id: 'settings', label: 'Settings', icon: '⚙️' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 text-xs font-semibold whitespace-nowrap border-b-2 flex items-center space-x-2 transition-smooth ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {activeTab === 'today' && (
          <TodayView
            todaySchedule={todaySchedule}
            dates={dates}
            feasibility={feasibility}
            onStartSession={(task) => {
              setFocusSessionTask(task);
              setIsFocusModalOpen(true);
            }}
            onRefresh={refreshAll}
            showToast={showToast}
          />
        )}

        {activeTab === 'calendar' && (
          <CalendarView
            dates={dates}
            onStartSession={(task) => {
              setFocusSessionTask(task);
              setIsFocusModalOpen(true);
            }}
            onRefresh={refreshAll}
            showToast={showToast}
          />
        )}

        {activeTab === 'syllabus' && (
          <SyllabusView
            subjects={subjects}
            onRefresh={refreshAll}
            showToast={showToast}
          />
        )}

        {activeTab === 'subjects' && (
          <SubjectsView
            subjects={subjects}
            onRefresh={refreshAll}
            showToast={showToast}
          />
        )}

        {activeTab === 'revision' && (
          <RevisionView
            dates={dates}
            onRefresh={refreshAll}
            showToast={showToast}
          />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsView
            feasibility={feasibility}
            dates={dates}
          />
        )}

        {activeTab === 'history' && (
          <HistoryView
            onRefresh={refreshAll}
          />
        )}

        {activeTab === 'import' && (
          <ImportView
            onRefresh={refreshAll}
            showToast={showToast}
            onSuccess={() => setActiveTab('syllabus')}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            settings={settings}
            dates={dates}
            onRefresh={loadInitialData}
            showToast={showToast}
            onOpenOnboarding={() => setShowOnboarding(true)}
          />
        )}
      </main>

      {/* Focus Mode Study Session Modal */}
      {isFocusModalOpen && focusSessionTask && (
        <FocusSessionModal
          task={focusSessionTask}
          onClose={() => {
            setIsFocusModalOpen(false);
            setFocusSessionTask(null);
          }}
          onFinish={async () => {
            setIsFocusModalOpen(false);
            setFocusSessionTask(null);
            await refreshAll();
            showToast('Study session completed and recorded!', 'success');
          }}
          showToast={showToast}
        />
      )}

      {/* First-Run Onboarding Modal */}
      {showOnboarding && (
        <OnboardingModal
          settings={settings}
          onClose={() => setShowOnboarding(false)}
          onComplete={async () => {
            setShowOnboarding(false);
            await loadInitialData();
            showToast('Setup complete! Your personalized schedule is ready.', 'success');
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}

// ----------------- TODAY VIEW -----------------

function TodayView({ todaySchedule, dates, feasibility, onStartSession, onRefresh, showToast }) {
  const [completingTask, setCompletingTask] = useState(null);
  const [completePct, setCompletePct] = useState(100);
  const [actualMins, setActualMins] = useState(60);
  const [confidence, setConfidence] = useState(4);
  const [notes, setNotes] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleQuickComplete = async (taskId, pct, actual) => {
    try {
      const res = await window.StudyPilotAPI.completeTask(taskId, {
        status: pct === 100 ? 'COMPLETED' : 'PARTIALLY_COMPLETED',
        completion_percentage: pct,
        actual_minutes: actual,
        confidence_rating: 4,
        notes: 'Completed from Today view'
      });
      await onRefresh();
      showToast(res.summary || 'Task progress updated successfully!', 'success');
    } catch (err) {
      showToast('Error updating task: ' + err.message, 'error');
    }
  };

  const handleMarkMissed = async (taskId) => {
    try {
      const res = await window.StudyPilotAPI.completeTask(taskId, {
        status: 'MISSED',
        completion_percentage: 0,
        actual_minutes: 0,
        confidence_rating: 1,
        notes: 'Unfinished - carried forward by StudyPilot'
      });
      await onRefresh();
      showToast(res.summary || 'Unfinished task rescheduled automatically.', 'info');
    } catch (err) {
      showToast('Error rescheduling task: ' + err.message, 'error');
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const res = await window.StudyPilotAPI.generateSchedule(true);
      await onRefresh();
      showToast(`Schedule generated with ${res.tasks_scheduled} study sessions.`, 'success');
    } catch (err) {
      showToast('Generation failed: ' + err.message, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const tasks = todaySchedule?.tasks || [];

  return (
    <div className="space-y-6">
      {/* Top Countdown Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">Today's Date</p>
          <p className="text-xl font-bold mt-1 text-slate-100">{dates?.today_str}</p>
          <p className="text-xs text-indigo-400 mt-1">Local Asia/Kolkata</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">First Examination</p>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-extrabold text-indigo-400">{dates?.days_to_exam}</span>
            <span className="text-xs text-slate-400">days left ({dates?.first_exam_str})</span>
          </div>
          <p className="text-[11px] text-muted mt-1">End-Semester Examinations</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">Syllabus Completion Deadline</p>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-extrabold text-emerald-400">{dates?.days_to_deadline}</span>
            <span className="text-xs text-slate-400">days left ({dates?.first_pass_deadline_str})</span>
          </div>
          <p className="text-[11px] text-emerald-400/80 mt-1">Protected 7-Day Revision Buffer</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">Today's Workload</p>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-extrabold text-slate-100">{todaySchedule?.scheduled_minutes || 0}</span>
            <span className="text-xs text-slate-400">/ {todaySchedule?.available_minutes || 0} mins</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Free Buffer: <strong className="text-indigo-400">{todaySchedule?.remaining_free_minutes || 0}m</strong>
          </p>
        </div>
      </div>

      {/* Feasibility Alert */}
      {feasibility && (
        <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
          feasibility.status_label === 'ON_TRACK' ? 'bg-emerald-950/30 border-emerald-800 text-emerald-200' :
          feasibility.status_label === 'TIGHT' ? 'bg-amber-950/30 border-amber-800 text-amber-200' :
          'bg-rose-950/30 border-rose-800 text-rose-200'
        }`}>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm">
                {feasibility.status_label === 'ON_TRACK' ? '✓ Schedule Feasible & On Track' :
                 feasibility.status_label === 'TIGHT' ? '⚠️ Tight Study Schedule' : '🚨 Schedule Overload Detected'}
              </span>
              <span className="text-xs opacity-75">
                ({feasibility.total_remaining_hours}h required vs {feasibility.total_available_hours}h available)
              </span>
            </div>
            <p className="text-xs mt-1 opacity-90">{feasibility.warning_message}</p>
            {feasibility.actionable_recommendations.length > 0 && (
              <ul className="text-xs mt-2 list-disc list-inside space-y-0.5 opacity-80">
                {feasibility.actionable_recommendations.slice(0, 2).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex items-center space-x-2 self-start md:self-auto">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow transition-smooth flex items-center space-x-2"
            >
              <span>{isGenerating ? 'Recalculating...' : 'Regenerate Plan'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Today's Tasks Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Today's Study Plan</h2>
            <p className="text-xs text-muted">
              {tasks.length} topics scheduled for deep learning and problem solving today
            </p>
          </div>
          {todaySchedule && (
            <div className="text-xs text-muted">
              Completion: <strong className="text-indigo-400">{todaySchedule.completion_rate}%</strong>
            </div>
          )}
        </div>

        {tasks.length === 0 ? (
          <div className="glass-panel p-10 rounded-2xl border border-subtle text-center space-y-3">
            <div className="text-3xl">🎉</div>
            <h3 className="font-bold text-base">No Study Tasks Scheduled for Today</h3>
            <p className="text-xs text-muted max-w-md mx-auto">
              Your schedule is currently empty or all of today's work has been marked complete. Click below to generate or advance tasks.
            </p>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition-smooth"
            >
              {isGenerating ? 'Generating...' : 'Generate Realistic Schedule'}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {tasks.map(task => (
              <div
                key={task.id}
                className={`glass-panel p-5 rounded-2xl border transition-smooth ${
                  task.status === 'COMPLETED' ? 'border-emerald-500/40 bg-emerald-950/10' :
                  task.status === 'PARTIALLY_COMPLETED' ? 'border-amber-500/40 bg-amber-950/10' :
                  task.status === 'MISSED' ? 'border-rose-500/40 bg-rose-950/10' :
                  'border-subtle hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="text-xs font-bold px-2.5 py-0.5 rounded-lg text-white"
                        style={{ backgroundColor: task.subject_color || '#6366f1' }}
                      >
                        {task.subject_code} • {task.subject_name}
                      </span>
                      <span className="text-xs text-muted font-medium">Unit {task.unit_number}: {task.unit_title}</span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-surface-elevated text-slate-300">
                        ⏱️ {task.duration_minutes} mins
                      </span>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        task.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                        task.status === 'PARTIALLY_COMPLETED' ? 'bg-amber-500/20 text-amber-400' :
                        task.status === 'MISSED' ? 'bg-rose-500/20 text-rose-400' :
                        'bg-indigo-500/20 text-indigo-400'
                      }`}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-100">{task.topic_title}</h3>

                    {task.subtopics?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {task.subtopics.map((st, i) => (
                          <span key={i} className="code-pill text-[11px] text-slate-300">
                            {st}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Learning Objectives & Breakdown */}
                    <div className="bg-surface/60 p-3 rounded-xl border border-subtle space-y-1.5 text-xs">
                      <div>
                        <strong className="text-indigo-400 font-semibold">Study Method:</strong>{' '}
                        <span className="text-slate-300">{task.study_method}</span>
                      </div>
                      <div className="whitespace-pre-line text-slate-300 leading-relaxed">
                        {task.learning_objectives}
                      </div>
                      <div className="text-slate-400 border-t border-subtle/50 pt-1.5">
                        <strong className="text-slate-300">Suggested Plan:</strong> {task.suggested_breakdown}
                      </div>
                    </div>

                    {task.reasoning && (
                      <p className="text-[11px] text-muted italic">
                        💡 {task.reasoning}
                      </p>
                    )}
                  </div>

                  {/* Action Controls */}
                  <div className="flex flex-row md:flex-col gap-2 shrink-0">
                    <button
                      onClick={() => onStartSession(task)}
                      className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition-smooth flex items-center justify-center space-x-1.5"
                    >
                      <span>⏱️ Focus Mode</span>
                    </button>

                    {task.status !== 'COMPLETED' && (
                      <button
                        onClick={() => handleQuickComplete(task.id, 100, task.duration_minutes)}
                        className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 transition-smooth"
                      >
                        ✓ Mark 100% Done
                      </button>
                    )}

                    <button
                      onClick={() => {
                        setCompletingTask(task);
                        setActualMins(task.duration_minutes);
                        setCompletePct(50);
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 transition-smooth"
                    >
                      ✏️ Partial Progress
                    </button>

                    {task.status === 'PENDING' && (
                      <button
                        onClick={() => handleMarkMissed(task.id)}
                        className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 transition-smooth"
                      >
                        ⏩ Missed / Reschedule
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Partial Completion Modal */}
      {completingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
          <div className="glass-panel p-6 rounded-2xl border border-subtle max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-base">Record Progress for {completingTask.topic_title}</h3>
            
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-muted block mb-1">Percentage Completed ({completePct}%)</label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  value={completePct}
                  onChange={(e) => setCompletePct(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <label className="text-muted block mb-1">Actual Minutes Spent</label>
                <input
                  type="number"
                  min="5"
                  max="300"
                  value={actualMins}
                  onChange={(e) => setActualMins(Number(e.target.value))}
                  className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
                />
              </div>

              <div>
                <label className="text-muted block mb-1">Confidence Rating (1 to 5 Stars)</label>
                <div className="flex space-x-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setConfidence(star)}
                      className={`px-3 py-1.5 rounded-lg border text-sm transition-smooth ${
                        confidence >= star ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-surface border-subtle text-muted'
                      }`}
                    >
                      ★ {star}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-muted block mb-1">Notes / Blockers</label>
                <textarea
                  rows="2"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="What concepts felt tough? What remains unfinished?"
                  className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setCompletingTask(null)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  try {
                    const res = await window.StudyPilotAPI.completeTask(completingTask.id, {
                      status: completePct >= 100 ? 'COMPLETED' : 'PARTIALLY_COMPLETED',
                      completion_percentage: completePct,
                      actual_minutes: actualMins,
                      confidence_rating: confidence,
                      notes: notes
                    });
                    setCompletingTask(null);
                    await onRefresh();
                    showToast(res.summary || 'Progress updated and schedule adapted!', 'success');
                  } catch (err) {
                    showToast('Failed to save progress: ' + err.message, 'error');
                  }
                }}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow"
              >
                Save & Recalculate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- CALENDAR VIEW -----------------

function CalendarView({ dates, onStartSession, onRefresh, showToast }) {
  const [schedules, setSchedules] = useState([]);
  const [selectedDate, setSelectedDate] = useState(dates?.today_str || new Date().toISOString().split('T')[0]);
  const [viewMode, setViewMode] = useState('month'); // 'month' or 'week'

  const loadSchedules = async () => {
    try {
      const data = await window.StudyPilotAPI.getScheduleRange();
      setSchedules(data);
    } catch (err) {
      showToast('Failed to load schedule: ' + err.message, 'error');
    }
  };

  useEffect(() => {
    loadSchedules();
  }, []);

  // Group schedules by date
  const scheduleByDate = useMemo(() => {
    const map = {};
    for (const item of schedules) {
      if (!map[item.scheduled_date]) map[item.scheduled_date] = [];
      map[item.scheduled_date].push(item);
    }
    return map;
  }, [schedules]);

  // Generate calendar days for October/November/December 2026
  const calendarDays = useMemo(() => {
    const days = [];
    const base = new Date(selectedDate || '2026-10-25');
    // Start of month
    const start = new Date(base.getFullYear(), base.getMonth(), 1);
    const end = new Date(base.getFullYear(), base.getMonth() + 1, 0);

    // Padding for day of week
    const firstDayIndex = start.getDay(); // 0 is Sunday
    for (let i = 0; i < firstDayIndex; i++) {
      days.push(null);
    }

    for (let d = 1; d <= end.getDate(); d++) {
      const curr = new Date(base.getFullYear(), base.getMonth(), d);
      const dateStr = curr.toISOString().split('T')[0];
      days.push({
        date: curr,
        dateStr: dateStr,
        dayNumber: d,
        items: scheduleByDate[dateStr] || []
      });
    }
    return days;
  }, [selectedDate, scheduleByDate]);

  const selectedDateTasks = scheduleByDate[selectedDate] || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold">Study Calendar & Timeline</h2>
          <p className="text-xs text-muted">Inspect workload distribution, topic placements, and buffer periods</p>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="p-2 rounded-xl bg-surface border border-subtle text-xs text-slate-100"
          />
          <button
            onClick={onRefresh}
            className="p-2 rounded-xl bg-surface-elevated hover:bg-slate-700 text-xs transition-smooth"
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar Grid */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-muted border-b border-subtle pb-2">
            <span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span>
          </div>

          <div className="grid grid-cols-7 gap-2">
            {calendarDays.map((day, idx) => {
              if (!day) return <div key={idx} className="h-20 rounded-xl bg-surface/20 opacity-25"></div>;
              const isSelected = day.dateStr === selectedDate;
              const isToday = day.dateStr === dates?.today_str;
              const isDeadline = day.dateStr === dates?.first_pass_deadline_str;
              const isExam = day.dateStr === dates?.first_exam_str;
              const totalMins = day.items.reduce((acc, it) => acc + it.duration_minutes, 0);

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedDate(day.dateStr)}
                  className={`h-22 p-2 rounded-xl border flex flex-col justify-between cursor-pointer transition-smooth ${
                    isSelected ? 'border-indigo-500 bg-indigo-500/10 shadow-glow' :
                    isToday ? 'border-emerald-500/60 bg-emerald-950/20' :
                    isDeadline ? 'border-amber-500/60 bg-amber-950/20' :
                    isExam ? 'border-rose-500/60 bg-rose-950/20' :
                    'border-subtle bg-surface/40 hover:bg-surface/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold ${isSelected ? 'text-indigo-400' : 'text-slate-300'}`}>
                      {day.dayNumber}
                    </span>
                    {day.items.length > 0 && (
                      <span className="text-[10px] font-semibold text-slate-400">
                        {totalMins}m
                      </span>
                    )}
                  </div>

                  <div className="space-y-1 overflow-hidden">
                    {day.items.slice(0, 2).map(it => (
                      <div
                        key={it.id}
                        className="text-[10px] truncate px-1.5 py-0.5 rounded text-white font-medium"
                        style={{ backgroundColor: it.subject_color || '#6366f1' }}
                      >
                        {it.topic_title}
                      </div>
                    ))}
                    {day.items.length > 2 && (
                      <span className="text-[9px] text-muted block text-right font-medium">
                        +{day.items.length - 2} more
                      </span>
                    )}
                  </div>

                  {isDeadline && <span className="text-[8px] font-bold text-amber-400 uppercase">Deadline</span>}
                  {isExam && <span className="text-[8px] font-bold text-rose-400 uppercase">Exam</span>}
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Date Details Panel */}
        <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <div className="border-b border-subtle pb-3">
            <p className="text-xs text-muted font-medium uppercase tracking-wider">Selected Day Plan</p>
            <h3 className="text-lg font-bold text-slate-100 mt-1">{selectedDate}</h3>
            <p className="text-xs text-slate-400">
              {selectedDateTasks.length} tasks scheduled • Total {selectedDateTasks.reduce((a, b) => a + b.duration_minutes, 0)} minutes
            </p>
          </div>

          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {selectedDateTasks.length === 0 ? (
              <p className="text-xs text-muted py-8 text-center">No tasks scheduled on this date.</p>
            ) : (
              selectedDateTasks.map(task => (
                <div key={task.id} className="p-3.5 rounded-xl bg-surface border border-subtle space-y-2">
                  <div className="flex items-center justify-between">
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded text-white"
                      style={{ backgroundColor: task.subject_color || '#6366f1' }}
                    >
                      {task.subject_code}
                    </span>
                    <span className="text-xs font-semibold text-slate-300">{task.duration_minutes}m</span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">{task.topic_title}</h4>
                  <p className="text-[11px] text-muted">{task.unit_title}</p>
                  
                  <div className="pt-1 flex justify-end">
                    <button
                      onClick={() => onStartSession(task)}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
                    >
                      Focus Session
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- SYLLABUS EXPLORER -----------------

function SyllabusView({ subjects, onRefresh, showToast }) {
  const [syllabus, setSyllabus] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedMastery, setSelectedMastery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [editingTopic, setEditingTopic] = useState(null);
  const [isNewTopicModalOpen, setIsNewTopicModalOpen] = useState(false);

  const loadSyllabus = async () => {
    try {
      const data = await window.StudyPilotAPI.getSyllabus(
        selectedSubject || null,
        selectedMastery || null
      );
      setSyllabus(data);
    } catch (err) {
      showToast('Failed to load syllabus: ' + err.message, 'error');
    }
  };

  useEffect(() => {
    loadSyllabus();
  }, [selectedSubject, selectedMastery]);

  const filteredTopics = useMemo(() => {
    return syllabus.filter(t => {
      const q = searchQuery.toLowerCase();
      return t.title.toLowerCase().includes(q) ||
        t.unit_title.toLowerCase().includes(q) ||
        t.subject_name.toLowerCase().includes(q);
    });
  }, [syllabus, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold">University Syllabus Explorer</h2>
          <p className="text-xs text-muted">Official courses, units, topics, estimated minutes, and mastery status</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Search topics or units..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="p-2 rounded-xl bg-surface border border-subtle text-xs text-slate-100 w-48"
          />

          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            className="p-2 rounded-xl bg-surface border border-subtle text-xs text-slate-100"
          >
            <option value="">All Subjects</option>
            {subjects.map(s => (
              <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
            ))}
          </select>

          <select
            value={selectedMastery}
            onChange={(e) => setSelectedMastery(e.target.value)}
            className="p-2 rounded-xl bg-surface border border-subtle text-xs text-slate-100"
          >
            <option value="">All Mastery Levels</option>
            <option value="NOT_STARTED">Not Started</option>
            <option value="STUDIED_ONCE">Studied Once</option>
            <option value="PARTIALLY_UNDERSTOOD">Partially Understood</option>
            <option value="NEEDS_REVISION">Needs Revision</option>
            <option value="CONFIDENT">Confident</option>
            <option value="MASTERED">Mastered</option>
          </select>
        </div>
      </div>

      <div className="glass-panel rounded-2xl border border-subtle overflow-hidden">
        <div className="p-4 border-b border-subtle flex items-center justify-between text-xs text-muted">
          <span>Showing {filteredTopics.length} topics across curriculum</span>
        </div>

        <div className="divide-y divide-subtle max-h-[600px] overflow-y-auto">
          {filteredTopics.map(topic => (
            <div key={topic.id} className="p-4 hover:bg-surface/50 transition-smooth flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center space-x-2">
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded text-white"
                    style={{ backgroundColor: topic.subject_color }}
                  >
                    {topic.subject_code}
                  </span>
                  <span className="text-xs text-muted">Unit {topic.unit_number}: {topic.unit_title}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    topic.mastery_level === 'MASTERED' ? 'bg-emerald-500/20 text-emerald-400' :
                    topic.mastery_level === 'CONFIDENT' ? 'bg-indigo-500/20 text-indigo-400' :
                    topic.mastery_level === 'NEEDS_REVISION' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-slate-700/50 text-slate-400'
                  }`}>
                    {topic.mastery_level.replace('_', ' ')}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-100">{topic.title}</h4>

                {topic.subtopics?.length > 0 && (
                  <div className="flex flex-wrap gap-1 text-[11px] text-muted">
                    {topic.subtopics.map((st, i) => (
                      <span key={i} className="code-pill">{st}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex items-center space-x-4 shrink-0 text-xs">
                <div className="text-right">
                  <span className="text-slate-300 font-semibold">{topic.estimated_minutes}m</span>
                  <span className="text-muted block text-[10px]">Base Effort</span>
                </div>

                <button
                  onClick={() => setEditingTopic(topic)}
                  className="px-3 py-1.5 rounded-xl border border-subtle bg-surface hover:bg-surface-elevated text-slate-200 transition-smooth font-medium"
                >
                  Edit Topic
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Edit Topic Modal */}
      {editingTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
          <div className="glass-panel p-6 rounded-2xl border border-subtle max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-base">Edit Topic: {editingTopic.title}</h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-muted block mb-1">Topic Title</label>
                <input
                  type="text"
                  value={editingTopic.title}
                  onChange={(e) => setEditingTopic({ ...editingTopic, title: e.target.value })}
                  className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
                />
              </div>

              <div>
                <label className="text-muted block mb-1">Estimated Effort (Minutes)</label>
                <input
                  type="number"
                  min="15"
                  max="300"
                  step="15"
                  value={editingTopic.estimated_minutes}
                  onChange={(e) => setEditingTopic({ ...editingTopic, estimated_minutes: Number(e.target.value) })}
                  className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
                />
              </div>

              <div>
                <label className="text-muted block mb-1">Mastery Status</label>
                <select
                  value={editingTopic.mastery_level}
                  onChange={(e) => setEditingTopic({ ...editingTopic, mastery_level: e.target.value })}
                  className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
                >
                  <option value="NOT_STARTED">Not Started (100% effort required)</option>
                  <option value="STUDIED_ONCE">Studied Once (90% effort)</option>
                  <option value="PARTIALLY_UNDERSTOOD">Partially Understood (80% effort)</option>
                  <option value="NEEDS_REVISION">Needs Revision (60% effort)</option>
                  <option value="CONFIDENT">Confident (25% effort)</option>
                  <option value="MASTERED">Mastered Through Practice (0% first-pass effort)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setEditingTopic(null)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  try {
                    await window.StudyPilotAPI.updateTopic(editingTopic.id, {
                      title: editingTopic.title,
                      estimated_minutes: editingTopic.estimated_minutes,
                      mastery_level: editingTopic.mastery_level
                    });
                    setEditingTopic(null);
                    await loadSyllabus();
                    await onRefresh();
                    showToast('Topic updated successfully!', 'success');
                  } catch (err) {
                    showToast('Failed to update topic: ' + err.message, 'error');
                  }
                }}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- SUBJECTS VIEW -----------------

function SubjectsView({ subjects, onRefresh, showToast }) {
  const [selectedSubject, setSelectedSubject] = useState(null);

  const loadDetails = async (id) => {
    try {
      const data = await window.StudyPilotAPI.getSubjectDetail(id);
      setSelectedSubject(data);
    } catch (err) {
      showToast('Error loading subject: ' + err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold">Curriculum Subjects</h2>
        <p className="text-xs text-muted">Subject examination dates, priority weightings, and unit-by-unit progress</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {subjects.map(s => {
          const totalTopics = s.topics_count || 1;
          const mastered = s.mastered_count || 0;
          const pct = Math.round((mastered / totalTopics) * 100);

          return (
            <div key={s.id} className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: s.color }}
                    ></span>
                    <span className="code-pill font-bold text-xs">{s.code}</span>
                    <span className="text-xs text-muted font-medium">{s.credits} Credits • {s.total_lectures} Lectures</span>
                  </div>
                  <h3 className="text-base font-bold text-slate-100 mt-1">{s.name}</h3>
                </div>

                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                  s.priority === 'URGENT' ? 'bg-rose-500/20 text-rose-400' :
                  s.priority === 'HIGH' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-slate-700/50 text-slate-300'
                }`}>
                  {s.priority} Priority
                </span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-muted">
                  <span>Coverage & Mastery</span>
                  <span className="font-semibold text-slate-300">{pct}% ({mastered}/{totalTopics})</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-smooth"
                    style={{ width: `${pct}%`, backgroundColor: s.color }}
                  ></div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 text-center text-xs border-t border-subtle">
                <div>
                  <span className="text-muted block text-[10px]">Units</span>
                  <span className="font-bold text-slate-200">{s.units_count} Units</span>
                </div>
                <div>
                  <span className="text-muted block text-[10px]">Est. Hours</span>
                  <span className="font-bold text-slate-200">{Math.round((s.total_estimated_minutes || 0) / 60)}h</span>
                </div>
                <div>
                  <span className="text-muted block text-[10px]">Exam Date</span>
                  <span className="font-bold text-indigo-400">{s.exam_date || 'TBD'}</span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => loadDetails(s.id)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-slate-700 text-slate-200 transition-smooth"
                >
                  View Units & Topics →
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Subject Detail Drawer */}
      {selectedSubject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
          <div className="glass-panel p-6 rounded-2xl border border-subtle max-w-2xl w-full max-h-[85vh] overflow-y-auto space-y-4 shadow-2xl">
            <div className="flex items-start justify-between border-b border-subtle pb-3">
              <div>
                <span className="code-pill font-bold text-xs">{selectedSubject.code}</span>
                <h3 className="text-lg font-bold text-slate-100 mt-1">{selectedSubject.name}</h3>
                <p className="text-xs text-muted">Examination Date: {selectedSubject.exam_date || 'Not announced'}</p>
              </div>
              <button
                onClick={() => setSelectedSubject(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-100"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {selectedSubject.units?.map(u => (
                <div key={u.id} className="p-4 rounded-xl bg-surface border border-subtle space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-200">
                      Unit {u.unit_number}: {u.title}
                    </h4>
                    <span className="text-[10px] text-muted">{u.lecture_allocation} Lectures</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    {u.topics?.map(t => (
                      <div key={t.id} className="p-2 rounded-lg bg-surface-elevated text-xs flex justify-between items-center">
                        <span className="truncate text-slate-300 pr-2">{t.title}</span>
                        <span className="text-[10px] text-indigo-400 shrink-0 font-medium">{t.estimated_minutes}m</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- REVISION VIEW -----------------

function RevisionView({ dates, onRefresh, showToast }) {
  const [revisionData, setRevisionData] = useState(null);

  const loadRevision = async () => {
    try {
      const data = await window.StudyPilotAPI.getRevision();
      setRevisionData(data);
    } catch (err) {
      showToast('Error loading revision items: ' + err.message, 'error');
    }
  };

  useEffect(() => {
    loadRevision();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold">Revision & Practice System</h2>
        <p className="text-xs text-muted">Protected 7-day pre-exam revision buffer and active recall queue</p>
      </div>

      {/* Protected Buffer Info Box */}
      <div className="glass-panel p-5 rounded-2xl border border-indigo-500/30 bg-indigo-950/20 space-y-2">
        <div className="flex items-center space-x-2">
          <span className="text-lg">🛡️</span>
          <h3 className="font-bold text-sm text-indigo-300">Protected Final 7-Day Revision Buffer</h3>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          From <strong className="text-indigo-400">{dates?.first_pass_deadline_str}</strong> through{' '}
          <strong className="text-indigo-400">{dates?.first_exam_str}</strong>, StudyPilot reserves daily study capacity
          strictly for high-yield timed mock tests, formula sheets, weak concept reinforcement, and previous mistakes.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Weak Topics List */}
        <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <div className="border-b border-subtle pb-2">
            <h3 className="font-bold text-sm text-slate-100">Concepts Needing Reinforcement</h3>
            <p className="text-xs text-muted">Flagged by low self-rated confidence or marked for review</p>
          </div>

          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {!revisionData?.weak_topics?.length ? (
              <p className="text-xs text-muted py-6 text-center">No weak topics recorded yet. Mark confidence ratings during sessions.</p>
            ) : (
              revisionData.weak_topics.map(t => (
                <div key={t.id} className="p-3 rounded-xl bg-surface border border-subtle flex items-center justify-between text-xs">
                  <div>
                    <h4 className="font-semibold text-slate-200">{t.title}</h4>
                    <p className="text-[11px] text-muted">{t.subject_name}</p>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                    Needs Review
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Scheduled Buffer Sessions */}
        <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <div className="border-b border-subtle pb-2">
            <h3 className="font-bold text-sm text-slate-100">Buffer Revision Sessions</h3>
            <p className="text-xs text-muted">Sessions scheduled during the final 7 calendar days before exams</p>
          </div>

          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {!revisionData?.buffer_sessions?.length ? (
              <p className="text-xs text-muted py-6 text-center">No buffer sessions populated yet. Generate schedule to populate buffer.</p>
            ) : (
              revisionData.buffer_sessions.map(s => (
                <div key={s.id} className="p-3 rounded-xl bg-surface border border-subtle flex items-center justify-between text-xs">
                  <div className="space-y-1">
                    <span className="code-pill text-[10px]">{s.scheduled_date}</span>
                    <h4 className="font-semibold text-slate-200">{s.topic_title}</h4>
                    <p className="text-[10px] text-muted">{s.study_method}</p>
                  </div>
                  <span className="text-xs font-bold text-slate-300">{s.duration_minutes}m</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- ANALYTICS VIEW -----------------

function AnalyticsView({ feasibility, dates }) {
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    window.StudyPilotAPI.getAnalytics().then(setAnalytics).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold">Analytics & Study Performance</h2>
        <p className="text-xs text-muted">Quantitative evaluation of first-pass coverage, remaining effort, and daily pace</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase">First-Pass Coverage</p>
          <p className="text-2xl font-extrabold text-indigo-400 mt-1">
            {feasibility ? Math.round((feasibility.completed_topics_count / (feasibility.total_topics_count || 1)) * 100) : 0}%
          </p>
          <p className="text-xs text-muted mt-1">{feasibility?.completed_topics_count} of {feasibility?.total_topics_count} topics covered</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase">Remaining Workload</p>
          <p className="text-2xl font-extrabold text-amber-400 mt-1">
            {feasibility?.total_remaining_hours || 0} hrs
          </p>
          <p className="text-xs text-muted mt-1">~{feasibility?.remaining_topics_count} topics left to study</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase">Available Capacity</p>
          <p className="text-2xl font-extrabold text-emerald-400 mt-1">
            {feasibility?.total_available_hours || 0} hrs
          </p>
          <p className="text-xs text-muted mt-1">before {dates?.first_pass_deadline_str}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-subtle">
          <p className="text-xs text-muted font-medium uppercase">Daily Average Needed</p>
          <p className="text-2xl font-extrabold text-slate-100 mt-1">
            {Math.round((feasibility?.daily_average_needed_minutes || 0) / 60 * 10) / 10} hrs/day
          </p>
          <p className="text-xs text-muted mt-1">to meet the 7-day revision deadline</p>
        </div>
      </div>

      {/* Subject-Wise Coverage Breakdown */}
      <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
        <h3 className="font-bold text-sm text-slate-100">Subject Coverage Breakdown</h3>
        <div className="space-y-3">
          {analytics?.subjects_stats?.map(s => {
            const pct = Math.round((s.mastered_topics / (s.total_topics || 1)) * 100);
            return (
              <div key={s.id} className="space-y-1.5 text-xs">
                <div className="flex justify-between font-medium">
                  <span className="text-slate-200">{s.code} - {s.name}</span>
                  <span className="text-muted">{pct}% ({s.mastered_topics}/{s.total_topics} topics)</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-smooth"
                    style={{ width: `${pct}%`, backgroundColor: s.color || '#6366f1' }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ----------------- STUDY HISTORY VIEW -----------------

function HistoryView({ onRefresh }) {
  const [historyData, setHistoryData] = useState({ history: [], change_logs: [] });

  useEffect(() => {
    window.StudyPilotAPI.getHistory().then(setHistoryData).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold">Study History & Adaptive Audit Log</h2>
        <p className="text-xs text-muted">Complete record of completed work, partial progress, and schedule recalculation reasons</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Completed Work History */}
        <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <h3 className="font-bold text-sm text-slate-100">Completed Sessions</h3>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {historyData.history.length === 0 ? (
              <p className="text-xs text-muted py-8 text-center">No study sessions recorded yet.</p>
            ) : (
              historyData.history.map(item => (
                <div key={item.id} className="p-3 rounded-xl bg-surface border border-subtle space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">{item.topic_title}</span>
                    <span className="code-pill text-[10px]">{item.scheduled_date}</span>
                  </div>
                  <div className="flex items-center space-x-3 text-[11px] text-muted">
                    <span>{item.subject_name}</span>
                    <span>• Spent: {item.actual_minutes}m</span>
                    <span>• {item.completion_percentage}% done</span>
                    {item.confidence_rating > 0 && <span>• Confidence: {'★'.repeat(item.confidence_rating)}</span>}
                  </div>
                  {item.notes && <p className="text-[11px] text-slate-300 italic pt-1">"{item.notes}"</p>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Schedule Change Logs */}
        <div className="glass-panel p-5 rounded-2xl border border-subtle space-y-4">
          <h3 className="font-bold text-sm text-slate-100">Schedule Change Explanations (Audit Log)</h3>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {historyData.change_logs.length === 0 ? (
              <p className="text-xs text-muted py-8 text-center">No schedule changes recorded yet.</p>
            ) : (
              historyData.change_logs.map(log => (
                <div key={log.id} className="p-3 rounded-xl bg-surface border border-subtle space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-indigo-400">{log.reason}</span>
                    <span className="text-[10px] text-muted">{log.timestamp}</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">{log.changes_summary}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------- IMPORT HANDOUTS VIEW -----------------

function ImportView({ onRefresh, showToast, onSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [extractedData, setExtractedData] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    setIsUploading(true);
    try {
      const res = await window.StudyPilotAPI.uploadSyllabus(selectedFile);
      setExtractedData(res.data);
      showToast('Document parsed successfully! Review the extracted structure below.', 'success');
    } catch (err) {
      showToast('Upload error: ' + err.message, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCommit = async () => {
    if (!extractedData) return;
    try {
      const res = await window.StudyPilotAPI.commitSyllabus(extractedData);
      showToast(`Imported ${res.topics_added} topics into course syllabus!`, 'success');
      await onRefresh();
      onSuccess();
    } catch (err) {
      showToast('Commit error: ' + err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold">Import Additional Syllabus & Handouts</h2>
        <p className="text-xs text-muted">Upload course handouts, PDFs, Markdown, or text files for automatic local extraction</p>
      </div>

      {/* Upload Box */}
      <div className="glass-panel p-6 rounded-2xl border border-subtle text-center space-y-4">
        <input
          type="file"
          id="syllabus-file-input"
          accept=".pdf,.txt,.md,.markdown"
          onChange={(e) => setSelectedFile(e.target.files[0])}
          className="hidden"
        />

        <div
          onClick={() => document.getElementById('syllabus-file-input').click()}
          className="border-2 border-dashed border-subtle hover:border-indigo-500/50 p-8 rounded-xl cursor-pointer transition-smooth space-y-2 bg-surface/30"
        >
          <div className="text-3xl">📄</div>
          <p className="text-sm font-semibold text-slate-200">
            {selectedFile ? selectedFile.name : 'Click to select PDF, Markdown, or Text handout'}
          </p>
          <p className="text-xs text-muted">Files are processed 100% locally on your computer with zero external API calls.</p>
        </div>

        {selectedFile && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="px-6 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow transition-smooth"
          >
            {isUploading ? 'Extracting Structure...' : 'Extract Syllabus Structure'}
          </button>
        )}
      </div>

      {/* Extracted Review Screen */}
      {extractedData && (
        <div className="glass-panel p-6 rounded-2xl border border-subtle space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-subtle pb-4">
            <div>
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Extraction Review</span>
              <h3 className="text-base font-bold text-slate-100 mt-1">{extractedData.course_name} ({extractedData.course_code})</h3>
            </div>
            <button
              onClick={handleCommit}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow transition-smooth"
            >
              ✓ Save & Merge into Syllabus
            </button>
          </div>

          {/* Warnings / Duplicates */}
          {extractedData.detected_duplicates?.length > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-800 text-xs text-amber-200 space-y-1">
              <strong>⚠️ Duplicate Topics Detected:</strong>
              <p>{extractedData.detected_duplicates.join(', ')}</p>
            </div>
          )}

          <div className="space-y-4">
            {extractedData.units?.map((u, uIdx) => (
              <div key={uIdx} className="p-4 rounded-xl bg-surface border border-subtle space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-200">Unit {u.unit_number}: {u.title}</h4>
                  <span className="text-[10px] text-muted">{u.topics?.length} topics</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  {u.topics?.map((t, tIdx) => (
                    <div key={tIdx} className="p-2 rounded bg-surface-elevated text-xs flex justify-between">
                      <span className="text-slate-300 truncate pr-2">{t.title}</span>
                      <span className="text-indigo-400 font-medium shrink-0">{t.estimated_minutes}m</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------- SETTINGS VIEW -----------------

function SettingsView({ settings, dates, onRefresh, showToast, onOpenOnboarding }) {
  const [formData, setFormData] = useState(settings || {});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (settings) setFormData(settings);
  }, [settings]);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await window.StudyPilotAPI.updateSettings(formData);
      await onRefresh();
      showToast('Settings saved and deadlines recalculated.', 'success');
    } catch (err) {
      showToast('Save error: ' + err.message, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportBackup = async () => {
    try {
      const data = await window.StudyPilotAPI.exportBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `studypilot_backup_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Backup JSON downloaded successfully!', 'success');
    } catch (err) {
      showToast('Backup error: ' + err.message, 'error');
    }
  };

  const handleRestoreBackup = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      await window.StudyPilotAPI.restoreBackup(data);
      await onRefresh();
      showToast('Backup restored successfully!', 'success');
    } catch (err) {
      showToast('Restore error: ' + err.message, 'error');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold">Planner Settings & Parameters</h2>
        <p className="text-xs text-muted">Customise examination dates, study capacity, session lengths, and local backups</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Examination & Deadlines */}
        <div className="glass-panel p-6 rounded-2xl border border-subtle space-y-4">
          <h3 className="font-bold text-sm text-slate-100">Examination & Deadlines</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-muted block mb-1">First Examination Date</label>
              <input
                type="date"
                value={formData.first_exam_date || '2026-11-26'}
                onChange={(e) => setFormData({ ...formData, first_exam_date: e.target.value })}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
              <p className="text-[11px] text-muted mt-1">End-Semester first exam date</p>
            </div>

            <div>
              <label className="text-muted block mb-1">Protected Revision Buffer (Days)</label>
              <input
                type="number"
                min="3"
                max="14"
                value={formData.revision_buffer_days || 7}
                onChange={(e) => setFormData({ ...formData, revision_buffer_days: Number(e.target.value) })}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
              <p className="text-[11px] text-muted mt-1">
                Target Deadline: <strong className="text-indigo-400">{dates?.first_pass_deadline_str}</strong>
              </p>
            </div>
          </div>
        </div>

        {/* Daily Availability */}
        <div className="glass-panel p-6 rounded-2xl border border-subtle space-y-4">
          <h3 className="font-bold text-sm text-slate-100">Daily Study Capacity</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-muted block mb-1">Weekday Study Minutes ({Math.round((formData.weekday_minutes || 180) / 60)}h)</label>
              <input
                type="number"
                min="60"
                max="480"
                step="30"
                value={formData.weekday_minutes || 180}
                onChange={(e) => setFormData({ ...formData, weekday_minutes: Number(e.target.value) })}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>

            <div>
              <label className="text-muted block mb-1">Weekend Study Minutes ({Math.round((formData.weekend_minutes || 300) / 60)}h)</label>
              <input
                type="number"
                min="60"
                max="600"
                step="30"
                value={formData.weekend_minutes || 300}
                onChange={(e) => setFormData({ ...formData, weekend_minutes: Number(e.target.value) })}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center pt-2">
          <button
            type="button"
            onClick={onOpenOnboarding}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-elevated text-slate-300 hover:text-white"
          >
            Launch Setup Wizard
          </button>

          <button
            type="submit"
            disabled={isSaving}
            className="px-6 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow transition-smooth"
          >
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>

      {/* Backup & Restore Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-subtle space-y-4">
        <h3 className="font-bold text-sm text-slate-100">Local-First Backup & Restore</h3>
        <p className="text-xs text-muted">
          Your entire syllabus, study history, schedules, and custom settings are stored locally in SQLite. You can back up or transfer everything via JSON.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            onClick={handleExportBackup}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface border border-subtle hover:bg-surface-elevated text-slate-200"
          >
            ⬇️ Export JSON Backup
          </button>

          <label className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface border border-subtle hover:bg-surface-elevated text-slate-200 cursor-pointer">
            ⬆️ Restore from JSON
            <input type="file" accept=".json" onChange={handleRestoreBackup} className="hidden" />
          </label>
        </div>
      </div>
    </div>
  );
}

// ----------------- FOCUS STUDY SESSION MODAL -----------------

function FocusSessionModal({ task, onClose, onFinish, showToast }) {
  const [secondsLeft, setSecondsLeft] = useState(task.duration_minutes * 60);
  const [isRunning, setIsRunning] = useState(true);
  const [isBreak, setIsBreak] = useState(false);
  const [sessionNotes, setSessionNotes] = useState('');
  const [isFinishing, setIsFinishing] = useState(false);
  const [completionPct, setCompletionPct] = useState(100);
  const [confidence, setConfidence] = useState(4);

  const initialSeconds = task.duration_minutes * 60;

  useEffect(() => {
    let timer = null;
    if (isRunning && secondsLeft > 0) {
      timer = setInterval(() => {
        setSecondsLeft(prev => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isRunning, secondsLeft]);

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleFinishConfirm = async () => {
    const elapsedSeconds = initialSeconds - secondsLeft;
    const actualMinutes = Math.max(1, Math.round(elapsedSeconds / 60));
    try {
      await window.StudyPilotAPI.completeTask(task.id, {
        status: completionPct >= 100 ? 'COMPLETED' : 'PARTIALLY_COMPLETED',
        completion_percentage: completionPct,
        actual_minutes: actualMinutes,
        confidence_rating: confidence,
        notes: sessionNotes
      });
      onFinish();
    } catch (err) {
      showToast('Error saving session: ' + err.message, 'error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
      <div className="glass-panel p-6 rounded-3xl border border-subtle max-w-lg w-full space-y-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div>
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded text-white"
              style={{ backgroundColor: task.subject_color }}
            >
              {task.subject_code}
            </span>
            <h3 className="font-bold text-base text-slate-100 mt-1">{task.topic_title}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-100">
            ✕
          </button>
        </div>

        {/* Big Timer Display */}
        <div className="text-center py-4 space-y-2">
          <div className="text-5xl font-mono font-extrabold tracking-wider text-slate-100">
            {formatTime(secondsLeft)}
          </div>
          <p className="text-xs text-muted">
            {isBreak ? '☕ Break Session' : `🎯 Focused Study: ${task.study_method}`}
          </p>
        </div>

        {/* Timer Controls */}
        <div className="flex justify-center items-center space-x-3">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow"
          >
            {isRunning ? '⏸️ Pause' : '▶️ Resume'}
          </button>
          <button
            onClick={() => {
              setIsBreak(!isBreak);
              setSecondsLeft(isBreak ? task.duration_minutes * 60 : 5 * 60);
            }}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface border border-subtle text-slate-300"
          >
            {isBreak ? 'Back to Study' : 'Take 5m Break'}
          </button>
          <button
            onClick={() => setIsFinishing(true)}
            className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow"
          >
            ✓ Finish Session
          </button>
        </div>

        {/* Objectives / Suggested Plan */}
        <div className="bg-surface/60 p-3.5 rounded-xl border border-subtle text-xs space-y-2">
          <div>
            <strong className="text-indigo-400">Objectives:</strong>
            <p className="text-slate-300 whitespace-pre-line mt-0.5">{task.learning_objectives}</p>
          </div>
          <div className="border-t border-subtle pt-2">
            <strong className="text-slate-400">Breakdown:</strong>
            <p className="text-slate-300">{task.suggested_breakdown}</p>
          </div>
        </div>

        {/* Scratchpad Notes */}
        <div>
          <label className="text-xs text-muted block mb-1">Session Scratchpad</label>
          <textarea
            rows="2"
            value={sessionNotes}
            onChange={(e) => setSessionNotes(e.target.value)}
            placeholder="Jot down active recall items, formulas, or tricky edge cases..."
            className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-xs text-slate-100"
          />
        </div>

        {/* Finish Confirmation Dialog */}
        {isFinishing && (
          <div className="p-4 rounded-xl bg-surface border border-indigo-500/40 space-y-3">
            <h4 className="font-bold text-xs text-indigo-300">Session Evaluation</h4>
            <div className="space-y-2 text-xs">
              <div>
                <label className="text-muted block">Completion: {completionPct}%</label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="10"
                  value={completionPct}
                  onChange={(e) => setCompletionPct(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <label className="text-muted block mb-1">Confidence Rating</label>
                <div className="flex space-x-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setConfidence(star)}
                      className={`px-2.5 py-1 rounded text-xs border ${
                        confidence >= star ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-surface border-subtle text-muted'
                      }`}
                    >
                      ★ {star}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setIsFinishing(false)}
                  className="px-3 py-1.5 rounded-lg text-xs text-slate-400"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFinishConfirm}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white"
                >
                  Confirm & Save
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------- ONBOARDING WIZARD -----------------

function OnboardingModal({ settings, onClose, onComplete, showToast }) {
  const [step, setStep] = useState(1);
  const [examDate, setExamDate] = useState(settings?.first_exam_date || '2026-11-26');
  const [bufferDays, setBufferDays] = useState(settings?.revision_buffer_days || 7);
  const [weekdayMins, setWeekdayMins] = useState(settings?.weekday_minutes || 180);
  const [weekendMins, setWeekendMins] = useState(settings?.weekend_minutes || 300);

  const handleFinishOnboarding = async () => {
    try {
      await window.StudyPilotAPI.updateSettings({
        first_exam_date: examDate,
        revision_buffer_days: bufferDays,
        weekday_minutes: weekdayMins,
        weekend_minutes: weekendMins,
        onboarding_completed: true
      });
      // Generate initial schedule
      await window.StudyPilotAPI.generateSchedule(false);
      onComplete();
    } catch (err) {
      showToast('Onboarding error: ' + err.message, 'error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
      <div className="glass-panel p-6 rounded-3xl border border-subtle max-w-lg w-full space-y-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div>
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Step {step} of 3</span>
            <h3 className="font-bold text-base text-slate-100 mt-0.5">Welcome to StudyPilot</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-100">
            ✕
          </button>
        </div>

        {step === 1 && (
          <div className="space-y-4 text-xs">
            <p className="text-slate-300 leading-relaxed">
              StudyPilot guarantees complete syllabus coverage and protects a 7-day revision buffer before your examinations.
            </p>
            <div>
              <label className="text-muted block mb-1">First Examination Date</label>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>
            <div>
              <label className="text-muted block mb-1">Revision Buffer (Calendar Days)</label>
              <input
                type="number"
                min="3"
                max="14"
                value={bufferDays}
                onChange={(e) => setBufferDays(Number(e.target.value))}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 text-xs">
            <p className="text-slate-300 leading-relaxed">
              Realistic scheduling: StudyPilot will never schedule more work than your configured daily availability.
            </p>
            <div>
              <label className="text-muted block mb-1">Weekday Study Minutes ({Math.round(weekdayMins / 60)} hours/day)</label>
              <input
                type="number"
                min="60"
                max="480"
                step="30"
                value={weekdayMins}
                onChange={(e) => setWeekdayMins(Number(e.target.value))}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>
            <div>
              <label className="text-muted block mb-1">Weekend Study Minutes ({Math.round(weekendMins / 60)} hours/day)</label>
              <input
                type="number"
                min="60"
                max="600"
                step="30"
                value={weekendMins}
                onChange={(e) => setWeekendMins(Number(e.target.value))}
                className="w-full p-2.5 rounded-xl bg-surface border border-subtle text-slate-100"
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 text-xs">
            <p className="text-slate-300 leading-relaxed">
              You are ready! When you click below, StudyPilot's deterministic scheduling engine will calculate your topic prerequisites, assess feasibility, and generate your custom daily study plan.
            </p>
            <div className="p-3 rounded-xl bg-surface border border-subtle space-y-1">
              <div className="flex justify-between">
                <span className="text-muted">First Examination:</span>
                <span className="font-bold text-indigo-400">{examDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Revision Buffer:</span>
                <span className="font-bold text-emerald-400">{bufferDays} calendar days</span>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-between items-center pt-2 border-t border-subtle">
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200"
            >
              ← Back
            </button>
          ) : <div></div>}

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow"
            >
              Continue →
            </button>
          ) : (
            <button
              onClick={handleFinishOnboarding}
              className="px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow"
            >
              🚀 Generate My Study Plan
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Mount React Root
const rootElement = document.getElementById('root');
const root = ReactDOM.createRoot(rootElement);
root.render(<App />);
