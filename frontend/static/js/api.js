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

  getAnalytics: () => API.get('/api/analytics'),
  getHistory: () => API.get('/api/history'),
  getRevision: () => API.get('/api/revision'),

  uploadSyllabus: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return API.upload('/api/import/upload', fd);
  },
  commitSyllabus: (data) => API.post('/api/import/commit', data),

  exportBackup: () => API.get('/api/backup/export'),
  restoreBackup: (data) => API.post('/api/backup/restore', data)
};

window.StudyPilotAPI = API;
