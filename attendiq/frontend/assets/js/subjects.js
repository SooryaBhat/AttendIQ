let facultySubjects = [];
let studentSubjects = [];
let currentShareSubject = null;
let editingSubjectId = null;
let html5QrCode = null;
let qrScanning = false;
let facultyCurrentUser = null;

function renderFacultySubjects() {
  const list = document.getElementById("facultySubjectList");
  if (!list) return;

  if (!facultySubjects.length) {
    list.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:1rem; color:#64748b;">No subjects found for your account.</td></tr>';
    return;
  }

  list.innerHTML = facultySubjects
    .map(
      (subject) => `
      <tr data-subject-id="${subject.id}">
        <td>
          <strong>${escapeHtml(subject.name)}</strong>
          <div class="status-text">Semester ${escapeHtml(String(subject.semester))} · Section ${escapeHtml(subject.section || '—')}</div>
        </td>
        <td>${escapeHtml(subject.code)}</td>
        <td>${escapeHtml(String(subject.enrolled ?? 0))}</td>
        <td><span class="status-pill active">${escapeHtml(subject.status || 'Active')}</span></td>
        <td>
          <div class="action-buttons">
            <button type="button" class="action-button" data-action="view" data-id="${subject.id}">View</button>
            <button type="button" class="action-button" data-action="edit" data-id="${subject.id}">Edit</button>
            <button type="button" class="action-button alert" data-action="delete" data-id="${subject.id}">Delete</button>
            <button type="button" class="action-button" data-action="qr" data-id="${subject.id}">QR</button>
            <button type="button" class="action-button positive" data-action="share" data-id="${subject.id}">Share</button>
          </div>
        </td>
      </tr>
    `
    )
    .join("");

  list.querySelectorAll("button[data-action]").forEach((button) => {
    const action = button.dataset.action;
    const id = button.dataset.id;
    button.addEventListener("click", () => handleSubjectTableAction(action, id));
  });
}

function renderStudentSubjects() {
  const list = document.getElementById("studentSubjectList");
  if (!list) return;

  if (!studentSubjects.length) {
    list.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem; color:#64748b;">No enrolled subjects found.</td></tr>';
    return;
  }

  list.innerHTML = studentSubjects
    .map(
      (subject) => `
      <tr>
        <td>${escapeHtml(subject.name)}</td>
        <td>${escapeHtml(subject.code)}</td>
        <td>${escapeHtml(subject.instructor || 'Faculty')}</td>
        <td><span class="status-pill active">${escapeHtml(subject.progress || 'Enrolled')}</span></td>
      </tr>
    `
    )
    .join("");
}

function makeJoinLink(code) {
  const origin = window.location.protocol.startsWith("http")
    ? window.location.origin
    : "https://securely-masculine-elliptic.ngrok-free.dev";
  return `${origin}/join/${encodeURIComponent(code)}`;
}

function clearCreateForm() {
  editingSubjectId = null;
  document.getElementById("subjectName").value = "";
  document.getElementById("subjectCode").value = "";
  document.getElementById("subjectSemester").value = "";
  document.getElementById("subjectSection").value = "";
  document.getElementById("subjectDescription").value = "";
  const statusMessage = document.getElementById("subjectFormStatus");
  if (statusMessage) {
    statusMessage.textContent = "Create a new subject record and share access with students.";
    statusMessage.style.color = "#52637a";
  }
}

async function submitSubjectForm(event) {
  event.preventDefault();
  const nameInput = document.getElementById("subjectName");
  const codeInput = document.getElementById("subjectCode");
  const semesterInput = document.getElementById("subjectSemester");
  const sectionInput = document.getElementById("subjectSection");
  const descriptionInput = document.getElementById("subjectDescription");
  const statusMessage = document.getElementById("subjectFormStatus");

  const name = nameInput.value.trim();
  const code = codeInput.value.trim().toUpperCase();
  const semester = semesterInput.value.trim();
  const section = sectionInput.value.trim();
  const description = descriptionInput.value.trim();

  if (!name || !code || !semester || !section) {
    if (statusMessage) {
      statusMessage.textContent = "All fields except description are required.";
      statusMessage.style.color = "#c21f3c";
    }
    return;
  }

  if (!facultyCurrentUser) {
    if (statusMessage) {
      statusMessage.textContent = "Unable to resolve faculty account.";
      statusMessage.style.color = "#c21f3c";
    }
    return;
  }

  const payload = {
    name,
    code,
    faculty_id: facultyCurrentUser.id,
    department_id: facultyCurrentUser.department_id,
    semester: parseInt(semester, 10),
    credits: 3,
  };

  try {
    if (editingSubjectId) {
      const updated = await updateSubject(editingSubjectId, payload);
      const index = facultySubjects.findIndex((item) => item.id === editingSubjectId);
      if (index !== -1) {
        facultySubjects[index] = { ...facultySubjects[index], ...updated };
      }
      if (statusMessage) {
        statusMessage.textContent = "Subject updated successfully.";
        statusMessage.style.color = "#14a44d";
      }
    } else {
      const created = await createSubject(payload);
      facultySubjects.unshift(created);
      if (statusMessage) {
        statusMessage.textContent = "Subject created successfully.";
        statusMessage.style.color = "#14a44d";
      }
    }

    renderFacultySubjects();
    clearCreateForm();
  } catch (err) {
    console.error(err);
    if (statusMessage) {
      statusMessage.textContent = err.message || 'Unable to save subject.';
      statusMessage.style.color = '#c21f3c';
    }
  }
}

function handleSubjectTableAction(action, subjectId) {
  const subject = facultySubjects.find((item) => item.id === subjectId);
  if (!subject) return;

  switch (action) {
    case "view":
      viewSubject(subject);
      break;
    case "edit":
      editSubject(subject);
      break;
    case "delete":
      removeSubject(subject);
      break;
    case "qr":
      openShareDialog(subjectId);
      break;
    case "share":
      openShareDialog(subjectId);
      break;
    default:
      break;
  }
}

function viewSubject(subject) {
  window.alert(`Subject:\n${subject.name}\n\nCode: ${subject.code}\nSemester: ${subject.semester}\nSection: ${subject.section}\nStudents Enrolled: ${subject.enrolled ?? 0}\n\nDescription:\n${subject.description || 'No description provided.'}`);
}

function editSubject(subject) {
  editingSubjectId = subject.id;
  document.getElementById("subjectName").value = subject.name;
  document.getElementById("subjectCode").value = subject.code;
  document.getElementById("subjectSemester").value = subject.semester;
  document.getElementById("subjectSection").value = subject.section;
  document.getElementById("subjectDescription").value = subject.description || "";
  const statusMessage = document.getElementById("subjectFormStatus");
  if (statusMessage) {
    statusMessage.textContent = "Editing subject. Make updates and click Save subject.";
    statusMessage.style.color = "#0f4bb2";
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function removeSubject(subject) {
  if (!window.confirm(`Delete subject ${subject.name}? This action cannot be undone.`)) {
    return;
  }

  deleteSubject(subject.id)
    .then(() => {
      facultySubjects = facultySubjects.filter((item) => item.id !== subject.id);
      renderFacultySubjects();
    })
    .catch((err) => {
      console.error(err);
      window.alert(err.message || 'Unable to delete subject.');
    });
}

function openShareDialog(subjectId) {
  const subject = facultySubjects.find((item) => item.id === subjectId);
  if (!subject) return;

  currentShareSubject = subject;
  document.getElementById("shareSubjectName").value = subject.name;
  document.getElementById("shareSubjectCode").value = subject.code;
  document.getElementById("shareJoinLink").value = subject.joinLink || makeJoinLink(subject.code);

  const qrContainer = document.getElementById("shareQrCode");
  qrContainer.innerHTML = "";
  new QRCode(qrContainer, {
    text: document.getElementById("shareJoinLink").value,
    width: 200,
    height: 200,
    colorDark: "#102a43",
    colorLight: "#ffffff",
  });

  document.getElementById("shareDialogOverlay").classList.add("open");
}

function closeShareDialog() {
  const overlay = document.getElementById("shareDialogOverlay");
  if (!overlay) return;
  overlay.classList.remove("open");
  const qrContainer = document.getElementById("shareQrCode");
  if (qrContainer) qrContainer.innerHTML = "";
}

function copyToClipboard(value, messageTargetId) {
  const messageTarget = document.getElementById(messageTargetId);
  if (!value) return;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(value)
      .then(() => {
        if (messageTarget) {
          messageTarget.textContent = "Copied to clipboard.";
        }
      })
      .catch(() => fallbackCopyText(value, messageTarget));
  } else {
    fallbackCopyText(value, messageTarget);
  }
}

function fallbackCopyText(value, messageTarget) {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
    if (messageTarget) {
      messageTarget.textContent = "Copied to clipboard.";
    }
  } finally {
    document.body.removeChild(textarea);
  }
}

function downloadQrCode() {
  const qrContainer = document.getElementById("shareQrCode");
  if (!qrContainer) return;
  const img = qrContainer.querySelector("img");
  const canvas = qrContainer.querySelector("canvas");
  const source = img || canvas;
  if (!source) return;

  const dataUrl = source.tagName === "IMG" ? source.src : source.toDataURL("image/png");
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = `${currentShareSubject ? currentShareSubject.code : "subject"}-qr.png`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function shareSubject() {
  const subject = currentShareSubject;
  if (!subject) return;

  const text = `Subject: ${subject.name}\nCode: ${subject.code}\nLink: ${subject.joinLink || makeJoinLink(subject.code)}`;
  const url = subject.joinLink || makeJoinLink(subject.code);

  if (navigator.share) {
    navigator
      .share({
        title: subject.name,
        text,
        url,
      })
      .catch(() => {
        copyToClipboard(url, "shareStatus");
      });
  } else {
    copyToClipboard(url, "shareStatus");
  }
}

function addStudentSubject(subject) {
  if (!studentSubjects.some((item) => item.code === subject.code)) {
    studentSubjects.unshift({
      id: `STU-${Date.now()}`,
      name: subject.name,
      code: subject.code,
      instructor: "Faculty Team",
      progress: "Joined",
    });
  }
  renderStudentSubjects();
}

async function loadFacultySubjects(user) {
  facultyCurrentUser = user;
  try {
    const subjects = await getSubjects();
    facultySubjects = Array.isArray(subjects) ? subjects.filter((subject) => subject.faculty_id === user.id) : [];
    renderFacultySubjects();
  } catch (error) {
    console.error('Unable to load faculty subjects', error);
  }
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

