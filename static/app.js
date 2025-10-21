// 光度立体渲染器 Web 应用 JavaScript

class RenderApp {
    constructor() {
        this.socket = io();
        this.currentImageIndex = 0;
        this.totalImages = 0;
        this.isRendering = false;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadAvailableFiles();
    }
    
    initializeElements() {
        // 表单元素
        this.renderForm = document.getElementById('renderForm');
        this.objSelect = document.getElementById('objSelect');
        this.brdfSelect = document.getElementById('brdfSelect');
        this.renderBtn = document.getElementById('renderBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        
        // 预览元素
        this.previewArea = document.getElementById('previewArea');
        this.defaultHint = document.getElementById('defaultHint');
        this.imageGrid = document.getElementById('imageGrid');
        
        // 进度元素
        this.progressContainer = document.getElementById('progressContainer');
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');
        this.progressPercent = document.getElementById('progressPercent');
    }
    
    setupEventListeners() {
        // 表单提交
        this.renderForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startRender();
        });
        
        // Socket.IO 事件
        this.socket.on('connect', () => {
            console.log('已连接到服务器');
        });
        
        this.socket.on('render_status', (data) => {
            this.updateStatus(data.status, data.message);
        });
        
        this.socket.on('render_progress', (data) => {
            this.updateProgress(data.progress, data.status, data.message);
        });
        
        this.socket.on('render_complete', (data) => {
            console.log('收到 render_complete 事件:', data);
            this.hideProgress();
            
            if (data.images && data.images.length > 0) {
                this.displayAllImages(data.images);
            } else {
                console.error('render_complete 事件中没有图像数据');
                this.showError('渲染完成但没有生成图像');
            }
            
            this.updateStatus(data.status, data.message);
        });
        
        // 添加错误处理
        this.socket.on('connect_error', (error) => {
            console.error('Socket 连接错误:', error);
            this.updateStatus('error', '连接服务器失败');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Socket 断开连接:', reason);
            if (reason === 'io server disconnect') {
                // 服务器主动断开，尝试重连
                this.socket.connect();
            }
        });
    }
    
    async loadAvailableFiles() {
        try {
            const response = await fetch('/api/files');
            const data = await response.json();
            
            // 填充 OBJ 文件选项
            this.objSelect.innerHTML = '<option value="">选择模型...</option>';
            data.obj_files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                this.objSelect.appendChild(option);
            });
            
            // 填充 BRDF 文件选项
            this.brdfSelect.innerHTML = '<option value="">选择材质...</option>';
            data.brdf_files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                this.brdfSelect.appendChild(option);
            });
            
            // 如果有可用文件，自动选择第一个
            if (data.obj_files.length > 0) {
                this.objSelect.value = data.obj_files[0];
            }
            if (data.brdf_files.length > 0) {
                this.brdfSelect.value = data.brdf_files[0];
            }
            
        } catch (error) {
            console.error('加载文件列表失败:', error);
            this.updateStatus('error', '无法加载文件列表');
        }
    }
    
    async startRender() {
        if (this.isRendering) {
            return;
        }
        
        // 验证输入
        if (!this.objSelect.value || !this.brdfSelect.value) {
            alert('请选择模型和材质文件');
            return;
        }
        
        this.isRendering = true;
        this.renderBtn.disabled = true;
        this.renderBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 渲染中...';
        
        // 收集参数
        const params = this.collectRenderParams();
        
        try {
            const response = await fetch('/api/render', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(params)
            });
            
            const result = await response.json();
            
            if (!result.success) {
                this.updateStatus('error', result.message);
                this.resetRenderButton();
            }
            
        } catch (error) {
            console.error('启动渲染失败:', error);
            this.updateStatus('error', '启动渲染失败');
            this.resetRenderButton();
        }
    }
    
    collectRenderParams() {
        const imageSize = parseInt(document.getElementById('imageSize').value);
        const cameraDistance = parseFloat(document.getElementById('cameraDistance').value);
        
        return {
            obj_name: this.objSelect.value,
            brdf_name: this.brdfSelect.value,
            num_lights: parseInt(document.getElementById('numLights').value),
            light_pattern: document.getElementById('lightPattern').value,
            light_distance: parseFloat(document.getElementById('lightDistance').value),
            light_intensity: parseFloat(document.getElementById('lightIntensity').value),
            camera_fov: parseFloat(document.getElementById('cameraFov').value),
            camera_position: [0, 0, cameraDistance],
            camera_target: [0, 0, 0],
            image_size: [imageSize, imageSize],
            spp: parseInt(document.getElementById('spp').value)
        };
    }
    
    updateStatus(status, message) {
        const statusClasses = {
            'ready': 'status-ready',
            'starting': 'status-rendering',
            'rendering': 'status-rendering',
            'completed': 'status-completed',
            'error': 'status-error'
        };
        
        const statusIcons = {
            'ready': 'bi-circle-fill',
            'starting': 'bi-hourglass-split',
            'rendering': 'bi-hourglass-split',
            'completed': 'bi-check-circle-fill',
            'error': 'bi-exclamation-triangle-fill'
        };
        
        // 更新状态指示器
        this.statusIndicator.className = `status-indicator ${statusClasses[status] || 'status-ready'}`;
        this.statusIndicator.innerHTML = `<i class="bi ${statusIcons[status] || 'bi-circle-fill'}"></i> ${message}`;
        
        // 如果渲染完成或出错，重置按钮
        if (status === 'completed' || status === 'error') {
            this.resetRenderButton();
        }
    }
    
    resetRenderButton() {
        this.isRendering = false;
        this.renderBtn.disabled = false;
        this.renderBtn.innerHTML = '<i class="bi bi-play-fill"></i> 开始渲染';
    }
    
    updateProgress(progress, status, message) {
        // 显示进度容器
        this.progressContainer.style.display = 'block';
        
        // 计算进度百分比
        const percent = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;
        
        // 更新进度条
        this.progressBar.style.width = `${percent}%`;
        this.progressPercent.textContent = `${percent}%`;
        
        // 更新进度文本
        let progressMessage = message;
        if (progress.current_image) {
            progressMessage += ` (${progress.current_image})`;
        }
        this.progressText.textContent = progressMessage;
        
        // 更新状态
        this.updateStatus(status, message);
    }
    
    hideProgress() {
        this.progressContainer.style.display = 'none';
    }
    
    displayAllImages(images) {
        if (!images || images.length === 0) {
            this.showError('没有渲染图像可显示');
            return;
        }
        
        // 隐藏默认提示，显示图像网格
        this.defaultHint.style.display = 'none';
        this.imageGrid.style.display = 'block';
        this.imageGrid.innerHTML = '';
        
        // 创建图像网格
        images.forEach((imageData, index) => {
            const colDiv = document.createElement('div');
            colDiv.className = 'col-md-6 col-lg-4 mb-3';
            
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            imageItem.style.cursor = 'pointer';
            
            const img = document.createElement('img');
            img.src = imageData.data;
            img.alt = imageData.name;
            img.className = 'img-fluid';
            
            const label = document.createElement('div');
            label.className = 'image-label';
            label.textContent = `光源 ${imageData.light_id}: ${imageData.name}`;
            
            // 点击放大功能
            imageItem.addEventListener('click', () => {
                this.showImageModal(imageData);
            });
            
            imageItem.appendChild(img);
            imageItem.appendChild(label);
            colDiv.appendChild(imageItem);
            this.imageGrid.appendChild(colDiv);
        });
        
        console.log(`显示了 ${images.length} 张 RGB 渲染图像`);
    }
    
    showError(message) {
        if (this.imageGrid) {
            this.imageGrid.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-warning text-center">
                        <i class="bi bi-exclamation-triangle"></i>
                        ${message}
                    </div>
                </div>
            `;
            this.imageGrid.style.display = 'block';
        }
        if (this.defaultHint) {
            this.defaultHint.style.display = 'none';
        }
    }
    
    showImageModal(imageData) {
        console.log('显示模态框:', imageData.name);
        
        // 使用大图数据，如果没有则使用原图
        const imageSource = imageData.large_data || imageData.data;
        
        // 创建模态框显示大图
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-image"></i>
                            ${imageData.name}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center p-4">
                        <img src="${imageSource}" alt="${imageData.name}" class="img-fluid" style="max-height: 70vh;">
                        <div class="mt-3 text-muted">
                            <small>
                                光源 ${imageData.light_id} | 
                                ${imageData.size ? `缩略图: ${imageData.size[0]}×${imageData.size[1]}` : ''} |
                                ${imageData.original_size ? `原图: ${imageData.original_size[0]}×${imageData.original_size[1]}` : ''}
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-primary" onclick="this.downloadImage('${imageData.name}', '${imageSource}')">
                            <i class="bi bi-download"></i> 下载
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 确保 Bootstrap 已加载
        if (typeof bootstrap !== 'undefined') {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } else {
            // 备用显示方法
            modal.style.display = 'block';
            modal.classList.add('show');
        }
        
        // 模态框关闭后移除元素
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
        
        // 添加点击背景关闭功能
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
                document.body.removeChild(modal);
            }
        });
    }
    
    downloadImage(filename, dataUrl) {
        console.log('下载图像:', filename);
        const link = document.createElement('a');
        link.download = filename;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    

}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new RenderApp();
});