const facultySubjects = [
  {
    id: "SUBJ-AI01",
    name: "Artificial Intelligence Fundamentals",
    code: "AI-2026",
    semester: "Spring 2026",
    section: "A1",
    enrolled: 82,
    description: "Introductory AI concepts and algorithms.",
    joinLink: "https://attendiq.local/join/AI-2026",
    status: "Active",
  },
  {
    id: "SUBJ-NET02",
    name: "Computer Networks",
    code: "NET-2026",
    semester: "Spring 2026",
    section: "B2",
    enrolled: 64,
    description: "Network design, protocols, and campus infrastructure.",
    joinLink: "https://attendiq.local/join/NET-2026",
    status: "Active",
  },
  {
    id: "SUBJ-DB03",
    name: "Database Systems",
    code: "DB-2026",
    semester: "Fall 2026",
    section: "C3",
    enrolled: 57,
    description: "Relational databases, SQL, and data modeling.",
    joinLink: "https://attendiq.local/join/DB-2026",
    status: "Active",
  },
];

const studentSubjects = [
  {
    id: "STU-AI01",
    name: "Artificial Intelligence Fundamentals",
    code: "AI-2026",
    instructor: "Dr. Priya Rao",
    progress: "Joined",
  },
  {
    id: "STU-DB03",
    name: "Database Systems",
    code: "DB-2026",
    instructor: "Prof. Arun Singh",
    progress: "Joined",
  },
];

let currentShareSubject = null;
let editingSubjectId = null;
let html5QrCode = null;
let qrScanning = false;

function renderFacultySubjects() {
  const list = document.getElementById("facultySubjectList");
  if (!list) return;

  list.innerHTML = facultySubjects
    .map(
      (subject) => `
      <tr data-subject-id="${subject.id}">
        <td>
          <strong>${subject.name}</strong>
          <div class="status-text">${subject.semester} · Section ${subject.section}</div>
        </td>
        <td>${subject.code}</td>
        <td>${subject.enrolled}</td>
        <td><span class="status-pill active">${subject.status}</span></td>
        <td>
          <div class="action-buttons">
            <button type="button" class="action-button" data-action="view" data-id="${subject.id}">View</button>
            <button type="button" class="action-button" data-action="edit" data-id="${subject.id}">Edit</button>
            <button type="button" class="action-button alert" data-action="delete" data-id="${subject.id}">Delete</button>
            <button type="button" class="action-button" data-action="qr" data-id="${subject.id}">Generate QR</button>
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

  list.innerHTML = studentSubjects
    .map(
      (subject) => `
      <tr>
        <td>${subject.name}</td>
        <td>${subject.code}</td>
        <td>${subject.instructor}</td>
        <td><span class="status-pill active">${subject.progress}</span></td>
      </tr>
    `
    )
    .join("");
}

function makeJoinLink(code) {
  return `https://attendiq.local/join/${encodeURIComponent(code)}`;
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

function createSubject(event) {
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

  if (editingSubjectId) {
    const subject = facultySubjects.find((item) => item.id === editingSubjectId);
    if (subject) {
      subject.name = name;
      subject.code = code;
      subject.semester = semester;
      subject.section = section;
      subject.description = description;
      subject.joinLink = makeJoinLink(subject.code);
      if (statusMessage) {
        statusMessage.textContent = "Subject updated successfully.";
        statusMessage.style.color = "#14a44d";
      }
    }
  } else {
    facultySubjects.unshift({
      id: `SUBJ-${Date.now()}`,
      name,
      code,
      semester,
      section,
      enrolled: 0,
      description,
      joinLink: makeJoinLink(code),
      status: "Active",
    });
    if (statusMessage) {
      statusMessage.textContent = "Subject created successfully.";
      statusMessage.style.color = "#14a44d";
    }
  }

  renderFacultySubjects();
  clearCreateForm();
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
      deleteSubject(subject);
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
  window.alert(`Subject:\n${subject.name}\n\nCode: ${subject.code}\nSemester: ${subject.semester}\nSection: ${subject.section}\nStudents Enrolled: ${subject.enrolled}\n\nDescription:\n${subject.description}`);
}

function editSubject(subject) {
  editingSubjectId = subject.id;
  document.getElementById("subjectName").value = subject.name;
  document.getElementById("subjectCode").value = subject.code;
  document.getElementById("subjectSemester").value = subject.semester;
  document.getElementById("subjectSection").value = subject.section;
  document.getElementById("subjectDescription").value = subject.description;
  const statusMessage = document.getElementById("subjectFormStatus");
  if (statusMessage) {
    statusMessage.textContent = "Editing subject. Make updates and click Save subject.";
    statusMessage.style.color = "#0f4bb2";
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function deleteSubject(subject) {
  if (!window.confirm(`Delete subject ${subject.name}? This action cannot be undone.`)) {
    return;
  }
  const index = facultySubjects.findIndex((item) => item.id === subject.id);
  if (index !== -1) {
    facultySubjects.splice(index, 1);
    renderFacultySubjects();
  }
}

function openShareDialog(subjectId) {
  const subject = facultySubjects.find((item) => item.id === subjectId);
  if (!subject) return;

  currentShareSubject = subject;
  document.getElementById("shareSubjectName").value = subject.name;
  document.getElementById("shareSubjectCode").value = subject.code;
  document.getElementById("shareJoinLink").value = subject.joinLink;

  const qrContainer = document.getElementById("shareQrCode");
  qrContainer.innerHTML = "";
  new QRCode(qrContainer, {
    text: subject.joinLink,
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

  const text = `Subject: ${subject.name}\nCode: ${subject.code}\nLink: ${subject.joinLink}`;
  const url = subject.joinLink;

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

function joinByCode(event) {
  event.preventDefault();
  const input = document.getElementById("joinSubjectCode");
  const status = document.getElementById("studentJoinStatus");
  const code = input.value.trim().toUpperCase();

  if (!code) {
    status.textContent = "Enter a valid subject code.";
    status.style.color = "#c21f3c";
    return;
  }

  const subject = facultySubjects.find((item) => item.code === code);
  if (!subject) {
    status.textContent = "Subject code not recognized.";
    status.style.color = "#c21f3c";
    return;
  }

  addStudentSubject(subject);
  status.textContent = `Joined ${subject.name}.`;
  status.style.color = "#14a44d";
  input.value = "";
}

function joinByLink(event) {
  event.preventDefault();
  const input = document.getElementById("joinSubjectLink");
  const status = document.getElementById("studentJoinStatus");
  const value = input.value.trim();

  if (!value) {
    status.textContent = "Enter a valid join link.";
    status.style.color = "#c21f3c";
    return;
  }

  const match = value.match(/join\/([^\/\s]+)/i);
  if (!match) {
    status.textContent = "Unable to parse the join link.";
    status.style.color = "#c21f3c";
    return;
  }

  const code = match[1].toUpperCase();
  const subject = facultySubjects.find((item) => item.code === code);
  if (!subject) {
    status.textContent = "Join link is invalid or expired.";
    status.style.color = "#c21f3c";
    return;
  }

  addStudentSubject(subject);
  status.textContent = `Joined ${subject.name} via join link.`;
  status.style.color = "#14a44d";
  input.value = "";
}

function scanSuccess(decodedText) {
  const status = document.getElementById("qrScanStatus");
  if (!decodedText) return;

  const match = decodedText.match(/join\/([^\/\s]+)/i);
  if (!match) {
    status.textContent = "Scanned QR code is not a valid join link.";
    status.style.color = "#c21f3c";
    return;
  }

  const code = match[1].toUpperCase();
  const subject = facultySubjects.find((item) => item.code === code);
  if (!subject) {
    status.textContent = "Scanned subject code is not recognized.";
    status.style.color = "#c21f3c";
    return;
  }

  addStudentSubject(subject);
  status.textContent = `Successfully joined ${subject.name}.`;
  status.style.color = "#14a44d";
  stopQrScanner();
}

function scanError() {
  const status = document.getElementById("qrScanStatus");
  if (status) {
    status.textContent = "Scanning... point the camera at a subject QR code.";
    status.style.color = "#52637a";
  }
}

function startQrScanner() {
  const reader = document.getElementById("qr-reader");
  const status = document.getElementById("qrScanStatus");
  if (!reader) return;

  if (!window.Html5Qrcode) {
    status.textContent = "QR scanning library failed to load.";
    status.style.color = "#c21f3c";
    return;
  }

  if (qrScanning) {
    stopQrScanner();
    return;
  }

  html5QrCode = new Html5Qrcode("qr-reader");
  html5QrCode
    .start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      scanSuccess,
      scanError
    )
    .then(() => {
      qrScanning = true;
      status.textContent = "Scanning for subject join QR codes...";
      status.style.color = "#0f4bb2";
      document.getElementById("qrToggleButton").textContent = "Stop scanning";
    })
    .catch(() => {
      status.textContent = "Unable to start camera. Please allow access.";
      status.style.color = "#c21f3c";
    });
}

function stopQrScanner() {
  const status = document.getElementById("qrScanStatus");
  if (!html5QrCode || !qrScanning) return;

  html5QrCode.stop().then(() => {
    html5QrCode.clear();
    qrScanning = false;
    if (status) {
      status.textContent = "QR scanning stopped.";
      status.style.color = "#52637a";
    }
    document.getElementById("qrToggleButton").textContent = "Start QR scan";
  });
}

function initSubjectModule() {
  const facultyForm = document.getElementById("subjectForm");
  const resetSubjectForm = document.getElementById("resetSubjectForm");
  const joinCodeButton = document.getElementById("joinCodeButton");
  const joinLinkButton = document.getElementById("joinLinkButton");
  const shareClose = document.getElementById("closeShareDialog");
  const copyCode = document.getElementById("copySubjectCode");
  const copyLink = document.getElementById("copyJoinLink");
  const downloadQr = document.getElementById("downloadQrCode");
  const shareButton = document.getElementById("shareSubjectButton");
  const qrToggle = document.getElementById("qrToggleButton");

  if (facultyForm) {
    facultyForm.addEventListener("submit", createSubject);
  }

  if (resetSubjectForm) {
    resetSubjectForm.addEventListener("click", clearCreateForm);
  }

  if (joinCodeButton) {
    joinCodeButton.addEventListener("click", joinByCode);
  }

  if (joinLinkButton) {
    joinLinkButton.addEventListener("click", joinByLink);
  }

  if (shareClose) {
    shareClose.addEventListener("click", closeShareDialog);
  }

  if (copyCode) {
    copyCode.addEventListener("click", () => {
      const value = document.getElementById("shareSubjectCode").value;
      copyToClipboard(value, "shareStatus");
    });
  }

  if (copyLink) {
    copyLink.addEventListener("click", () => {
      const value = document.getElementById("shareJoinLink").value;
      copyToClipboard(value, "shareStatus");
    });
  }

  if (downloadQr) {
    downloadQr.addEventListener("click", downloadQrCode);
  }

  if (shareButton) {
    shareButton.addEventListener("click", shareSubject);
  }

  if (qrToggle) {
    qrToggle.addEventListener("click", startQrScanner);
  }

  renderFacultySubjects();
  renderStudentSubjects();
}

window.addEventListener("DOMContentLoaded", initSubjectModule);
