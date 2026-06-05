let studentsByDeptChart = null;

function setReportMetric(id, value) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = value !== undefined && value !== null ? value : "—";
}

function renderDepartmentStatsTable(items) {
  const body = document.getElementById("departmentStatsBody");
  if (!body) return;
  if (!Array.isArray(items) || items.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="4" style="text-align:center; color: #52637a;">No departments available.</td>
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
          <td>${item.total_students}</td>
          <td>${item.total_faculty}</td>
        </tr>
      `
    )
    .join("");
}

function renderStudentsByDeptChart(items) {
  const ctx = document.getElementById("studentsByDeptChart");
  if (!ctx) return;

  const labels = items.map((item) => item.department_name);
  const data = items.map((item) => item.total_students);

  if (studentsByDeptChart) {
    studentsByDeptChart.destroy();
  }

  studentsByDeptChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Students",
          data,
          backgroundColor: "rgba(15, 75, 178, 0.75)",
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}

async function loadSuperAdminReports() {
  try {
    const summary = await getSuperAdminSummary();
    setReportMetric("reportDepartments", summary.total_departments);
    setReportMetric("reportAdmins", summary.total_department_admins);
    setReportMetric("reportFaculty", summary.total_faculty);
    setReportMetric("reportStudents", summary.total_students);
    setReportMetric("reportSubjects", summary.total_subjects);
    setReportMetric("reportSessions", summary.total_attendance_sessions);
  } catch (error) {
    console.error("Unable to load report summary", error);
  }

  try {
    const departmentStats = await getSuperAdminDepartmentStats();
    renderDepartmentStatsTable(departmentStats || []);
    renderStudentsByDeptChart(departmentStats || []);
  } catch (error) {
    console.error("Unable to load department statistics", error);
  }
}

window.addEventListener("DOMContentLoaded", loadSuperAdminReports);
