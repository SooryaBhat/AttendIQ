/*
  Dashboard layout script for AttendIQ.
  Expected markup structure:
  - .app-shell
  - .sidebar
  - #sidebarToggle
  - .topbar
  - .user-menu-toggle
  - .user-menu
  - .notification-button
*/

const sidebar = document.querySelector(".sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const userMenuToggle = document.querySelector(".user-menu-toggle");
const userMenu = document.querySelector(".user-menu");
const notificationButton = document.querySelector(".notification-button");
const logoutLinks = document.querySelectorAll("a[href='#logout'], a[href='#signout'], .logout-link");
const userNameElement = document.querySelector(".user-menu-toggle strong");
const userSubtextElement = document.querySelector(".user-menu-toggle small");

function toggleSidebar() {
  if (!sidebar) return;

  if (window.innerWidth <= 1024) {
    sidebar.classList.toggle("sidebar-open");
    return;
  }

  sidebar.classList.toggle("sidebar-collapsed");
  document.body.classList.toggle("dashboard-sidebar-collapsed");
}

function closeSidebarOnResize() {
  if (!sidebar) return;
  if (window.innerWidth > 1024) {
    sidebar.classList.remove("sidebar-open");
  }
}

function toggleUserMenu() {
  if (!userMenu || !userMenuToggle) return;
  userMenu.classList.toggle("menu-open");
  userMenuToggle.setAttribute("aria-expanded", String(userMenu.classList.contains("menu-open")));
}

function closeUserMenu(event) {
  if (!userMenu || !userMenuToggle) return;
  if (userMenu.contains(event.target) || userMenuToggle.contains(event.target)) {
    return;
  }
  userMenu.classList.remove("menu-open");
  userMenuToggle.setAttribute("aria-expanded", "false");
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("attendiq_user")) || null;
  } catch (error) {
    return null;
  }
}

function applyUserContext() {
  const storedUser = getStoredUser();
  if (!storedUser) return;

  if (userNameElement) {
    userNameElement.textContent = storedUser.full_name || storedUser.role || "User";
  }

  if (userSubtextElement) {
    userSubtextElement.textContent = storedUser.role ? storedUser.role.replace(/_/g, " ") : "Logged in";
  }
}

function logout(event) {
  if (event) {
    event.preventDefault();
  }

  localStorage.removeItem("attendiq_user");
  localStorage.removeItem("attendiq_token");
  const loginUrl = new URL("../auth/login.html", window.location.href).toString();
  window.location.href = loginUrl;
}

function initDashboardLayout() {
  applyUserContext();

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", toggleSidebar);
  }

  if (userMenuToggle) {
    userMenuToggle.addEventListener("click", toggleUserMenu);
  }

  document.addEventListener("click", closeUserMenu);
  window.addEventListener("resize", closeSidebarOnResize);

  if (notificationButton) {
    notificationButton.addEventListener("click", () => {
      window.alert("You have no new notifications in this demo layout.");
    });
  }

  logoutLinks.forEach((link) => {
    link.addEventListener("click", logout);
  });
}

window.addEventListener("DOMContentLoaded", initDashboardLayout);
