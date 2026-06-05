async function loadSuperAdminDashboard() {
  try {
    const summary = await getSuperAdminSummary();
    document.getElementById("cardTotalDepartments").textContent = summary.total_departments ?? "—";
    document.getElementById("cardDepartmentAdmins").textContent = summary.total_department_admins ?? "—";
    document.getElementById("cardTotalFaculty").textContent = summary.total_faculty ?? "—";
    document.getElementById("cardTotalStudents").textContent = summary.total_students ?? "—";
    document.getElementById("cardTotalSubjects").textContent = summary.total_subjects ?? "—";
    document.getElementById("cardAttendanceSessions").textContent = summary.total_attendance_sessions ?? "—";
  } catch (error) {
    console.error("Unable to load dashboard summary", error);
  }
}

window.addEventListener("DOMContentLoaded", loadSuperAdminDashboard);
