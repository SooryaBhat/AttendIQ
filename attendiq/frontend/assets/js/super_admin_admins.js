let editingAdminId = null;
const departmentMap = new Map();

const adminForm = document.getElementById("adminForm");
const adminNameInput = document.getElementById("adminName");
const adminEmailInput = document.getElementById("adminEmail");
const adminDepartmentSelect = document.getElementById("adminDepartment");
const adminPhoneInput = document.getElementById("adminPhone");
const adminPasswordInput = document.getElementById("adminPassword");
const adminActiveInput = document.getElementById("adminActive");
const adminSubmitButton = document.getElementById("adminSubmitButton");
const adminStatusMessage = document.getElementById("adminStatusMessage");
const adminsTableBody = document.getElementById("adminsTableBody");

function showAdminMessage(message, type = "info") {
  if (!adminStatusMessage) return;
  adminStatusMessage.textContent = message;
  adminStatusMessage.style.color = type === "error" ? "#c21f3c" : "#14a44d";
}

function resetAdminForm() {
  editingAdminId = null;
  if (adminNameInput) adminNameInput.value = "";
  if (adminEmailInput) adminEmailInput.value = "";
  if (adminDepartmentSelect) adminDepartmentSelect.value = "";
  if (adminPhoneInput) adminPhoneInput.value = "";
  if (adminPasswordInput) adminPasswordInput.value = "";
  if (adminActiveInput) adminActiveInput.checked = true;
  if (adminSubmitButton) adminSubmitButton.textContent = "Create admin";
  showAdminMessage("Ready to add a new department admin.");
}

function renderDepartmentOptions(departments) {
  if (!adminDepartmentSelect) return;
  departmentMap.clear();
  adminDepartmentSelect.innerHTML = `<option value="">Select department</option>`;
  departments.forEach((department) => {
    departmentMap.set(department.id, `${department.name} (${department.code})`);
    const option = document.createElement("option");
    option.value = department.id;
    option.textContent = `${department.name} (${department.code})`;
    adminDepartmentSelect.appendChild(option);
  });
}

function renderAdmins(admins) {
  if (!adminsTableBody) return;
  if (admins.length === 0) {
    adminsTableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; color: #52637a;">No department admins found.</td>
      </tr>
    `;
    return;
  }

  adminsTableBody.innerHTML = admins
    .map(
      (admin) => `
        <tr>
          <td>${admin.full_name}</td>
          <td>${admin.email}</td>
          <td>${departmentMap.get(admin.department_id) || admin.department_id || "—"}</td>
          <td>${admin.phone || "—"}</td>
          <td>${admin.is_active ? "Active" : "Inactive"}</td>
          <td>
            <div class="table-actions">
              <button class="action-btn" type="button" onclick="editAdmin('${admin.id}')">Edit</button>
              <button class="action-btn" type="button" onclick="toggleAdminStatus('${admin.id}', ${admin.is_active})">${admin.is_active ? "Deactivate" : "Activate"}</button>
              <button class="action-btn alert" type="button" onclick="deleteAdmin('${admin.id}')">Delete</button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");
}

async function loadDepartmentsForAdmins() {
  try {
    const departments = await getDepartments();
    renderDepartmentOptions(departments || []);
  } catch (error) {
    console.error("Unable to load departments", error);
    showAdminMessage("Unable to load departments.", "error");
  }
}

async function loadAdmins() {
  try {
    const admins = await getDepartmentAdmins();
    renderAdmins(admins || []);
  } catch (error) {
    console.error("Unable to load department admins", error);
    showAdminMessage("Unable to load department admins.", "error");
  }
}

async function handleAdminSubmit(event) {
  event.preventDefault();

  const name = adminNameInput?.value.trim();
  const email = adminEmailInput?.value.trim();
  const departmentId = adminDepartmentSelect?.value;
  const phone = adminPhoneInput?.value.trim();
  const password = adminPasswordInput?.value;
  const isActive = adminActiveInput?.checked;

  if (!name || !email || !departmentId) {
    showAdminMessage("Name, email, and department are required.", "error");
    return;
  }

  const payload = {
    full_name: name,
    email,
    role: "department_admin",
    department_id: departmentId,
    phone: phone || null,
  };

  if (editingAdminId) {
    payload.is_active = isActive;
    if (password) {
      payload.password = password;
    }
  } else {
    if (!password) {
      showAdminMessage("Password is required when creating a new admin.", "error");
      return;
    }
    payload.password = password;
  }

  try {
    if (editingAdminId) {
      await updateDepartmentAdmin(editingAdminId, payload);
      showAdminMessage("Department admin updated successfully.");
    } else {
      await createDepartmentAdmin(payload);
      showAdminMessage("Department admin created successfully.");
    }
    resetAdminForm();
    loadAdmins();
  } catch (error) {
    console.error(error);
    showAdminMessage(error?.payload?.detail || error?.message || "Failed to save department admin.", "error");
  }
}

window.editAdmin = async function (adminId) {
  try {
    const admin = await getDepartmentAdminById(adminId);
    editingAdminId = admin.id;
    adminNameInput.value = admin.full_name;
    adminEmailInput.value = admin.email;
    adminDepartmentSelect.value = admin.department_id || "";
    adminPhoneInput.value = admin.phone || "";
    adminPasswordInput.value = "";
    adminActiveInput.checked = admin.is_active;
    adminSubmitButton.textContent = "Update admin";
    showAdminMessage("Edit mode enabled. Update the fields and save.");
  } catch (error) {
    console.error(error);
    showAdminMessage("Unable to load admin details.", "error");
  }
};

window.toggleAdminStatus = async function (adminId, currentStatus) {
  const action = currentStatus ? "deactivate" : "activate";
  if (!window.confirm(`Are you sure you want to ${action} this admin?`)) return;

  try {
    if (currentStatus) {
      await deactivateDepartmentAdmin(adminId);
      showAdminMessage("Department admin deactivated.");
    } else {
      await activateDepartmentAdmin(adminId);
      showAdminMessage("Department admin activated.");
    }
    loadAdmins();
  } catch (error) {
    console.error(error);
    showAdminMessage(error?.payload?.detail || error?.message || "Unable to update admin status.", "error");
  }
};

window.deleteAdmin = async function (adminId) {
  if (!window.confirm("Delete this department admin? This action cannot be undone.")) return;

  try {
    await deleteDepartmentAdmin(adminId);
    showAdminMessage("Department admin deleted successfully.");
    loadAdmins();
  } catch (error) {
    console.error(error);
    showAdminMessage(error?.payload?.detail || error?.message || "Unable to delete admin.", "error");
  }
};

window.addEventListener("DOMContentLoaded", async () => {
  if (adminForm) {
    adminForm.addEventListener("submit", handleAdminSubmit);
  }
  const resetButton = document.getElementById("adminResetButton");
  if (resetButton) {
    resetButton.addEventListener("click", (event) => {
      event.preventDefault();
      resetAdminForm();
    });
  }

  await loadDepartmentsForAdmins();
  await loadAdmins();
});
