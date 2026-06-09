// Geolocation for upload
document.addEventListener('DOMContentLoaded', function() {
    const locationInput = document.getElementById('location');
    if (locationInput) {
        navigator.geolocation.getCurrentPosition(function(position) {
            locationInput.value = position.coords.latitude + ',' + position.coords.longitude;
        }, function(error) {
            console.log('Geolocation error:', error);
            locationInput.value = 'Unknown';
        });
    }

    // Camera functionality (only if elements exist)
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const startCameraBtn = document.getElementById('startCamera');
    const captureBtn = document.getElementById('capture');
    const stopCameraBtn = document.getElementById('stopCamera');
    const liveDetectionCheckbox = document.getElementById('liveDetection');
    const liveVideoCheckbox = document.getElementById('liveVideo');
    const status = document.getElementById('status');
    let stream;
    let liveDetectionInterval;
    let liveVideoInterval;

    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                startCameraBtn.style.display = 'none';
                captureBtn.style.display = 'inline';
                stopCameraBtn.style.display = 'inline';
                status.textContent = 'Camera started. Click Capture to take a photo.';
                if (liveDetectionCheckbox && liveDetectionCheckbox.checked) {
                    startLiveDetection();
                }
                if (liveVideoCheckbox && liveVideoCheckbox.checked) {
                    startLiveVideo();
                }
            } catch (err) {
                status.textContent = 'Error accessing camera: ' + err.message;
            }
        });
    }

    if (captureBtn) {
        captureBtn.addEventListener('click', () => {
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
                const file = new File([blob], 'captured_image.jpg', { type: 'image/jpeg' });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('file').files = dataTransfer.files;
                status.textContent = 'Image captured. Click Upload and Detect to proceed.';
            });
        });
    }

    if (stopCameraBtn) {
        stopCameraBtn.addEventListener('click', () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                video.srcObject = null;
                startCameraBtn.style.display = 'inline';
                captureBtn.style.display = 'none';
                stopCameraBtn.style.display = 'none';
                status.textContent = '';
                stopLiveDetection();
                stopLiveVideo();
            }
        });
    }

    if (liveDetectionCheckbox) {
        liveDetectionCheckbox.addEventListener('change', () => {
            if (liveDetectionCheckbox.checked && stream) {
                startLiveDetection();
            } else {
                stopLiveDetection();
            }
        });
    }

    if (liveVideoCheckbox) {
        liveVideoCheckbox.addEventListener('change', () => {
            if (liveVideoCheckbox.checked && stream) {
                startLiveVideo();
            } else {
                stopLiveVideo();
            }
        });
    }

    function startLiveDetection() {
        liveDetectionInterval = setInterval(async () => {
            if (!stream) return;
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('file', new File([blob], 'live_image.jpg', { type: 'image/jpeg' }));
                formData.append('location', document.getElementById('location').value);

                try {
                    const response = await fetch('/detect_live', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    if (result.error) {
                        status.textContent = `Live Detection Error: ${result.error}`;
                        return;
                    }
                    status.textContent = `Live Detection: ${result.cars} cars, ${result.persons} persons. ${result.accident ? 'Accident Detected!' : 'No Accident'}`;
                    if (result.accident) {
                        // Trigger alert for live detection
                        alert('Accident detected in live feed!');
                    }
                } catch (err) {
                    console.error('Live detection error:', err);
                    status.textContent = 'Live detection failed';
                }
            });
        }, 2000); // Detect every 2 seconds
    }

    function stopLiveDetection() {
        if (liveDetectionInterval) {
            clearInterval(liveDetectionInterval);
            liveDetectionInterval = null;
        }
    }

    function startLiveVideo() {
        liveVideoInterval = setInterval(async () => {
            if (!stream) return;
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('file', new File([blob], 'live_video_frame.jpg', { type: 'image/jpeg' }));
                formData.append('location', document.getElementById('location').value);

                try {
                    const response = await fetch('/detect_live', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    if (result.error) {
                        status.textContent = `Live Video Error: ${result.error}`;
                        return;
                    }
                    status.textContent = `Live Video: ${result.cars} cars, ${result.persons} persons. ${result.accident ? 'Accident Detected!' : 'No Accident'}`;
                    if (result.accident) {
                        // Trigger alert for live video
                        alert('Accident detected in live video!');
                    }
                } catch (err) {
                    console.error('Live video error:', err);
                    status.textContent = 'Live video failed';
                }
            });
        }, 1000); // Detect every 1 second for video
    }

    function stopLiveVideo() {
        if (liveVideoInterval) {
            clearInterval(liveVideoInterval);
            liveVideoInterval = null;
        }
    }
});
