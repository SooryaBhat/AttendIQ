let cameraStream = null;
let cameraVideoElement = null;
let lastCapturedPhoto = null;
let mediaRecorder = null;
let audioStream = null;
let recordedAudioBlobs = [];
let recordedAudioFile = null;
let recordingTimerInterval = null;

function isCameraSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

function isMicrophoneSupported() {
  return isCameraSupported() && !!window.MediaRecorder;
}

async function startCamera(videoElement) {
  if (!isCameraSupported()) {
    throw new Error('Camera is not available in this browser.');
  }

  if (!videoElement) {
    throw new Error('A video element is required to start the camera.');
  }

  stopCamera();

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
      audio: false,
    });
    cameraStream = stream;
    cameraVideoElement = videoElement;
    videoElement.srcObject = stream;
    await videoElement.play();
    return stream;
  } catch (error) {
    stopCamera();
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      throw new Error('Camera permission denied. Please allow camera access.');
    }
    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      throw new Error('No camera was found on this device.');
    }
    throw error;
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  if (cameraVideoElement) {
    cameraVideoElement.pause();
    cameraVideoElement.srcObject = null;
    cameraVideoElement = null;
  }
}

async function capturePhoto(canvasElement) {
  if (!cameraVideoElement || !cameraStream) {
    throw new Error('Camera has not been started yet.');
  }
  if (!canvasElement) {
    throw new Error('A canvas element is required to capture a photo.');
  }

  const videoWidth = cameraVideoElement.videoWidth || 1280;
  const videoHeight = cameraVideoElement.videoHeight || 720;
  canvasElement.width = videoWidth;
  canvasElement.height = videoHeight;

  const ctx = canvasElement.getContext('2d');
  ctx.drawImage(cameraVideoElement, 0, 0, videoWidth, videoHeight);

  return new Promise((resolve, reject) => {
    canvasElement.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Unable to capture the photo.'));
        return;
      }

      const file = new File([blob], `attendance-${Date.now()}.jpg`, {
        type: 'image/jpeg',
      });
      lastCapturedPhoto = file;
      resolve(file);
    }, 'image/jpeg', 0.92);
  });
}

function retakePhoto() {
  lastCapturedPhoto = null;
  stopCamera();
  return true;
}

async function startRecording() {
  if (!isMicrophoneSupported()) {
    throw new Error('Microphone recording is not supported in this browser.');
  }
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    throw new Error('Recording is already in progress.');
  }

  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    recordedAudioBlobs = [];
    recordedAudioFile = null;

    mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data && event.data.size > 0) {
        recordedAudioBlobs.push(event.data);
      }
    });

    mediaRecorder.start();
    return mediaRecorder;
  } catch (error) {
    stopRecording();
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      throw new Error('Microphone permission denied. Please allow microphone access.');
    }
    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      throw new Error('No microphone was found on this device.');
    }
    throw error;
  }
}

async function stopRecording() {
  if (!mediaRecorder) {
    throw new Error('No active recording session found.');
  }

  return new Promise((resolve, reject) => {
    mediaRecorder.addEventListener('stop', () => {
      const blob = new Blob(recordedAudioBlobs, { type: 'audio/webm' });
      recordedAudioFile = new File([blob], `attendance-${Date.now()}.webm`, { type: blob.type });
      if (audioStream) {
        audioStream.getTracks().forEach((track) => track.stop());
      }
      mediaRecorder = null;
      audioStream = null;
      resolve(recordedAudioFile);
    });

    mediaRecorder.addEventListener('error', (event) => {
      reject(new Error(event.error?.message || 'Recording failed.'));
    });

    try {
      mediaRecorder.stop();
    } catch (error) {
      reject(error);
    }
  });
}

function playRecording(audioElement) {
  if (!recordedAudioFile) {
    throw new Error('No recorded audio file available.');
  }
  if (!audioElement) {
    throw new Error('An audio element is required to play the recording.');
  }

  const url = URL.createObjectURL(recordedAudioFile);
  audioElement.src = url;
  audioElement.play();
  return url;
}

function getCapturedImageFile() {
  return lastCapturedPhoto;
}

function getRecordedAudioFile() {
  return recordedAudioFile;
}

function clearCapturedImage() {
  lastCapturedPhoto = null;
}

function clearRecordedAudio() {
  recordedAudioBlobs = [];
  recordedAudioFile = null;
}

window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.capturePhoto = capturePhoto;
window.retakePhoto = retakePhoto;
window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.playRecording = playRecording;
window.getCapturedImageFile = getCapturedImageFile;
window.getRecordedAudioFile = getRecordedAudioFile;
window.clearCapturedImage = clearCapturedImage;
window.clearRecordedAudio = clearRecordedAudio;
