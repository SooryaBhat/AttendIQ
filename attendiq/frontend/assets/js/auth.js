const loginForm = document.getElementById("loginForm");
const statusMessage = document.getElementById("statusMessage");

const roleRedirectMap = {
  super_admin: "../super_admin/dashboard.html",
  dept_admin: "../dept_admin/dashboard.html",
  faculty: "../faculty/dashboard.html",
  student: "../student/dashboard.html",
};

function showMessage(message, type = "info") {
  statusMessage.textContent = message;
  statusMessage.style.color = type === "error" ? "#c21f3c" : "#0f4bb2";
}

async function handleLogin(event) {
  event.preventDefault();

  const role = loginForm.role.value;
  const email = loginForm.email.value.trim().toLowerCase();
  const password = loginForm.password.value;

  if (!role) {
    showMessage("Please select your role.", "error");
    return;
  }

  if (!email || !password) {
    showMessage("Email and password are required.", "error");
    return;
  }

  showMessage("Signing in…");

  try {
    const response = await loginUser({ email, password });

    if (!response || !response.access_token || !response.user) {
      throw new Error("Unexpected login response from server.");
    }

    saveAuthData(response.access_token, response.user);

    const redirectUrl = roleRedirectMap[response.user.role] || "../auth/login.html";
    showMessage("Login successful. Redirecting…", "success");

    setTimeout(() => {
      window.location.href = redirectUrl;
    }, 600);
  } catch (error) {
    const message = error?.payload?.detail || error?.message || "Login failed. Please try again.";
    showMessage(message, "error");
  }
}

if (loginForm) {
  loginForm.addEventListener("submit", handleLogin);
}

