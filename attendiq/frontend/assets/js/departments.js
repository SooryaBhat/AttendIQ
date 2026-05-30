let editingDepartmentId = null;

const departmentsForm = document.getElementById("departmentsForm");
const deptNameInput = document.getElementById("departmentName");
const deptCodeInput = document.getElementById("departmentCode");
const deptDescriptionInput = document.getElementById("departmentDescription");
const deptSubmitButton = document.getElementById("departmentSubmitButton");
const deptStatusMessage = document.getElementById("departmentStatusMessage");
const departmentsTableBody = document.getElementById("departmentsTableBody");

function showDepartmentMessage(message, type = "info") {
  if (!deptStatusMessage) return;
  deptStatusMessage.textContent = message;
  deptStatusMessage.style.color = type === "error" ? "#c21f3c" : "#14a44d";
}

function resetDepartmentForm() {
  editingDepartmentId = null;
  if (deptNameInput) deptNameInput.value = "";
  if (deptCodeInput) deptCodeInput.value = "";
  if (deptDescriptionInput) deptDescriptionInput.value = "";
  if (deptSubmitButton) deptSubmitButton.textContent = "Create department";
  showDepartmentMessage("Ready to create a new department.");
}

async function loadDepartments() {
  try {
    const departments = await getDepartments();
    renderDepartments(departments || []);
  } catch (error) {
    showDepartmentMessage(error?.payload?.detail || error?.message || "Unable to load departments.", "error");
  }
}

function renderDepartments(departments) {
  if (!departmentsTableBody) return;

  if (departments.length === 0) {
    departmentsTableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align:center; color: #52637a;">No departments available yet.</td>
      </tr>
    `;
    return;
  }

  departmentsTableBody.innerHTML = departments
    .map(
      (department) => `
        <tr>
          <td>${department.name}</td>
          <td>${department.code}</td>
          <td>${department.description || "—"}</td>
          <td>
            <div class="table-actions">
              <button class="action-btn" type="button" onclick="editDepartment('${department.id}')">Edit</button>
              <button class="action-btn alert" type="button" onclick="deleteDepartment('${department.id}')">Delete</button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");
}

async function handleDepartmentSubmit(event) {
  event.preventDefault();

  const name = deptNameInput?.value.trim();
  const code = deptCodeInput?.value.trim().toUpperCase();
  const description = deptDescriptionInput?.value.trim();

  if (!name || !code) {
    showDepartmentMessage("Name and code are required.", "error");
    return;
  }

  try {
    if (editingDepartmentId) {
      await updateDepartment(editingDepartmentId, { name, code, description });
      showDepartmentMessage("Department updated successfully.");
    } else {
      await createDepartment({ name, code, description });
      showDepartmentMessage("Department created successfully.");
    }

    resetDepartmentForm();
    loadDepartments();
  } catch (error) {
    showDepartmentMessage(error?.payload?.detail || error?.message || "Failed to save department.", "error");
  }
}

window.editDepartment = function (departmentId) {
  fetchDepartment(departmentId);
};

async function fetchDepartment(departmentId) {
  try {
    const department = await getDepartment(departmentId);
    editingDepartmentId = department.id;
    if (deptNameInput) deptNameInput.value = department.name;
    if (deptCodeInput) deptCodeInput.value = department.code;
    if (deptDescriptionInput) deptDescriptionInput.value = department.description || "";
    if (deptSubmitButton) deptSubmitButton.textContent = "Update department";
    showDepartmentMessage("Edit mode enabled. Save changes or reset the form.");
  } catch (error) {
    showDepartmentMessage(error?.payload?.detail || error?.message || "Unable to load department.", "error");
  }
}

async function deleteDepartment(departmentId) {
  if (!window.confirm("Delete this department? This action cannot be undone.")) {
    return;
  }

  try {
    await deleteDepartmentById(departmentId);
    loadDepartments();
    showDepartmentMessage("Department deleted successfully.");
  } catch (error) {
    showDepartmentMessage(error?.payload?.detail || error?.message || "Unable to delete department.", "error");
  }
}

async function deleteDepartmentById(departmentId) {
  return request(`/departments/${departmentId}`, { method: "DELETE" });
}

async function getDepartment(departmentId) {
  return request(`/departments/${departmentId}`);
}

function initDepartmentManagement() {
  if (departmentsForm) {
    departmentsForm.addEventListener("submit", handleDepartmentSubmit);
  }

  const resetButton = document.getElementById("departmentResetButton");
  if (resetButton) {
    resetButton.addEventListener("click", (event) => {
      event.preventDefault();
      resetDepartmentForm();
    });
  }

  loadDepartments();
}

window.addEventListener("DOMContentLoaded", initDepartmentManagement);
