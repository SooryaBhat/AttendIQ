const facultySearchInput = document.getElementById("facultySearchInput");
const facultyFilterDepartment = document.getElementById("facultyFilterDepartment");
const facultySearchButton = document.getElementById("facultySearchButton");
const facultyClearButton = document.getElementById("facultyClearButton");
const facultyTableBody = document.getElementById("facultyTableBody");
const facultyForm = document.getElementById("facultyForm");
const facultyFormTitle = document.getElementById("facultyFormTitle");
const facultyNameInput = document.getElementById("facultyNameInput");
const facultyEmailInput = document.getElementById("facultyEmailInput");
const facultyPhoneInput = document.getElementById("facultyPhoneInput");
const facultyDepartmentSelect = document.getElementById("facultyDepartmentSelect");
const facultyPasswordInput = document.getElementById("facultyPasswordInput");
const facultyActiveInput = document.getElementById("facultyActiveInput");
const facultyResetButton = document.getElementById("facultyResetButton");

let editingFacultyId = null;
let facultyDepartments = [];

async function loadFacultyDepartments() {
  try {
    facultyDepartments = await getDepartments();
    renderFacultyDepartmentOptions();
  } catch (error) {
    console.error("Unable to load departments", error);
  }
}

function renderFacultyDepartmentOptions() {
  facultyFilterDepartment.innerHTML = "<option value=\"\">All departments</option>";
  facultyDepartmentSelect.innerHTML = "<option value=\"\">Select department</option>";

  facultyDepartments.forEach((department) => {
    const option = document.createElement("option");
    option.value = department.id;
    option.textContent = department.name;
    facultyFilterDepartment.appendChild(option);

    const formOption = document.createElement("option");
    formOption.value = department.id;
    formOption.textContent = department.name;
    facultyDepartmentSelect.appendChild(formOption);
  });
}

async function loadFaculty() {
  const search = facultySearchInput.value.trim();
  const departmentId = facultyFilterDepartment.value || undefined;

  try {
    const facultyList = await getFaculties(search, departmentId);
    renderFacultyTable(facultyList);
  } catch (error) {
    console.error("Unable to fetch faculty", error);
  }
}

function renderFacultyTable(facultyList) {
  facultyTableBody.innerHTML = "";

  if (!facultyList.length) {
    const row = document.createElement("tr");
    row.innerHTML = "<td colspan=\"7\">No faculty found.</td>";
    facultyTableBody.appendChild(row);
    return;
  }

  facultyList.forEach((member) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${member.full_name}</td>
      <td>${member.email}</td>
      <td>${member.phone || "-"}</td>
      <td>${getFacultyDepartmentName(member.department_id) || "-"}</td>
      <td>${member.is_active ? "Active" : "Inactive"}</td>
      <td>
        <button class="btn btn-small btn-secondary" data-action="edit" data-id="${member.id}">Edit</button>
        <button class="btn btn-small btn-danger" data-action="delete" data-id="${member.id}">Delete</button>
      </td>
    `;

    row.querySelector("button[data-action=edit]").addEventListener("click", () => {
      editFaculty(member.id);
    });
    row.querySelector("button[data-action=delete]").addEventListener("click", () => {
      deleteFacultyRecord(member.id);
    });

    facultyTableBody.appendChild(row);
  });
}

function getFacultyDepartmentName(departmentId) {
  const department = facultyDepartments.find((item) => item.id === departmentId);
  return department ? department.name : "";
}

async function editFaculty(facultyId) {
  try {
    const member = await getFacultyById(facultyId);
    editingFacultyId = facultyId;
    facultyFormTitle.textContent = "Update faculty";
    facultyNameInput.value = member.full_name;
    facultyEmailInput.value = member.email;
    facultyPhoneInput.value = member.phone || "";
    facultyDepartmentSelect.value = member.department_id || "";
    facultyActiveInput.checked = member.is_active;
    facultyPasswordInput.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    console.error("Unable to load faculty details", error);
  }
}

async function deleteFacultyRecord(facultyId) {
  if (!confirm("Delete this faculty member? This action cannot be undone.")) {
    return;
  }

  try {
    await deleteFaculty(facultyId);
    await loadFaculty();
  } catch (error) {
    console.error("Unable to delete faculty", error);
  }
}

function resetFacultyForm() {
  editingFacultyId = null;
  facultyFormTitle.textContent = "Add new faculty";
  facultyForm.reset();
  facultyDepartmentSelect.value = "";
}

facultyForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    full_name: facultyNameInput.value.trim(),
    email: facultyEmailInput.value.trim(),
    phone: facultyPhoneInput.value.trim() || null,
    department_id: facultyDepartmentSelect.value || null,
    password: facultyPasswordInput.value.trim() || null,
    is_active: facultyActiveInput.checked,
  };

  try {
    if (editingFacultyId) {
      await updateFaculty(editingFacultyId, payload);
    } else {
      await createFaculty(payload);
    }
    resetFacultyForm();
    await loadFaculty();
  } catch (error) {
    console.error("Unable to save faculty", error);
  }
});

facultySearchButton.addEventListener("click", async () => {
  await loadFaculty();
});

facultyClearButton.addEventListener("click", () => {
  facultySearchInput.value = "";
  facultyFilterDepartment.value = "";
  loadFaculty();
});

facultyResetButton.addEventListener("click", resetFacultyForm);

window.addEventListener("DOMContentLoaded", async () => {
  await loadFacultyDepartments();
  await loadFaculty();
});
