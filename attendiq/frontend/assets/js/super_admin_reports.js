let charts = {};

function setReportMetric(id, value) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = value !== undefined && value !== null ? value : "—";
}

function renderTableRows(items) {
  const body = document.getElementById("departmentStatsBody");
  if (!body) return;

  if (!Array.isArray(items) || items.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center; color: #52637a;">No department data available.</td>
      </tr>
    `;
    return;
  }

  body.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>${item.department_name}</td>
          <td>${item.total_department_admins}</td>
          <td>${item.total_faculty}</td>
          <td>${item.total_students}</td>
          <td>${item.attendance_percent.toFixed(1)}%</td>
        </tr>
      `
    )
    .join("");
}

function getChartColors(count) {
  const palette = [
    "rgba(15, 75, 178, 0.85)",
    "rgba(24, 120, 199, 0.85)",
    "rgba(84, 161, 255, 0.85)",
    "rgba(98, 174, 228, 0.85)",
    "rgba(34, 105, 161, 0.85)",
    "rgba(59, 137, 197, 0.85)",
  ];
  return Array.from({ length: count }, (_, i) => palette[i % palette.length]);
}

function buildChart(canvasId, config) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }
  charts[canvasId] = new Chart(ctx, config);
  return charts[canvasId];
}

function renderStudentsByDepartment(payload) {
  if (!payload || !Array.isArray(payload.labels) || payload.labels.length === 0) return;
  buildChart("studentsByDeptChart", {
    type: "bar",
    data: {
      labels: payload.labels,
      datasets: [
        {
          label: "Students",
          data: payload.data,
          backgroundColor: getChartColors(payload.labels.length),
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { ticks: { maxRotation: 0, autoSkip: false } },
        y: { beginAtZero: true },
      },
    },
  });
}

function renderFacultyByDepartment(payload) {
  if (!payload || !Array.isArray(payload.labels) || payload.labels.length === 0) return;
  buildChart("facultyByDeptChart", {
    type: "bar",
    data: {
      labels: payload.labels,
      datasets: [
        {
          label: "Faculty",
          data: payload.data,
          backgroundColor: getChartColors(payload.labels.length),
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxRotation: 0, autoSkip: false } },
        y: { beginAtZero: true },
      },
    },
  });
}

function renderAttendanceByDepartment(payload) {
  if (!payload || !Array.isArray(payload.labels) || payload.labels.length === 0) return;
  buildChart("attendanceByDeptChart", {
    type: "line",
    data: {
      labels: payload.labels,
      datasets: [
        {
          label: "Attendance %",
          data: payload.data,
          borderColor: "#0f4bb2",
          backgroundColor: "rgba(15, 75, 178, 0.18)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100 },
      },
    },
  });
}

function renderDepartmentComparison(payload) {
  if (!Array.isArray(payload) || payload.length === 0) return;
  const labels = payload.map((item) => item.department_name);
  const students = payload.map((item) => item.total_students);
  const faculty = payload.map((item) => item.total_faculty);
  const admins = payload.map((item) => item.total_department_admins);

  buildChart("departmentComparisonChart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Students",
          data: students,
          backgroundColor: "rgba(15, 75, 178, 0.75)",
        },
        {
          label: "Faculty",
          data: faculty,
          backgroundColor: "rgba(24, 120, 199, 0.75)",
        },
        {
          label: "Admins",
          data: admins,
          backgroundColor: "rgba(84, 161, 255, 0.75)",
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { tooltip: { mode: "index", intersect: false } },
      scales: {
        x: { stacked: true, ticks: { maxRotation: 0, autoSkip: false } },
        y: { stacked: true, beginAtZero: true },
      },
    },
  });
}

async function loadSuperAdminReports() {
  try {
    const summary = await getAnalyticsSummary();
    setReportMetric("reportDepartments", summary.total_departments);
    setReportMetric("reportAdmins", summary.total_department_admins);
    setReportMetric("reportFaculty", summary.total_faculty);
    setReportMetric("reportStudents", summary.total_students);
    setReportMetric("reportSubjects", summary.total_subjects);
    setReportMetric("reportSessions", summary.attendance_sessions);
  } catch (error) {
    console.error("Unable to load report summary", error);
  }

  try {
    const studentsPayload = await getStudentsByDepartment();
    renderStudentsByDepartment(studentsPayload);
  } catch (error) {
    console.error("Unable to load students by department", error);
  }

  try {
    const facultyPayload = await getFacultyByDepartment();
    renderFacultyByDepartment(facultyPayload);
  } catch (error) {
    console.error("Unable to load faculty by department", error);
  }

  try {
    const attendancePayload = await getDepartmentComparison();
    renderAttendanceByDepartment(attendancePayload);
  } catch (error) {
    console.error("Unable to load attendance by department", error);
  }

  try {
    const departmentData = await getDepartmentStats();
    renderDepartmentComparison(departmentData);
    renderTableRows(departmentData);
  } catch (error) {
    console.error("Unable to load department stats", error);
  }
}

window.addEventListener("DOMContentLoaded", loadSuperAdminReports);
