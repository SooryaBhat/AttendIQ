const searchInput = document.getElementById("searchInput");
const filterDepartment = document.getElementById("filterDepartment");
const searchButton = document.getElementById("searchButton");
const clearButton = document.getElementById("clearButton");
const studentsTableBody = document.getElementById("studentsTableBody");
const studentsForm = document.getElementById("studentsForm");
const formTitle = document.getElementById("formTitle");
const fullNameInput = document.getElementById("fullNameInput");
const rollNumberInput = document.getElementById("rollNumberInput");
const emailInput = document.getElementById("emailInput");
const phoneInput = document.getElementById("phoneInput");
const departmentSelect = document.getElementById("departmentSelect");
const faceEnrolledInput = document.getElementById("faceEnrolledInput");
const voiceEnrolledInput = document.getElementById("voiceEnrolledInput");
const resetButton = document.getElementById("resetButton");

let editingStudentId = null;
let departments = [];

async function loadDepartments() {
  try {
    departments = await getDepartments();
    renderDepartmentOptions();
  } catch (error) {
    console.error("Unable to load departments", error);
  }
}

function renderDepartmentOptions() {
  filterDepartment.innerHTML = "<option value=\"\">All departments</option>";
  departmentSelect.innerHTML = "<option value=\"\">Select department</option>";

  departments.forEach((department) => {
    const option = document.createElement("option");
    option.value = department.id;
    option.textContent = department.name;
    filterDepartment.appendChild(option);

    const formOption = document.createElement("option");
    formOption.value = department.id;
    formOption.textContent = department.name;
    departmentSelect.appendChild(formOption);
  });
}

async function loadStudents() {
  const search = searchInput.value.trim();
  const departmentId = filterDepartment.value || undefined;

  try {
    const students = await getStudents(search, departmentId);
    renderStudentTable(students);
  } catch (error) {
    console.error("Unable to fetch students", error);
  }
}

function renderStudentTable(students) {
  studentsTableBody.innerHTML = "";

  if (!students.length) {
    const row = document.createElement("tr");
    row.innerHTML = "<td colspan=\"8\">No students found.</td>";
    studentsTableBody.appendChild(row);
    return;
  }

  students.forEach((student) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${student.full_name}</td>
      <td>${student.roll_number}</td>
      <td>${student.email}</td>
      <td>${student.phone || "-"}</td>
      <td>${getDepartmentName(student.department_id) || "-"}</td>
      <td>${student.face_enrolled ? "Yes" : "No"}</td>
      <td>${student.voice_enrolled ? "Yes" : "No"}</td>
      <td>
        <button class="btn btn-small btn-secondary" data-action="edit" data-id="${student.id}">Edit</button>
        <button class="btn btn-small btn-danger" data-action="delete" data-id="${student.id}">Delete</button>
      </td>
    `;

    row.querySelector("button[data-action=edit]").addEventListener("click", () => {
      editStudent(student.id);
    });
    row.querySelector("button[data-action=delete]").addEventListener("click", () => {
      deleteStudentRecord(student.id);
    });

    studentsTableBody.appendChild(row);
  });
}

function getDepartmentName(departmentId) {
  const department = departments.find((item) => item.id === departmentId);
  return department ? department.name : "";
}

async function editStudent(studentId) {
  try {
    const student = await getStudentById(studentId);
    editingStudentId = studentId;
    formTitle.textContent = "Update student";
    fullNameInput.value = student.full_name;
    rollNumberInput.value = student.roll_number;
    emailInput.value = student.email;
    phoneInput.value = student.phone || "";
    departmentSelect.value = student.department_id || "";
    faceEnrolledInput.checked = student.face_enrolled;
    voiceEnrolledInput.checked = student.voice_enrolled;
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    console.error("Unable to load student details", error);
  }
}

async function deleteStudentRecord(studentId) {
  if (!confirm("Delete this student? This action cannot be undone.")) {
    return;
  }

  try {
    await deleteStudent(studentId);
    await loadStudents();
  } catch (error) {
    console.error("Unable to delete student", error);
  }
}

function resetForm() {
  editingStudentId = null;
  formTitle.textContent = "Add new student";
  studentsForm.reset();
  departmentSelect.value = "";
}

studentsForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    full_name: fullNameInput.value.trim(),
    roll_number: rollNumberInput.value.trim(),
    email: emailInput.value.trim(),
    phone: phoneInput.value.trim() || null,
    department_id: departmentSelect.value || null,
    face_enrolled: faceEnrolledInput.checked,
    voice_enrolled: voiceEnrolledInput.checked,
  };

  try {
    if (editingStudentId) {
      await updateStudent(editingStudentId, payload);
    } else {
      await createStudent(payload);
    }
    resetForm();
    await loadStudents();
  } catch (error) {
    console.error("Unable to save student", error);
  }
});

searchButton.addEventListener("click", async () => {
  await loadStudents();
});

clearButton.addEventListener("click", () => {
  searchInput.value = "";
  filterDepartment.value = "";
  loadStudents();
});

resetButton.addEventListener("click", resetForm);

window.addEventListener("DOMContentLoaded", async () => {
  await loadDepartments();
  await loadStudents();
});
