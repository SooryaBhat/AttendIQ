/*
  Faculty attendance page script using real backend data.
*/

document.addEventListener("DOMContentLoaded", function () {
  if (!window.location.pathname.toLowerCase().includes("faculty/attendance.html")) return;
  initFacultyAttendancePage();
});

async function initFacultyAttendancePage() {
  const banner = getBanner("attendanceBanner");
  const user = await ensureAuthenticated(banner);
  if (!user) return;

  renderUserMenu(user);
  bindAttendancePageEvents();
  await loadSubjectOptions();
  await refreshAttendancePage();
}

function getBanner(id) {
  const element = document.getElementById(id);
  if (!element) return null;
  return {
    element,
    icon: element.querySelector(".status-icon"),
    text: element.querySelector("span[id$='Text']") || element.querySelector("span:last-child"),
  };
}

function showBanner(banner, type, icon, message) {
  if (!banner || !banner.element) return;
  banner.element.className = `status-banner show ${type}`;
  if (banner.icon) banner.icon.textContent = icon;
  if (banner.text) banner.textContent = message;
}

function hideBanner(banner) {
  if (!banner || !banner.element) return;
  banner.element.className = "status-banner";
}

async function ensureAuthenticated(banner) {
  const token = localStorage.getItem("attendiq_token");
  if (!token) {
    window.location.href = "../auth/login.html";
    return null;
  }

  try {
    const user = await fetchCurrentUser();
    localStorage.setItem("attendiq_user", JSON.stringify(user));
    if (!user || !["faculty", "super_admin", "department_admin"].includes(user.role)) {
      showBanner(banner, "error", "⚠️", "Faculty access required.");
      return null;
    }
    return user;
  } catch (error) {
    localStorage.removeItem("attendiq_token");
    localStorage.removeItem("attendiq_user");
    window.location.href = "../auth/login.html";
    return null;
  }
}

function renderUserMenu(user) {
  const toggle = document.querySelector(".user-menu-toggle");
  if (!toggle) return;
  const name = toggle.querySelector("strong");
  const role = toggle.querySelector("small");
  if (name) name.textContent = user.full_name || "Faculty";
  if (role) role.textContent = "Instructor";
}

function bindAttendancePageEvents() {
  const subjectSelect = document.getElementById("subjectSelect");
  const startSessionBtn = document.getElementById("startSessionBtn");
  const endSessionBtn = document.getElementById("endSessionBtn");

  if (subjectSelect) {
    subjectSelect.addEventListener("change", () => {
      if (startSessionBtn) startSessionBtn.disabled = !subjectSelect.value;
    });
  }

  if (startSessionBtn) {
    startSessionBtn.addEventListener("click", async () => {
      const user = JSON.parse(localStorage.getItem("attendiq_user"));
      if (!user) return;
      await handleStartSession(user);
    });
  }

  if (endSessionBtn) {
    endSessionBtn.addEventListener("click", async () => {
      await handleEndSession();
    });
  }
}

async function loadSubjectOptions() {
  const subjectSelect = document.getElementById("subjectSelect");
  const startSessionBtn = document.getElementById("startSessionBtn");

  if (!subjectSelect) return;

  try {
    const subjects = await getSubjects();
    if (!subjects || subjects.length === 0) {
      subjectSelect.innerHTML = '<option value="">No subjects available</option>';
      if (startSessionBtn) startSessionBtn.disabled = true;
      return;
    }

    subjectSelect.innerHTML = ['<option value="">— Select a subject —</option>']
      .concat(subjects.map((subject) => `<option value="${subject.id}">${escapeHtml(`${subject.name} (${subject.code})`)}</option>`))
      .join("");
    if (startSessionBtn) startSessionBtn.disabled = true;
  } catch (error) {
    subjectSelect.innerHTML = '<option value="">Unable to load subjects</option>';
    if (startSessionBtn) startSessionBtn.disabled = true;
  }
}

async function refreshAttendancePage() {
  const banner = getBanner("attendanceBanner");

  try {
    showBanner(banner, "info", "⏳", "Loading subjects and sessions...");
    const [subjects, sessions] = await Promise.all([getSubjects(), getAttendanceSessions()]);
    const subjectMap = subjects.reduce((map, subject) => {
      map[subject.id] = subject;
      return map;
    }, {});

    renderSessionHistory(sessions, subjectMap);
    await renderActiveSessionInfo(sessions, subjectMap);
    hideBanner(banner);
  } catch (error) {
    showBanner(banner, "error", "❌", error.message || "Unable to load attendance data.");
  }
}

async function handleStartSession(user) {
  const subjectSelect = document.getElementById("subjectSelect");
  const banner = getBanner("attendanceBanner");
  if (!subjectSelect || !subjectSelect.value) return;

  try {
    showBanner(banner, "info", "⏳", "Creating attendance session...");
    const payload = {
      subject_id: subjectSelect.value,
      faculty_id: user.id,
      department_id: user.department_id,
      session_label: `Session ${new Date().toLocaleTimeString()}`,
      session_date: new Date().toISOString().split("T")[0],
      method: "face",
    };
    const created = await createAttendanceSession(payload);
    await startAttendanceSession(created.id);
    await refreshAttendancePage();
    showBanner(banner, "success", "✅", "Session started successfully.");
    subjectSelect.value = "";
  } catch (error) {
    showBanner(banner, "error", "❌", error.message || "Unable to start session.");
  }
}

async function handleEndSession() {
  const banner = getBanner("attendanceBanner");
  const active = await getCurrentActiveSession();
  if (!active) {
    showBanner(banner, "warning", "⚠️", "No active session to end.");
    return;
  }

  if (!confirm("End the current attendance session?")) return;

  try {
    await endAttendanceSession(active.id);
    await refreshAttendancePage();
    showBanner(banner, "success", "✅", "Session ended successfully.");
  } catch (error) {
    showBanner(banner, "error", "❌", error.message || "Unable to end session.");
  }
}

async function getCurrentActiveSession() {
  const sessions = await getAttendanceSessions();
  return sessions.find((session) => session.status === "processing") || null;
}

function renderSessionHistory(sessions, subjectMap) {
  const body = document.getElementById("sessionsHistoryBody");
  if (!body) return;

  if (!sessions || sessions.length === 0) {
    body.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:#64748b;">No sessions yet.</td></tr>';
    return;
  }

  body.innerHTML = sessions
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .map((session) => {
      const subject = subjectMap[session.subject_id];
      const subjectLabel = subject ? `${subject.name} (${subject.code})` : "Unknown";
      const dateText = session.session_date ? formatDate(session.session_date) : formatDate(session.created_at);
      const actions = [];
      if (session.status === "pending") {
        actions.push(`<button class="action-btn" data-action="start" data-id="${session.id}">▶ Start</button>`);
      }
      if (session.status === "processing") {
        actions.push(`<button class="action-btn" data-action="end" data-id="${session.id}">⏹ End</button>`);
      }
      actions.push(`<button class="action-btn action-danger" data-action="delete" data-id="${session.id}">🗑 Delete</button>`);

      return `
        <tr data-session-id="${session.id}" data-status="${session.status}">
          <td>${escapeHtml(subjectLabel)}</td>
          <td>${escapeHtml(session.session_label)}</td>
          <td>${escapeHtml(dateText)}</td>
          <td>${escapeHtml(session.status)}</td>
          <td>${session.attendance_count || 0}</td>
          <td>${actions.join(" ")}</td>
        </tr>`;
    })
    .join("");

  body.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const { action, id } = button.dataset;
      if (action === "start") {
        await startAttendanceSession(id);
      }
      if (action === "end") {
        await endAttendanceSession(id);
      }
      if (action === "delete") {
        if (!confirm("Delete this session? This will remove its records.")) return;
        await deleteAttendanceSession(id);
      }
      await refreshAttendancePage();
    });
  });
}

async function renderActiveSessionInfo(sessions, subjectMap) {
  const activeSession = sessions.find((session) => session.status === "processing");
  const activeSection = document.getElementById("sessionActive");
  const activeSubject = document.getElementById("activeSubject");
  const statusBadge = document.getElementById("sessionStatus");
  const timerDisplay = document.getElementById("sessionTimer");
  const activeStudentsCount = document.getElementById("activeStudentsCount");
  const markedPresentCount = document.getElementById("markedPresentCount");
  const absentCount = document.getElementById("absentCount");
  const studentsBody = document.getElementById("studentsTableBody");

  if (!activeSession) {
    if (activeSection) activeSection.style.display = "none";
    if (studentsBody) studentsBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:2rem; color:#64748b;">No active session in progress.</td></tr>';
    return;
  }

  if (activeSection) activeSection.style.display = "block";
  if (activeSubject) activeSubject.textContent = subjectMap[activeSession.subject_id]?.name || "Unknown";
  if (statusBadge) {
    statusBadge.textContent = "Active";
    statusBadge.className = "status-badge status-active";
  }
  if (timerDisplay) timerDisplay.textContent = activeSession.started_at ? getSessionDuration(activeSession.started_at) : "00:00:00";

  const records = await getSessionAttendanceRecords(activeSession.id);
  const present = records.filter((record) => record.status === "present").length;
  const absent = records.filter((record) => record.status === "absent").length;

  if (activeStudentsCount) activeStudentsCount.textContent = `${records.length}`;
  if (markedPresentCount) markedPresentCount.textContent = `${present}`;
  if (absentCount) absentCount.textContent = `${absent}`;

  if (!studentsBody) return;
  if (!records || records.length === 0) {
    studentsBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:2rem; color:#64748b;">No attendance records yet.</td></tr>';
    return;
  }

  studentsBody.innerHTML = records
    .map((record) => {
      const statusClass = record.status === "present" ? "present" : record.status === "absent" ? "absent" : "pending";
      return `
        <tr>
          <td>${escapeHtml(record.student_id.substring(0, 8))}</td>
          <td>${escapeHtml(record.student_id.substring(0, 8))}</td>
          <td>${record.marked_at ? escapeHtml(new Date(record.marked_at).toLocaleTimeString()) : "-"}</td>
          <td><span class="status-pill ${statusClass}">${escapeHtml(capitalize(record.status))}</span></td>
          <td><button class="action-btn" onclick="markStudentAttendance('${record.student_id}', 'present')">✓</button></td>
        </tr>`;
    })
    .join("");
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function capitalize(value) {
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function getSessionDuration(startedAt) {
  const started = new Date(startedAt).getTime();
  if (Number.isNaN(started)) return "00:00:00";
  const diff = Math.max(Date.now() - started, 0);
  const seconds = Math.floor(diff / 1000);
  const hours = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const secs = String(seconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
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
