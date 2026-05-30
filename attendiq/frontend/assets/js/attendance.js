/*
  Attendance Session Module for AttendIQ
  Handles faculty and student attendance functionality
*/

// Dummy Data
const dummySubjects = [
  { id: "CS-301", name: "Advanced Algorithms", code: "CS-301", instructor: "Dr. Smith" },
  { id: "CS-302", name: "Database Systems", code: "CS-302", instructor: "Prof. Johnson" },
  { id: "CS-303", name: "Web Development", code: "CS-303", instructor: "Dr. Williams" },
  { id: "CS-304", name: "Machine Learning", code: "CS-304", instructor: "Prof. Brown" },
];

const dummyStudents = [
  { id: 1, rollNo: "CS001", name: "Alice Johnson", joinTime: "10:05 AM" },
  { id: 2, rollNo: "CS002", name: "Bob Smith", joinTime: "10:08 AM" },
  { id: 3, rollNo: "CS003", name: "Carol Davis", joinTime: "10:10 AM" },
  { id: 4, rollNo: "CS004", name: "David Wilson", joinTime: "10:03 AM" },
  { id: 5, rollNo: "CS005", name: "Emma Brown", joinTime: "10:12 AM" },
  { id: 6, rollNo: "CS006", name: "Frank Miller", joinTime: "10:07 AM" },
];

const dummySessionHistory = [
  {
    subject: "Advanced Algorithms",
    date: "2026-05-28",
    duration: "45 min",
    totalStudents: 35,
    present: 34,
    absent: 1,
  },
  {
    subject: "Database Systems",
    date: "2026-05-27",
    duration: "50 min",
    totalStudents: 32,
    present: 31,
    absent: 1,
  },
  {
    subject: "Web Development",
    date: "2026-05-26",
    duration: "48 min",
    totalStudents: 40,
    present: 38,
    absent: 2,
  },
];

const dummyAttendanceHistory = [
  { subject: "Advanced Algorithms", date: "2026-05-28", time: "10:15 AM", status: "present" },
  { subject: "Database Systems", date: "2026-05-27", time: "09:45 AM", status: "present" },
  { subject: "Web Development", date: "2026-05-26", time: "02:30 PM", status: "present" },
  { subject: "Machine Learning", date: "2026-05-25", time: "11:20 AM", status: "absent" },
];

// Global State
let sessionState = {
  isActive: false,
  selectedSubject: null,
  startTime: null,
  elapsedSeconds: 0,
  activeStudents: [],
  attendanceRecords: {},
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
}

function initializePage() {
  // Determine which page we're on based on file path or page content
  const path = window.location.pathname.toLowerCase();

  if (path.includes("faculty/attendance")) {
    initializeFacultyAttendance();
  } else if (path.includes("student/attendance")) {
    initializeStudentAttendance();
  }
}

// ============================================================================
// FACULTY ATTENDANCE MODULE
// ============================================================================

function initializeFacultyAttendance() {
  // Initialize session history table
  renderSessionsHistory();

  // Simulate active sessions from previous attempts
  const hasActiveSession = sessionStorage.getItem("hasActiveSession");
  if (hasActiveSession === "true") {
    const savedSubject = sessionStorage.getItem("activeSubject");
    if (savedSubject) {
      showSessionActive(savedSubject);
      sessionState.elapsedSeconds = parseInt(sessionStorage.getItem("elapsedSeconds") || "0");
      startSessionTimer();
      // Simulate student activity
      simulateStudentActivity();
    }
  }
}

function handleSubjectChange(event) {
  const startSessionBtn = document.getElementById("startSessionBtn");
  startSessionBtn.disabled = !event.target.value;
}

function startSession() {
  const subjectSelect = document.getElementById("subjectSelect");
  const selectedValue = subjectSelect.value;

  if (!selectedValue) return;

  const subject = dummySubjects.find((s) => s.id === selectedValue);
  if (!subject) return;

  // Update global state
  sessionState.isActive = true;
  sessionState.selectedSubject = subject;
  sessionState.startTime = new Date();
  sessionState.elapsedSeconds = 0;
  sessionState.activeStudents = [...dummyStudents];
  sessionState.attendanceRecords = {};

  // Initialize attendance records
  dummyStudents.forEach((student) => {
    sessionState.attendanceRecords[student.id] = "pending";
  });

  // Save to session storage
  sessionStorage.setItem("hasActiveSession", "true");
  sessionStorage.setItem("activeSubject", JSON.stringify(subject));

  // Update UI
  showSessionActive(subject);
  renderStudentsTable();
  startSessionTimer();
  simulateStudentActivity();

  // Disable subject select during session
  subjectSelect.disabled = true;
}

function endSession() {
  const confirmed = confirm("Are you sure you want to end this attendance session?");
  if (!confirmed) return;

  // Stop timer
  if (sessionTimerInterval) {
    clearInterval(sessionTimerInterval);
  }

  // Update state
  sessionState.isActive = false;
  sessionState.startTime = null;

  // Clear session storage
  sessionStorage.removeItem("hasActiveSession");
  sessionStorage.removeItem("activeSubject");
  sessionStorage.removeItem("elapsedSeconds");

  // Hide active session UI
  const sessionActive = document.getElementById("sessionActive");
  const studentsListSection = document.getElementById("studentsListSection");
  const subjectSelect = document.getElementById("subjectSelect");

  if (sessionActive) sessionActive.style.display = "none";
  if (studentsListSection) studentsListSection.style.display = "none";
  if (subjectSelect) {
    subjectSelect.disabled = false;
    subjectSelect.value = "";
  }

  const startSessionBtn = document.getElementById("startSessionBtn");
  if (startSessionBtn) startSessionBtn.disabled = true;

  // Add to history
  addToSessionHistory();

  alert("Attendance session ended successfully!");
}

function showSessionActive(subject) {
  const sessionActive = document.getElementById("sessionActive");
  const activeSubject = document.getElementById("activeSubject");
  const studentsListSection = document.getElementById("studentsListSection");

  if (sessionActive) {
    sessionActive.style.display = "block";
    if (activeSubject) {
      activeSubject.textContent = `${subject.name} (${subject.code})`;
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

    // Save elapsed time every 5 seconds
    if (sessionState.elapsedSeconds % 5 === 0) {
      sessionStorage.setItem("elapsedSeconds", sessionState.elapsedSeconds);
    }
  }, 1000);
}

function updateTimerDisplay() {
  const sessionTimer = document.getElementById("sessionTimer");
  if (!sessionTimer) return;

  const hours = Math.floor(sessionState.elapsedSeconds / 3600);
  const minutes = Math.floor((sessionState.elapsedSeconds % 3600) / 60);
  const seconds = sessionState.elapsedSeconds % 60;

  sessionTimer.textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(
    2,
    "0"
  )}:${String(seconds).padStart(2, "0")}`;
}

function renderStudentsTable() {
  const tbody = document.getElementById("studentsTableBody");
  if (!tbody) return;

  tbody.innerHTML = sessionState.activeStudents.map((student) => {
    const status = sessionState.attendanceRecords[student.id] || "pending";
    const statusClass = status === "present" ? "present" : status === "absent" ? "absent" : "pending";

    return `
      <tr>
        <td>${student.rollNo}</td>
        <td>${student.name}</td>
        <td>${student.joinTime}</td>
        <td><span class="status-pill ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span></td>
        <td>
          <div class="table-actions">
            <button class="action-btn mark-present" onclick="markStudentAttendance(${student.id}, 'present')">✓</button>
            <button class="action-btn mark-absent" onclick="markStudentAttendance(${student.id}, 'absent')">✗</button>
          </div>
        </td>
      </tr>
    `;
  });

  // Update counts
  const presentCount = sessionState.activeStudents.filter(
    (s) => sessionState.attendanceRecords[s.id] === "present"
  ).length;
  const absentCount = sessionState.activeStudents.filter(
    (s) => sessionState.attendanceRecords[s.id] === "absent"
  ).length;

  const activeStudentsCount = document.getElementById("activeStudentsCount");
  const markedPresentCount = document.getElementById("markedPresentCount");
  const absentCountEl = document.getElementById("absentCount");

  if (activeStudentsCount) activeStudentsCount.textContent = sessionState.activeStudents.length;
  if (markedPresentCount) markedPresentCount.textContent = presentCount;
  if (absentCountEl) absentCountEl.textContent = absentCount;
}

function markStudentAttendance(studentId, status) {
  sessionState.attendanceRecords[studentId] = status;
  renderStudentsTable();
}

function simulateStudentActivity() {
  // Randomly add/update student attendance over time
  if (!sessionState.isActive) return;

  // Randomly mark some students as present or absent
  const randomStudent = sessionState.activeStudents[Math.floor(Math.random() * sessionState.activeStudents.length)];
  const randomStatus = Math.random() > 0.3 ? "present" : "absent";

  if (sessionState.attendanceRecords[randomStudent.id] === "pending") {
    sessionState.attendanceRecords[randomStudent.id] = randomStatus;
    renderStudentsTable();
  }

  // Schedule next simulation in 3-8 seconds
  setTimeout(simulateStudentActivity, 3000 + Math.random() * 5000);
}

function renderSessionsHistory() {
  const tbody = document.getElementById("sessionsHistoryBody");
  if (!tbody) return;

  tbody.innerHTML = dummySessionHistory
    .map(
      (session) => `
    <tr>
      <td>${session.subject}</td>
      <td>${new Date(session.date).toLocaleDateString()}</td>
      <td>${session.duration}</td>
      <td>${session.totalStudents}</td>
      <td><span class="status-pill present">${session.present}</span></td>
      <td><span class="status-pill absent">${session.absent}</span></td>
    </tr>
  `
    )
    .join("");
}

function addToSessionHistory() {
  const subject = sessionState.selectedSubject;
  if (!subject) return;

  const duration = Math.floor(sessionState.elapsedSeconds / 60);
  const totalStudents = sessionState.activeStudents.length;
  const presentCount = sessionState.activeStudents.filter(
    (s) => sessionState.attendanceRecords[s.id] === "present"
  ).length;
  const absentCount = totalStudents - presentCount;

  const newSession = {
    subject: subject.name,
    date: new Date().toISOString().split("T")[0],
    duration: `${duration} min`,
    totalStudents,
    present: presentCount,
    absent: absentCount,
  };

  dummySessionHistory.unshift(newSession);
  renderSessionsHistory();
}

// ============================================================================
// STUDENT ATTENDANCE MODULE
// ============================================================================

function initializeStudentAttendance() {
  renderActiveSessions();
  renderAttendanceHistory();
}

function renderActiveSessions() {
  const container = document.getElementById("activeSessionsContainer");
  const noSessionsMessage = document.getElementById("noSessionsMessage");

  if (!container) return;

  // Show 2-3 active sessions
  const activeSessions = [
    {
      id: "S001",
      subject: "Advanced Algorithms",
      code: "CS-301",
      instructor: "Dr. Smith",
      startTime: "10:00 AM",
      activeStudents: 28,
      status: "active",
      joined: false,
    },
    {
      id: "S002",
      subject: "Web Development",
      code: "CS-303",
      instructor: "Dr. Williams",
      startTime: "02:00 PM",
      activeStudents: 35,
      status: "active",
      joined: false,
    },
  ];

  if (activeSessions.length === 0 && noSessionsMessage) {
    noSessionsMessage.style.display = "grid";
    container.innerHTML = "";
    return;
  }

  if (noSessionsMessage) {
    noSessionsMessage.style.display = "none";
  }

  container.innerHTML = activeSessions
    .map(
      (session) => `
    <div class="session-card" onclick="viewSessionDetails('${session.id}', this)">
      <div class="session-card-header">
        <div class="session-card-title">
          <h3>${session.subject}</h3>
          <span class="subject-code">${session.code}</span>
        </div>
        <div class="session-card-badge">
          🔴 Live
        </div>
      </div>

      <div class="session-card-info">
        <div class="session-card-info-item">
          <span class="session-card-info-label">Instructor</span>
          <span class="session-card-info-value">${session.instructor}</span>
        </div>
        <div class="session-card-info-item">
          <span class="session-card-info-label">Started</span>
          <span class="session-card-info-value">${session.startTime}</span>
        </div>
        <div class="session-card-info-item">
          <span class="session-card-info-label">Active Students</span>
          <span class="session-card-info-value">${session.activeStudents}</span>
        </div>
      </div>

      <div class="session-card-footer">
        <button class="session-card-btn primary" onclick="joinSession('${session.id}', event)">
          👋 Join Session
        </button>
        <button class="session-card-btn" onclick="viewSessionDetails('${session.id}', this.closest('.session-card'), event)">
          ℹ️ Details
        </button>
      </div>
    </div>
  `
    )
    .join("");
}

function viewSessionDetails(sessionId, cardElement, event) {
  if (event) {
    event.stopPropagation();
  }

  const detailsSection = document.getElementById("sessionDetailsSection");
  if (!detailsSection) return;

  const sessionData = {
    S001: {
      subject: "Advanced Algorithms",
      instructor: "Dr. Smith",
      duration: "45 minutes",
      startTime: "10:00 AM",
      activeStudents: "28 students",
      status: "Joined",
    },
    S002: {
      subject: "Web Development",
      instructor: "Dr. Williams",
      duration: "50 minutes",
      startTime: "02:00 PM",
      activeStudents: "35 students",
      status: "Not Joined",
    },
  };

  const data = sessionData[sessionId] || sessionData["S001"];

  document.getElementById("detailSubject").textContent = data.subject;
  document.getElementById("detailInstructor").textContent = data.instructor;
  document.getElementById("detailDuration").textContent = data.duration;
  document.getElementById("detailStartTime").textContent = data.startTime;
  document.getElementById("detailActiveStudents").textContent = data.activeStudents;

  const statusEl = document.getElementById("detailYourStatus");
  if (statusEl) {
    statusEl.textContent = data.status;
    statusEl.className = "detail-value status-badge " + (data.status === "Joined" ? "status-active" : "status-pending");
  }

  const joinBtn = document.getElementById("joinSessionBtn");
  const markBtn = document.getElementById("markAttendanceBtn");

  if (joinBtn && markBtn) {
    if (data.status === "Joined") {
      joinBtn.style.display = "none";
      markBtn.style.display = "inline-block";
    } else {
      joinBtn.style.display = "inline-block";
      markBtn.style.display = "none";
    }
  }

  detailsSection.style.display = "block";
  detailsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeSessionDetails() {
  const detailsSection = document.getElementById("sessionDetailsSection");
  if (detailsSection) {
    detailsSection.style.display = "none";
  }
}

function joinSession(sessionId, event) {
  if (event) {
    event.stopPropagation();
  }

  const confirmed = confirm("Join this attendance session?");
  if (confirmed) {
    alert("✓ You have successfully joined the session!");
    // Update session data
    viewSessionDetails(sessionId);
  }
}

function renderAttendanceHistory() {
  const tbody = document.getElementById("attendanceHistoryBody");
  if (!tbody) return;

  tbody.innerHTML = dummyAttendanceHistory
    .map(
      (record) => `
    <tr>
      <td>${record.subject}</td>
      <td>${new Date(record.date).toLocaleDateString()}</td>
      <td>${record.time}</td>
      <td>
        <span class="status-pill ${record.status}">
          ${record.status === "present" ? "✓ Present" : "✗ Absent"}
        </span>
      </td>
    </tr>
  `
    )
    .join("");
}

// Dashboard integration - ensure sidebar/topbar work
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
