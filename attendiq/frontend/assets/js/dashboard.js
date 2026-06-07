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
const topbarActions = document.querySelector(".topbar-actions");
const userMenuToggle = document.querySelector(".user-menu-toggle");
const userMenu = document.querySelector(".user-menu");
const notificationButton = document.querySelector(".notification-button");
const logoutLinks = document.querySelectorAll("a[href*='#logout'], a[href*='#signout'], .logout-link, button.logout-button");
const userNameElement = document.querySelector(".user-menu-toggle strong");
const userSubtextElement = document.querySelector(".user-menu-toggle small");
let sidebarBackdrop = null;

function toggleSidebar() {
  if (!sidebar) return;

  if (window.innerWidth <= 1024) {
    sidebar.classList.toggle("sidebar-open");
    updateBackdropState();
    return;
  }

  sidebar.classList.toggle("sidebar-collapsed");
  document.body.classList.toggle("dashboard-sidebar-collapsed");
}

function closeSidebarOnResize() {
  if (!sidebar) return;
  if (window.innerWidth > 1024) {
    sidebar.classList.remove("sidebar-open");
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.remove("visible");
    }
  }
}

function toggleUserMenu() {
  if (!userMenu || !userMenuToggle) return;
  userMenu.classList.toggle("menu-open");
  userMenuToggle.setAttribute("aria-expanded", String(userMenu.classList.contains("menu-open")));
}

function stripUnusedSettingsLinks() {
  document.querySelectorAll("a[href='#settings']").forEach((link) => link.remove());
}

function closeUserMenu(event) {
  if (!userMenu || !userMenuToggle) return;
  if (userMenu.contains(event.target) || userMenuToggle.contains(event.target)) {
    return;
  }
  userMenu.classList.remove("menu-open");
  userMenuToggle.setAttribute("aria-expanded", "false");
}

function createSidebarBackdrop() {
  if (!sidebar || sidebarBackdrop) return;
  sidebarBackdrop = document.createElement("div");
  sidebarBackdrop.className = "sidebar-backdrop";
  document.body.appendChild(sidebarBackdrop);
  sidebarBackdrop.addEventListener("click", () => {
    sidebar.classList.remove("sidebar-open");
    sidebarBackdrop.classList.remove("visible");
  });
}

function injectSidebarLogout() {
  if (!sidebar) return;
  const footer = sidebar.querySelector(".sidebar-footer");
  if (!footer || footer.querySelector("button.logout-button")) return;

  const logoutBtn = document.createElement("button");
  logoutBtn.type = "button";
  logoutBtn.className = "logout-button";
  logoutBtn.textContent = "Logout";
  logoutBtn.title = "Sign out";
  const referenceNode = footer.querySelector(".sidebar-toggle");
  footer.insertBefore(logoutBtn, referenceNode ? referenceNode.nextSibling : null);
  logoutBtn.addEventListener("click", logout);
}

function updateBackdropState() {
  if (!sidebar || !sidebarBackdrop) return;
  if (sidebar.classList.contains("sidebar-open")) {
    sidebarBackdrop.classList.add("visible");
  } else {
    sidebarBackdrop.classList.remove("visible");
  }
}

function ensureMobileSidebarButton() {
  if (!sidebar || !topbarActions) return;

  let mobileButton = document.getElementById("mobileMenuButton");
  if (!mobileButton) {
    mobileButton = document.createElement("button");
    mobileButton.id = "mobileMenuButton";
    mobileButton.type = "button";
    mobileButton.className = "sidebar-open-button";
    mobileButton.setAttribute("aria-label", "Open navigation");
    mobileButton.innerHTML = "☰";
    topbarActions.prepend(mobileButton);
  }

  mobileButton.addEventListener("click", () => {
    toggleSidebar();
    updateBackdropState();
  });
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

  ensureMobileSidebarButton();
  createSidebarBackdrop();
  injectSidebarLogout();
  stripUnusedSettingsLinks();

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
