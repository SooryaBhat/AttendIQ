const API_BASE_URL = "http://127.0.0.1:8000";

function getAuthToken() {
  return localStorage.getItem("attendiq_token");
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("attendiq_user")) || null;
  } catch (error) {
    return null;
  }
}

function saveAuthData(token, user) {
  localStorage.setItem("attendiq_token", token);
  localStorage.setItem("attendiq_user", JSON.stringify(user));
}

function clearAuthData() {
  localStorage.removeItem("attendiq_token");
  localStorage.removeItem("attendiq_user");
}

function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const defaultHeaders = {
    Accept: "application/json",
    ...getAuthHeaders(),
    ...options.headers,
  };

  const response = await fetch(url, {
    method: options.method || "GET",
    headers: defaultHeaders,
    body: options.body,
  });

  const contentType = response.headers.get("Content-Type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const message = payload?.detail || payload?.message || response.statusText || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

async function loginUser(credentials) {
  return request("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });
}

async function fetchCurrentUser() {
  return request("/auth/me", {
    method: "GET",
  });
}

async function getDepartments() {
  return request("/departments");
}

async function createDepartment(payload) {
  return request("/departments", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function updateDepartment(id, payload) {
  return request(`/departments/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function deleteDepartment(id) {
  return request(`/departments/${id}`, {
    method: "DELETE",
  });
}

async function getStudents(search, departmentId) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (departmentId) params.set("department_id", departmentId);
  const query = params.toString();
  return request(`/students${query ? `?${query}` : ""}`);
}

async function getStudentById(id) {
  return request(`/students/${id}`);
}

async function createStudent(payload) {
  return request("/students", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function updateStudent(id, payload) {
  return request(`/students/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function deleteStudent(id) {
  return request(`/students/${id}`, {
    method: "DELETE",
  });
}

async function getFaculties(search, departmentId) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (departmentId) params.set("department_id", departmentId);
  return request(`/faculties${params.toString() ? `?${params.toString()}` : ""}`);
}

async function getFacultyById(id) {
  return request(`/faculties/${id}`);
}

async function createFaculty(payload) {
  return request("/faculties", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function updateFaculty(id, payload) {
  return request(`/faculties/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function deleteFaculty(id) {
  return request(`/faculties/${id}`, {
    method: "DELETE",
  });
}

// ============================================================================
// ATTENDANCE API FUNCTIONS
// ============================================================================

async function getAttendanceSessions(subjectId = null) {
  const params = new URLSearchParams();
  if (subjectId) params.set("subject_id", subjectId);
  const query = params.toString();
  return request(`/attendance/sessions${query ? `?${query}` : ""}`);
}

async function getAttendanceSession(sessionId) {
  return request(`/attendance/sessions/${sessionId}`);
}

async function createAttendanceSession(payload) {
  return request("/attendance/sessions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function startAttendanceSession(sessionId) {
  return request(`/attendance/sessions/${sessionId}/start`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
}

async function endAttendanceSession(sessionId) {
  return request(`/attendance/sessions/${sessionId}/end`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
}

async function markAttendance(sessionId, studentId, attendanceStatus) {
  return request("/attendance/mark", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      student_id: studentId,
      attendance_status: attendanceStatus,
    }),
  });
}

async function getSessionAttendanceRecords(sessionId) {
  return request(`/attendance/sessions/${sessionId}/records`);
}
