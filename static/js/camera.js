/**
 * Camera Preview Module - Hỗ trợ mở camera realtime
 * Tích hợp với OCR Scanner
 */

let cameraStream = null;
let videoElement = null;
let canvasElement = null;

/**
 * Mở camera với getUserMedia API
 */
async function openCameraPreview() {
    try {
        // Tạo modal camera preview
        const modalHTML = `
            <div id="camera-modal" class="camera-modal">
                <div class="camera-modal-content">
                    <div class="camera-header">
                        <h3><i class="fa-solid fa-camera"></i> Camera Preview</h3>
                        <button onclick="closeCameraPreview()" class="btn-close-camera">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                    <div class="camera-body">
                        <video id="camera-video" autoplay playsinline></video>
                        <canvas id="camera-canvas" style="display:none;"></canvas>
                    </div>
                    <div class="camera-footer">
                        <button onclick="closeCameraPreview()" class="btn-camera-action secondary">
                            <i class="fa-solid fa-xmark"></i> Hủy
                        </button>
                        <button onclick="captureFromCamera()" class="btn-camera-action primary">
                            <i class="fa-solid fa-camera"></i> Chụp ảnh
                        </button>
                        <button onclick="toggleCameraFlash()" class="btn-camera-action secondary">
                            <i class="fa-solid fa-lightbulb"></i> Đèn flash
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Thêm modal vào body
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = modalHTML;
        document.body.appendChild(tempDiv.firstElementChild);
        
        // Lấy video element
        videoElement = document.getElementById('camera-video');
        canvasElement = document.getElementById('camera-canvas');
        
        // Request camera permission
        const constraints = {
            video: {
                facingMode: 'environment', // Camera sau trên mobile
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            },
            audio: false
        };
        
        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        videoElement.srcObject = cameraStream;
        
        console.log('✓ Camera opened successfully');
        
    } catch (error) {
        console.error('Camera error:', error);
        
        let errorMsg = 'Không thể mở camera. ';
        if (error.name === 'NotAllowedError') {
            errorMsg += 'Vui lòng cấp quyền truy cập camera.';
        } else if (error.name === 'NotFoundError') {
            errorMsg += 'Không tìm thấy camera trên thiết bị.';
        } else if (error.name === 'NotReadableError') {
            errorMsg += 'Camera đang được sử dụng bởi ứng dụng khác.';
        } else {
            errorMsg += error.message;
        }
        
        alert(errorMsg);
        closeCameraPreview();
    }
}

/**
 * Đóng camera và cleanup
 */
function closeCameraPreview() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const modal = document.getElementById('camera-modal');
    if (modal) {
        modal.remove();
    }
    
    videoElement = null;
    canvasElement = null;
}

/**
 * Chụp ảnh từ camera preview
 */
async function captureFromCamera() {
    if (!videoElement || !canvasElement) {
        alert('Camera chưa sẵn sàng');
        return;
    }
    
    try {
        // Set canvas size to video size
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        
        // Draw video frame to canvas
        const ctx = canvasElement.getContext('2d');
        ctx.drawImage(videoElement, 0, 0);
        
        // Convert to blob
        canvasElement.toBlob(async (blob) => {
            if (!blob) {
                alert('Không thể chụp ảnh');
                return;
            }
            
            // Đóng camera
            closeCameraPreview();
            
            // Chuyển blob thành base64
            const reader = new FileReader();
            reader.onloadend = function() {
                const base64data = reader.result;
                
                // Gọi hàm xử lý OCR (giống như upload file)
                processOcrImage(blob, base64data);
            };
            reader.readAsDataURL(blob);
            
        }, 'image/jpeg', 0.9);
        
    } catch (error) {
        console.error('Capture error:', error);
        alert('Lỗi khi chụp ảnh: ' + error.message);
    }
}

/**
 * Toggle camera flash (nếu có)
 */
async function toggleCameraFlash() {
    if (!cameraStream) return;
    
    try {
        const track = cameraStream.getVideoTracks()[0];
        const capabilities = track.getCapabilities();
        
        if (capabilities.torch) {
            const currentSettings = track.getSettings();
            const newTorchState = !currentSettings.torch;
            
            await track.applyConstraints({
                advanced: [{ torch: newTorchState }]
            });
            
            console.log('Flash toggled:', newTorchState);
        } else {
            alert('Thiết bị không hỗ trợ đèn flash camera');
        }
    } catch (error) {
        console.error('Flash toggle error:', error);
    }
}

/**
 * Xử lý ảnh OCR (gọi từ capture hoặc upload)
 */
async function processOcrImage(file, previewUrl) {
    // Hiện khu vực OCR nếu đang đóng
    const ocrBody = document.getElementById('ocr-body');
    if (ocrBody.style.display === 'none') {
        toggleOcrSection();
    }
    
    // Ẩn upload area, hiện loading
    document.getElementById('ocr-upload-area').style.display = 'none';
    document.getElementById('ocr-loading').style.display = 'flex';
    document.getElementById('ocr-result-area').style.display = 'none';
    
    // Tạo FormData
    const formData = new FormData();
    formData.append('receipt', file);
    
    try {
        const response = await fetch('/api/ocr/scan-receipt', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Ẩn loading
        document.getElementById('ocr-loading').style.display = 'none';
        
        if (result.ok && result.data) {
            // Hiển thị kết quả
            displayOcrResult(result.data, previewUrl);
        } else {
            // Hiển thị lỗi
            alert('Lỗi OCR: ' + (result.error || 'Không xác định'));
            resetOcrScanner();
        }
        
    } catch (error) {
        document.getElementById('ocr-loading').style.display = 'none';
        console.error('OCR error:', error);
        alert('Không thể quét hóa đơn. Vui lòng thử lại.');
        resetOcrScanner();
    }
}

/**
 * Hiển thị kết quả OCR
 */
function displayOcrResult(data, imageUrl) {
    const resultArea = document.getElementById('ocr-result-area');
    
    // Set preview image
    document.getElementById('ocr-preview-img').src = imageUrl;
    
    // Set merchant name
    document.getElementById('ocr-merchant-name').textContent = data.merchant || 'Không xác định';
    document.getElementById('ocr-edit-merchant').value = data.merchant || '';
    
    // Set timestamp
    if (data.timestamp) {
        const dt = new Date(data.timestamp);
        const formatted = dt.toISOString().slice(0, 16);
        document.getElementById('ocr-edit-timestamp').value = formatted;
        document.getElementById('ocr-timestamp-display').textContent = 
            dt.toLocaleDateString('vi-VN') + ' ' + dt.toLocaleTimeString('vi-VN');
    } else {
        const now = new Date();
        document.getElementById('ocr-edit-timestamp').value = now.toISOString().slice(0, 16);
        document.getElementById('ocr-timestamp-display').textContent = 'Hôm nay';
    }
    
    // Set source banner
    const banner = document.getElementById('ocr-source-banner');
    const source = data.source || 'unknown';
    
    if (source === 'easyocr_local') {
        banner.className = 'ocr-source-banner success';
        banner.innerHTML = '<i class="fa-solid fa-check-circle"></i> Đã quét bằng EasyOCR (Offline)';
    } else if (source.includes('gemini')) {
        banner.className = 'ocr-source-banner success';
        banner.innerHTML = '<i class="fa-solid fa-sparkles"></i> Đã quét bằng Gemini AI';
    } else {
        banner.className = 'ocr-source-banner warning';
        banner.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i> OCR cục bộ';
    }
    
    // Warnings
    const warningsContainer = document.getElementById('ocr-warnings-container');
    warningsContainer.innerHTML = '';
    if (data.warnings && data.warnings.length > 0) {
        data.warnings.forEach(warn => {
            const warnDiv = document.createElement('div');
            warnDiv.className = 'ocr-warning-box';
            warnDiv.innerHTML = `<i class="fa-solid fa-info-circle"></i> ${warn}`;
            warningsContainer.appendChild(warnDiv);
        });
    }
    
    // Items table
    const tbody = document.getElementById('ocr-items-tbody');
    tbody.innerHTML = '';
    
    if (data.items && data.items.length > 0) {
        data.items.forEach((item, index) => {
            addOcrItemRow(item, index);
        });
    }
    
    // Update total
    updateOcrTotal();
    
    // Show result area
    resultArea.style.display = 'block';
    
    // Store raw data
    window.ocrRawData = data;
}

/**
 * Thêm row item vào bảng OCR
 */
function addOcrItemRow(item, index) {
    const tbody = document.getElementById('ocr-items-tbody');
    const row = document.createElement('tr');
    row.dataset.index = index;
    
    row.innerHTML = `
        <td><input type="text" class="ocr-item-input" value="${item.name || ''}" onchange="updateOcrTotal()"></td>
        <td><input type="number" class="ocr-item-input text-center" value="${item.quantity || 1}" min="1" onchange="updateOcrTotal()"></td>
        <td><input type="number" class="ocr-item-input text-right" value="${item.unit_price || 0}" min="0" onchange="updateOcrTotal()"></td>
        <td><input type="number" class="ocr-item-input text-right" value="${item.amount || 0}" min="0" onchange="updateOcrTotal()"></td>
        <td>
            <select class="ocr-item-select" onchange="updateOcrTotal()">
                <option value="Ăn uống" ${item.category === 'Ăn uống' ? 'selected' : ''}>Ăn uống</option>
                <option value="Cà phê" ${item.category === 'Cà phê' ? 'selected' : ''}>Cà phê</option>
                <option value="Đi lại" ${item.category === 'Đi lại' ? 'selected' : ''}>Đi lại</option>
                <option value="Mua sắm" ${item.category === 'Mua sắm' ? 'selected' : ''}>Mua sắm</option>
                <option value="Hóa đơn sinh hoạt" ${item.category === 'Hóa đơn sinh hoạt' ? 'selected' : ''}>Hóa đơn</option>
                <option value="Giải trí" ${item.category === 'Giải trí' ? 'selected' : ''}>Giải trí</option>
                <option value="Sức khỏe" ${item.category === 'Sức khỏe' ? 'selected' : ''}>Sức khỏe</option>
                <option value="Khác" ${item.category === 'Khác' ? 'selected' : ''}>Khác</option>
            </select>
        </td>
        <td><button type="button" class="btn-delete-item" onclick="deleteOcrItem(this)"><i class="fa-solid fa-trash"></i></button></td>
    `;
    
    tbody.appendChild(row);
}

/**
 * Update tổng tiền OCR
 */
function updateOcrTotal() {
    const rows = document.querySelectorAll('#ocr-items-tbody tr');
    let total = 0;
    
    rows.forEach(row => {
        const amountInput = row.querySelectorAll('input')[3]; // Amount column
        const amount = parseInt(amountInput.value) || 0;
        total += amount;
    });
    
    document.getElementById('ocr-total-display').textContent = total.toLocaleString('vi-VN') + 'đ';
    
    // Enable/disable confirm button
    const confirmBtn = document.getElementById('btn-ocr-confirm');
    confirmBtn.disabled = (rows.length === 0 || total === 0);
}

// Export functions to global scope
window.openCameraPreview = openCameraPreview;
window.closeCameraPreview = closeCameraPreview;
window.captureFromCamera = captureFromCamera;
window.toggleCameraFlash = toggleCameraFlash;
window.processOcrImage = processOcrImage;
window.displayOcrResult = displayOcrResult;
window.updateOcrTotal = updateOcrTotal;
