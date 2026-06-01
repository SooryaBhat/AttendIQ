/*
  Attendance Session Module for AttendIQ
  Handles faculty and student attendance functionality
*/

// Global State
let sessionState = {
  isActive: false,
  selectedSession: null,
  startTime: null,
  elapsedSeconds: 0,
  currentStudent: null,
};

let sessionTimerInterval = null;

// Initialize
document.addEventListener("DOMContentLoaded", function () {
  initializeEventListeners();
  initializePage();
});

function initializeEventListeners() {
  const subjectSelect = document.getElementById("subjectSelect");
  const startSessionBtn = document.getElementById("startSessionBtn");
  const endSessionBtn = document.getElementById("endSessionBtn");
  const closeDetailsBtn = document.getElementById("closeDetailsBtn");
  const joinSessionBtn = document.getElementById("joinSessionBtn");
  const markAttendanceBtn = document.getElementById("markAttendanceBtn");

  if (subjectSelect) {
    subjectSelect.addEventListener("change", handleSubjectChange);
  }

  if (startSessionBtn) {
    startSessionBtn.addEventListener("click", startSession);
  }

  if (endSessionBtn) {
    endSessionBtn.addEventListener("click", endSession);
  }

  if (closeDetailsBtn) {
    closeDetailsBtn.addEventListener("click", closeSessionDetails);
  }

  if (joinSessionBtn) {
    joinSessionBtn.addEventListener("click", handleJoinSession);
  }

  if (markAttendanceBtn) {
    markAttendanceBtn.addEventListener("click", handleMarkAttendance);
  }
}

function initializePage() {
  const path = window.location.pathname.toLowerCase();

  if (path.includes("faculty/attendance")) {
    initializeFacultyAttendance();
  } else if (path.includes("student/attendance")) {
    initializeStudentAttendance();
  }
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("attendiq_user")) || null;
  } catch (error) {
    return null;
  }
}

function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function showError(message) {
  alert("❌ " + message);
  console.error(message);
}

function showSuccess(message) {
  alert("✓ " + message);
}

// ============================================================================
// FACULTY ATTENDANCE MODULE
// ============================================================================

async function initializeFacultyAttendance() {
  try {
    const user = getStoredUser();
    if (!user) {
      showError("User not found. Please log in again.");
      return;
    }

    await renderSessionsHistory();
  } catch (error) {
    showError("Unable to initialize faculty attendance: " + error.message);
  }
}

function handleSubjectChange(event) {
  const startSessionBtn = document.getElementById("startSessionBtn");
  if (startSessionBtn) {
    startSessionBtn.disabled = !event.target.value;
  }
}

async function startSession() {
  const subjectSelect = document.getElementById("subjectSelect");
  if (!subjectSelect) return;

  const subjectId = subjectSelect.value;
  if (!subjectId) return;

  try {
    const user = getStoredUser();
    if (!user) {
      showError("User not found. Please log in again.");
      return;
    }

    const sessionPayload = {
      subject_id: subjectId,
      faculty_id: user.id,
      session_name: `Session ${new Date().toLocaleTimeString()}`,
    };

    const createdSession = await createAttendanceSession(sessionPayload);
    const startedSession = await startAttendanceSession(createdSession.id);

    sessionState.isActive = true;
    sessionState.selectedSession = startedSession;
    sessionState.startTime = new Date();
    sessionState.elapsedSeconds = 0;

    showSessionActive(startedSession);
    await renderAttendanceRecords(startedSession.id);
    startSessionTimer();

    subjectSelect.disabled = true;
    showSuccess("Attendance session started successfully.");
  } catch (error) {
    showError("Failed to start session: " + error.message);
  }
}

async function renderAttendanceRecords(sessionId) {
  const tbody = document.getElementById("studentsTableBody");
  const activeStudentsCount = document.getElementById("activeStudentsCount");
  const markedPresentCount = document.getElementById("markedPresentCount");
  const absentCountEl = document.getElementById("absentCount");

  if (!tbody) return;

  try {
    const records = await getSessionAttendanceRecords(sessionId);
    if (!records || records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px;">No attendance records yet.</td></tr>';
      if (activeStudentsCount) activeStudentsCount.textContent = "0";
      if (markedPresentCount) markedPresentCount.textContent = "0";
      if (absentCountEl) absentCountEl.textContent = "0";
      return;
    }

    tbody.innerHTML = records
      .map((record) => {
        const status = record.attendance_status || "pending";
        const statusClass = status === "present" ? "present" : status === "absent" ? "absent" : "pending";
        return `
        <tr>
          <td>${record.student_id.substring(0, 8)}</td>
          <td>${record.student_id.substring(0, 8)}</td>
          <td>${record.marked_at ? new Date(record.marked_at).toLocaleTimeString() : "-"}</td>
          <td><span class="status-pill ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span></td>
          <td>
            <div class="table-actions">
              <button class="action-btn mark-present" onclick="markStudentAttendance('${record.student_id}', 'present')">✓</button>
              <button class="action-btn mark-absent" onclick="markStudentAttendance('${record.student_id}', 'absent')">✗</button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");

    const presentCount = records.filter((r) => r.attendance_status === "present").length;
    const absentCount = records.filter((r) => r.attendance_status === "absent").length;

    if (activeStudentsCount) activeStudentsCount.textContent = records.length;
    if (markedPresentCount) markedPresentCount.textContent = presentCount;
    if (absentCountEl) absentCountEl.textContent = absentCount;
  } catch (error) {
    console.error(error);
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:red;">Failed to load attendance records.</td></tr>';
  }
}

async function markStudentAttendance(studentId, status) {
  if (!sessionState.selectedSession) {
    showError("No active session selected.");
    return;
  }

  try {
    await markAttendance(sessionState.selectedSession.id, studentId, status);
    await renderAttendanceRecords(sessionState.selectedSession.id);
    showSuccess(`Student marked ${status}.`);
  } catch (error) {
    showError("Failed to update student attendance: " + error.message);
  }
}

async function endSession() {
  if (!sessionState.selectedSession) {
    showError("No active session to end.");
    return;
  }

  const confirmed = confirm("Are you sure you want to end this attendance session?");
  if (!confirmed) return;

  try {
    await endAttendanceSession(sessionState.selectedSession.id);

    if (sessionTimerInterval) {
      clearInterval(sessionTimerInterval);
    }

    sessionState.isActive = false;
    sessionState.selectedSession = null;
    sessionState.startTime = null;
    sessionState.elapsedSeconds = 0;

    const sessionActive = document.getElementById("sessionActive");
    const studentsListSection = document.getElementById("studentsListSection");
    const subjectSelect = document.getElementById("subjectSelect");
    const startSessionBtn = document.getElementById("startSessionBtn");

    if (sessionActive) sessionActive.style.display = "none";
    if (studentsListSection) studentsListSection.style.display = "none";
    if (subjectSelect) {
      subjectSelect.disabled = false;
      subjectSelect.value = "";
    }
    if (startSessionBtn) startSessionBtn.disabled = true;

    await renderSessionsHistory();
    showSuccess("Attendance session ended successfully.");
  } catch (error) {
    showError("Failed to end session: " + error.message);
  }
}

function showSessionActive(session) {
  const sessionActive = document.getElementById("sessionActive");
  const activeSubject = document.getElementById("activeSubject");
  const studentsListSection = document.getElementById("studentsListSection");

  if (sessionActive) {
    sessionActive.style.display = "block";
    if (activeSubject) {
      activeSubject.textContent = session.session_name || `Session ${session.id.substring(0, 8)}`;
    }
  }

  if (studentsListSection) {
    studentsListSection.style.display = "block";
  }
}

function startSessionTimer() {
  if (sessionTimerInterval) {
    clearInterval(sessionTimerInterval);
  }

  sessionTimerInterval = setInterval(() => {
    sessionState.elapsedSeconds++;
    updateTimerDisplay();
  }, 1000);
}

function updateTimerDisplay() {
  const sessionTimer = document.getElementById("sessionTimer");
  if (!sessionTimer) return;

  sessionTimer.textContent = formatTime(sessionState.elapsedSeconds);
}

async function renderSessionsHistory() {
  const tbody = document.getElementById("sessionsHistoryBody");
  if (!tbody) return;

  try {
    const sessions = await getAttendanceSessions();
    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px;">No sessions found.</td></tr>';
      return;
    }

    tbody.innerHTML = sessions
      .map((session) => {
        const start = session.start_time ? new Date(session.start_time) : null;
        const end = session.end_time ? new Date(session.end_time) : null;
        const duration = start && end ? `${Math.max(0, Math.floor((end - start) / 60000))} min` : "-";

        return `
        <tr>
          <td>${session.session_name || `Session ${session.id.substring(0, 8)}`}</td>
          <td>${start ? start.toLocaleDateString() : "-"}</td>
          <td>${duration}</td>
          <td>—</td>
          <td>—</td>
          <td>—</td>
        </tr>
      `;
      })
      .join("");
  } catch (error) {
    console.error(error);
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:red;">Failed to load sessions.</td></tr>';
  }
}

// ============================================================================
// STUDENT ATTENDANCE MODULE
// ============================================================================

async function initializeStudentAttendance() {
  try {
    const user = getStoredUser();
    if (!user) {
      showError("User not found. Please log in again.");
      return;
    }

    sessionState.currentStudent = user;
    await renderActiveSessions();
    await renderAttendanceHistory();
  } catch (error) {
    showError("Unable to initialize student attendance: " + error.message);
  }
}

async function renderActiveSessions() {
  const container = document.getElementById("activeSessionsContainer");
  const noSessionsMessage = document.getElementById("noSessionsMessage");

  if (!container) return;

  try {
    const sessions = await getAttendanceSessions();
    const activeSessions = sessions.filter((s) => s.status === "started");

    if (activeSessions.length === 0) {
      if (noSessionsMessage) noSessionsMessage.style.display = "grid";
      container.innerHTML = "";
      return;
    }

    if (noSessionsMessage) noSessionsMessage.style.display = "none";

    container.innerHTML = activeSessions
      .map((session) => {
        const startedAt = session.start_time ? new Date(session.start_time).toLocaleTimeString() : "-";
        return `
        <div class="session-card" onclick="viewSessionDetails('${session.id}', this)">
          <div class="session-card-header">
            <div class="session-card-title">
              <h3>${session.session_name || `Session ${session.id.substring(0, 8)}`}</h3>
              <span class="subject-code">${session.subject_id.substring(0, 8)}</span>
            </div>
            <div class="session-card-badge">🔴 Live</div>
          </div>

          <div class="session-card-info">
            <div class="session-card-info-item">
              <span class="session-card-info-label">Started</span>
              <span class="session-card-info-value">${startedAt}</span>
            </div>
          </div>

          <div class="session-card-footer">
            <button class="session-card-btn primary" onclick="handleJoinSessionClick('${session.id}', event)">👋 Join Session</button>
            <button class="session-card-btn" onclick="viewSessionDetails('${session.id}', this.closest('.session-card'), event)">ℹ️ Details</button>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (error) {
    console.error(error);
    container.innerHTML = '<div style="text-align:center; padding:20px; color:red;">Failed to load active sessions.</div>';
  }
}

async function viewSessionDetails(sessionId, cardElement, event) {
  if (event) event.stopPropagation();

  const detailsSection = document.getElementById("sessionDetailsSection");
  if (!detailsSection) return;

  try {
    const session = await getAttendanceSession(sessionId);
    const records = await getSessionAttendanceRecords(sessionId);
    const joinedRecord = records.find((record) => record.student_id === sessionState.currentStudent?.id);

    document.getElementById("detailSubject").textContent = session.session_name || `Session ${session.id.substring(0, 8)}`;
    document.getElementById("detailInstructor").textContent = "Instructor";
    document.getElementById("detailDuration").textContent = session.start_time ? `${Math.max(0, Math.floor((new Date() - new Date(session.start_time)) / 60000))} min` : "-";
    document.getElementById("detailStartTime").textContent = session.start_time ? new Date(session.start_time).toLocaleTimeString() : "-";
    document.getElementById("detailActiveStudents").textContent = `${records.length} students`;
    document.getElementById("detailYourStatus").textContent = joinedRecord ? joinedRecord.attendance_status || "Pending" : "Not Joined";

    const statusEl = document.getElementById("detailYourStatus");
    if (statusEl) {
      statusEl.className = "detail-value status-badge " + (joinedRecord ? "status-active" : "status-pending");
    }

    const joinBtn = document.getElementById("joinSessionBtn");
    const markBtn = document.getElementById("markAttendanceBtn");
    if (joinBtn && markBtn) {
      if (joinedRecord) {
        joinBtn.style.display = "none";
        markBtn.style.display = "inline-block";
      } else {
        joinBtn.style.display = "inline-block";
        markBtn.style.display = "none";
      }
    }

    sessionState.selectedSession = session;
    detailsSection.style.display = "block";
    detailsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError("Failed to load session details: " + error.message);
  }
}

function closeSessionDetails() {
  const detailsSection = document.getElementById("sessionDetailsSection");
  if (detailsSection) {
    detailsSection.style.display = "none";
  }
}

function handleJoinSessionClick(sessionId, event) {
  if (event) event.stopPropagation();
  sessionState.selectedSession = { id: sessionId };
  handleJoinSession();
}

async function handleJoinSession() {
  if (!sessionState.selectedSession || !sessionState.selectedSession.id) {
    showError("No session selected.");
    return;
  }

  const user = getStoredUser();
  if (!user) {
    showError("User not found. Please log in again.");
    return;
  }

  try {
    await markAttendance(sessionState.selectedSession.id, user.id, "present");
    showSuccess("You have successfully joined the session!");
    await renderActiveSessions();
    await viewSessionDetails(sessionState.selectedSession.id, null);
  } catch (error) {
    showError("Failed to join session: " + error.message);
  }
}

async function handleMarkAttendance() {
  if (!sessionState.selectedSession || !sessionState.currentStudent) {
    showError("No session or student available.");
    return;
  }

  try {
    await markAttendance(sessionState.selectedSession.id, sessionState.currentStudent.id, "present");
    showSuccess("Attendance marked successfully.");
    await viewSessionDetails(sessionState.selectedSession.id, null);
  } catch (error) {
    showError("Failed to mark attendance: " + error.message);
  }
}

async function renderAttendanceHistory() {
  const tbody = document.getElementById("attendanceHistoryBody");
  if (!tbody) return;

  try {
    const sessions = await getAttendanceSessions();
    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">No attendance records available.</td></tr>';
      return;
    }

    tbody.innerHTML = sessions
      .map((session) => {
        const start = session.start_time ? new Date(session.start_time) : null;
        const status = session.status === "ended" ? "present" : "pending";
        return `
        <tr>
          <td>${session.session_name || `Session ${session.id.substring(0, 8)}`}</td>
          <td>${start ? start.toLocaleDateString() : "-"}</td>
          <td>${start ? start.toLocaleTimeString() : "-"}</td>
          <td>
            <span class="status-pill ${status}">${status === "present" ? "✓ Present" : "⏳ Active"}</span>
          </td>
        </tr>
      `;
      })
      .join("");
  } catch (error) {
    console.error(error);
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:red;">Failed to load attendance history.</td></tr>';
  }
}

const sidebar = document.querySelector(".sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const userMenuToggle = document.querySelector(".user-menu-toggle");
const userMenu = document.querySelector(".user-menu");

if (sidebarToggle) {
  sidebarToggle.addEventListener("click", toggleSidebar);
}

if (userMenuToggle) {
  userMenuToggle.addEventListener("click", toggleUserMenu);
}

document.addEventListener("click", function (event) {
  if (userMenu && userMenuToggle && !userMenu.contains(event.target) && !userMenuToggle.contains(event.target)) {
    userMenu.classList.remove("menu-open");
    userMenuToggle.setAttribute("aria-expanded", "false");
  }
});

function toggleSidebar() {
  if (!sidebar) return;

  if (window.innerWidth <= 1024) {
    sidebar.classList.toggle("sidebar-open");
    return;
  }

  sidebar.classList.toggle("sidebar-collapsed");
  document.body.classList.toggle("dashboard-sidebar-collapsed");
}

function toggleUserMenu() {
  if (!userMenu || !userMenuToggle) return;
  userMenu.classList.toggle("menu-open");
  userMenuToggle.setAttribute("aria-expanded", String(userMenu.classList.contains("menu-open")));
}

window.addEventListener("resize", function () {
  if (!sidebar) return;
  if (window.innerWidth > 1024) {
    sidebar.classList.remove("sidebar-open");
  }
});
