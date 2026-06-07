const LOCAL_API_BASE_URL = "http://127.0.0.1:4040 ";
const API_BASE_URL = window.location.protocol.startsWith("http")
  ? (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? LOCAL_API_BASE_URL
      : window.location.origin)
  : LOCAL_API_BASE_URL;

function ensureFavicon() {
  const origin = window.location.protocol.startsWith("http")
    ? (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? LOCAL_API_BASE_URL
        : window.location.origin)
    : LOCAL_API_BASE_URL;
  const iconHref = new URL("/assets/images/logo.svg", origin).href;
  let iconLink = document.querySelector("link[rel~='icon']");
  if (!iconLink) {
    iconLink = document.createElement("link");
    iconLink.rel = "icon";
    iconLink.type = "image/svg+xml";
    document.head.appendChild(iconLink);
  }
  iconLink.href = iconHref;
}

ensureFavicon();

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
    "ngrok-skip-browser-warning": "true",
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

async function getDepartmentAdmins(search, departmentId) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (departmentId) params.set("department_id", departmentId);
  return request(`/super-admin/admins${params.toString() ? `?${params.toString()}` : ""}`);
}

async function getDepartmentAdminById(id) {
  return request(`/super-admin/admins/${id}`);
}

async function createDepartmentAdmin(payload) {
  return request("/super-admin/admins", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function updateDepartmentAdmin(id, payload) {
  return request(`/super-admin/admins/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

async function activateDepartmentAdmin(id) {
  return request(`/super-admin/admins/${id}/activate`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
}

async function deactivateDepartmentAdmin(id) {
  return request(`/super-admin/admins/${id}/deactivate`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
}

async function deleteDepartmentAdmin(id) {
  return request(`/super-admin/admins/${id}`, {
    method: "DELETE",
  });
}

async function getSuperAdminSummary() {
  return request("/super-admin/summary");
}

async function getSuperAdminDepartmentStats() {
  return request("/super-admin/department-stats");
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

async function getSubjects() {
  return request("/subjects");
}

async function getSubjectById(id) {
  return request(`/subjects/${id}`);
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

async function deleteAttendanceSession(sessionId) {
  return request(`/attendance/sessions/${sessionId}`, {
    method: "DELETE",
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

async function getStudentAttendanceHistory() {
  return request("/attendance/student-history");
}

// ============================================================================
// ENROLLMENT & SUBJECT API
// ============================================================================

async function joinSubjectByCode(subjectCode, studentId) {
  return request("/subjects/join-by-code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject_code: subjectCode, student_id: studentId || undefined }),
  });
}

async function enrollStudentInSubject(subjectId, studentId) {
  return request(`/subjects/${subjectId}/enroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId || undefined }),
  });
}

async function unenrollStudentFromSubject(subjectId, studentId) {
  return request(`/subjects/${subjectId}/unenroll/${studentId}`, { method: "DELETE" });
}

async function getStudentSubjects(studentId) {
  return request(`/subjects/students/${studentId}`);
}

async function getSubjectStudents(subjectId) {
  return request(`/subjects/${subjectId}/students`);
}

async function createSubject(payload) {
  return request("/subjects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function updateSubject(id, payload) {
  return request(`/subjects/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function deleteSubject(id) {
  return request(`/subjects/${id}`, { method: "DELETE" });
}

// ============================================================================
// ANALYTICS API
// ============================================================================

async function getAnalyticsSummary() {
  return request("/analytics/summary");
}

async function getStudentsByDepartment() {
  return request("/analytics/students-by-department");
}

async function getAttendanceTrend() {
  return request("/analytics/attendance-trend");
}

async function getDepartmentComparison() {
  return request("/analytics/department-comparison");
}

async function getSubjectAttendance() {
  return request("/analytics/subject-attendance");
}

async function getTopStudents(limit = 10) {
  return request(`/analytics/top-students?limit=${limit}`);
}

async function getLowStudents(limit = 10) {
  return request(`/analytics/low-students?limit=${limit}`);
}

// ============================================================================
// STUDENT ACTIVATION (Dept Admin)
// ============================================================================

async function createStudentWithActivation(payload) {
  return request("/students/create-with-activation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function bulkImportStudents(departmentId, students) {
  return request(`/students/${departmentId}/bulk-import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(students),
  });
}

// ============================================================================
// PROFILE
// ============================================================================

async function updateProfile(payload) {
  const user = getStoredUser();
  if (!user) throw new Error("Not logged in");
  const role = user.role;
  let path;
  if (role === "student") path = `/students/${user.id}`;
  else if (role === "faculty") path = `/faculties/${user.id}`;
  else path = `/auth/profile`;     // fallback
  return request(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function changePassword(newPassword) {
  const user = getStoredUser();
  if (!user) throw new Error("Not logged in");
  return updateProfile({ password: newPassword });
}

// ============================================================================
// BIOMETRIC STATUS
// ============================================================================

async function getBiometricStatus() {
  return request("/biometric/status");
}
