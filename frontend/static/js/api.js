// StudyPilot API Client
const API_BASE = '';

const API = {
  async get(endpoint) {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return res.json();
  },

  async post(endpoint, data) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return res.json();
  },

  async put(endpoint, data) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return res.json();
  },

  async delete(endpoint) {
    const res = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return res.json();
  },

  async upload(endpoint, formData) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  // High-level API methods
  getTime: () => API.get('/api/time'),
  getDates: () => API.get('/api/dates'),
  getFeasibility: () => API.get('/api/feasibility'),
  getSettings: () => API.get('/api/settings'),
  updateSettings: (settings) => API.put('/api/settings', settings),
  
  getSubjects: () => API.get('/api/subjects'),
  getSubjectDetail: (id) => API.get(`/api/subjects/${id}`),
  updateSubject: (id, data) => API.put(`/api/subjects/${id}`, data),
  createSubject: (data) => API.post('/api/subjects', data),

  getSyllabus: (subjectId = null, mastery = null) => {
    let url = '/api/syllabus';
    const params = [];
    if (subjectId) params.push(`subject_id=${subjectId}`);
    if (mastery) params.push(`mastery=${mastery}`);
    if (params.length) url += `?${params.join('&')}`;
    return API.get(url);
  },
  createTopic: (data) => API.post('/api/topics', data),
  updateTopic: (id, data) => API.put(`/api/topics/${id}`, data),
  deleteTopic: (id) => API.delete(`/api/topics/${id}`),

  getTodaySchedule: () => API.get('/api/schedule/today'),
  getScheduleRange: (start = null, end = null) => {
    let url = '/api/schedule';
    const params = [];
    if (start) params.push(`start_date=${start}`);
    if (end) params.push(`end_date=${end}`);
    if (params.length) url += `?${params.join('&')}`;
    return API.get(url);
  },
  generateSchedule: (preserveCompleted = true) => API.post(`/api/schedule/generate?preserve_completed=${preserveCompleted}`, {}),
  completeTask: (scheduleId, data) => API.post(`/api/schedule/${scheduleId}/complete`, data),

  startSession: (topicId, scheduleId = null) => API.post('/api/sessions/start', { topic_id: topicId, schedule_id: scheduleId }),
  finishSession: (data) => API.post('/api/sessions/finish', data),

  // Daily DSA (2 questions)
  getDailyDSA: () => API.get('/api/dsa/today'),
  updateDSAAssignment: (id, data) => API.put(`/api/dsa/assignment/${id}`, data),
  getAllDSA: () => API.get('/api/dsa/all'),

  // English Speaking (30 min)
  getEnglishToday: () => API.get('/api/english/today'),
  saveEnglishLog: (data) => API.post('/api/english/log', data),
  getEnglishHistory: () => API.get('/api/english/history'),

  // Daily Motivational Quotes
  getDailyQuote: () => API.get('/api/quotes/today'),
  toggleQuoteFavorite: (id) => API.post(`/api/quotes/${id}/favorite`, {}),
  getAllQuotes: () => API.get('/api/quotes/all'),

  // Extra Time Recommendations
  getExtraTime: () => API.get('/api/extra-time'),

  // Calendar
  getCalendarEvents: (start = null, end = null) => {
    let url = '/api/calendar/events';
    const params = [];
    if (start) params.push(`start=${start}`);
    if (end) params.push(`end=${end}`);
    if (params.length) url += `?${params.join('&')}`;
    return API.get(url);
  },
  createCalendarEvent: (data) => API.post('/api/calendar/events', data),
  updateCalendarEvent: (id, data) => API.put(`/api/calendar/events/${id}`, data),
  deleteCalendarEvent: (id) => API.delete(`/api/calendar/events/${id}`),

  getAnalytics: () => API.get('/api/analytics'),
  getHistory: () => API.get('/api/history'),
  getRevision: () => API.get('/api/revision'),

  // Full Horizon Schedule
  getFullSchedule: () => API.get('/api/schedule/full'),

  // Topic Status Checklist Control
  updateTopicStatus: (topicId, masteryLevel, notes = null) => API.put(`/api/topics/${topicId}/status`, { mastery_level: masteryLevel, notes }),

  // Wasted Time & Shortfall
  getWastedTimeSummary: (dateStr = null) => API.get(`/api/wasted-time/summary${dateStr ? '?date_str=' + dateStr : ''}`),
  logWastedTime: (data) => API.post('/api/wasted-time/log', data),
  getWastedTimeGraph: (startDate = null, endDate = null) => {
    let url = '/api/wasted-time/graph';
    const params = [];
    if (startDate) params.push(`start_date=${startDate}`);
    if (endDate) params.push(`end_date=${endDate}`);
    if (params.length) url += `?${params.join('&')}`;
    return API.get(url);
  },

  // DSA Topic Recommendations
  getDSATopics: (dateStr = null) => API.get(`/api/dsa/topics${dateStr ? '?date_str=' + dateStr : ''}`),
  updateDSATopic: (id, data) => API.put(`/api/dsa/topic/${id}`, data),

  // Simple English Practice
  getEnglishStatus: (dateStr = null) => API.get(`/api/english/status${dateStr ? '?date_str=' + dateStr : ''}`),
  saveEnglishSimple: (data) => API.post('/api/english/simple-log', data),

  // Courses & Units Checklist Hierarchy
  getCourses: () => API.get('/api/courses'),

  uploadSyllabus: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return API.upload('/api/import/upload', fd);
  },
  commitSyllabus: (data) => API.post('/api/import/commit', data),

  exportBackup: () => API.get('/api/backup/export'),
  restoreBackup: (data) => API.post('/api/backup/restore', data)
};

window.LastChanceAPI = API;
window.StudyPilotAPI = API;
