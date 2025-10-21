// 光度立体渲染器 Web 应用 JavaScript
// 支持单相机和光场相机阵列模式

class RenderApp {
    constructor() {
        this.socket = io();
        this.currentImageIndex = 0;
        this.totalImages = 0;
        this.isRendering = false;
        this.lights = [];
        this.lightIdCounter = 0;
        this.cameraMode = 'single'; // 'single' or 'lightfield'

        this.initializeElements();
        this.setupEventListeners();
        this.loadAvailableFiles();
        this.addDefaultLight();

        // 延迟初始化，确保DOM完全加载
        setTimeout(() => {
            // 确保初始状态正确
            const cameraModeSelect = document.getElementById('cameraMode');
            if (cameraModeSelect && cameraModeSelect.value !== 'single') {
                cameraModeSelect.value = 'single';
            }

            // 确保显示状态正确
            const singleSettings = document.getElementById('singleCameraSettings');
            const lightfieldSettings = document.getElementById('lightfieldCameraSettings');

            if (singleSettings && lightfieldSettings) {
                singleSettings.style.display = 'block';
                lightfieldSettings.style.display = 'none';
                singleSettings.classList.add('active');
                lightfieldSettings.classList.remove('active');
            }

            // 初始化光场预览
            this.updateLightfieldPreview();
        }, 200);
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

        // 光源元素
        this.lightsContainer = document.getElementById('lightsContainer');
        this.addLightBtn = document.getElementById('addLightBtn');
        this.lightCount = document.getElementById('lightCount');

        // 光场相机元素
        this.cameraMode = document.getElementById('cameraMode');
        this.singleCameraSettings = document.getElementById('singleCameraSettings');
        this.lightfieldCameraSettings = document.getElementById('lightfieldCameraSettings');
        this.lightfieldPreview = document.getElementById('lightfieldPreview');
        this.totalCameras = document.getElementById('totalCameras');
    }

    setupEventListeners() {
        // 表单提交
        this.renderForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startRender();
        });

        // 添加光源按钮
        this.addLightBtn.addEventListener('click', () => {
            this.addLight(); // 默认添加点光源
        });

        // 相机模式切换
        const cameraModeSelect = document.getElementById('cameraMode');
        if (cameraModeSelect) {
            cameraModeSelect.addEventListener('change', () => {
                this.toggleCameraMode();
            });
        }

        // 光场相机参数变化监听器
        const lightfieldInputs = [
            'lightfieldGridSize', 'lightfieldSpacingX', 'lightfieldSpacingY',
            'lightfieldCenterX', 'lightfieldCenterY', 'lightfieldDistanceZ'
        ];

        lightfieldInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => {
                    this.updateLightfieldPreview();
                });
            }
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

        // 如果没有光源，提示用户只会渲染法线图
        if (this.lights.length === 0) {
            const confirmed = confirm('没有光源配置，只会渲染法线图。\n\n是否继续？\n\n（点击"添加光源"按钮可以添加光源来渲染光源图像）');
            if (!confirmed) {
                return;
            }
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
        const cameraMode = document.getElementById('cameraMode').value;

        // 收集光源参数
        console.log('当前光源列表:', this.lights);
        const lightsData = this.lights.map(light => {
            const lightData = {
                type: light.type,
                intensity: light.intensity
            };

            if (light.type === 'point') {
                lightData.position = [light.x, light.y, light.z];
            } else if (light.type === 'directional') {
                // 归一化方向向量
                const length = Math.sqrt(light.dirX * light.dirX + light.dirY * light.dirY + light.dirZ * light.dirZ);
                if (length > 0) {
                    lightData.direction = [light.dirX / length, light.dirY / length, light.dirZ / length];
                } else {
                    lightData.direction = [0, 0, -1]; // 默认向下
                }
            }

            return lightData;
        });

        console.log('发送到后端的光源数据:', lightsData);

        const baseParams = {
            obj_name: this.objSelect.value,
            brdf_name: this.brdfSelect.value,
            lights: lightsData,
            image_size: [imageSize, imageSize],
            spp: parseInt(document.getElementById('spp').value),
            camera_mode: cameraMode
        };

        if (cameraMode === 'single') {
            // 单相机模式
            const cameraPosX = parseFloat(document.getElementById('cameraPosX').value);
            const cameraPosY = parseFloat(document.getElementById('cameraPosY').value);
            const cameraPosZ = parseFloat(document.getElementById('cameraPosZ').value);
            const cameraTargetX = parseFloat(document.getElementById('cameraTargetX').value);
            const cameraTargetY = parseFloat(document.getElementById('cameraTargetY').value);
            const cameraTargetZ = parseFloat(document.getElementById('cameraTargetZ').value);

            baseParams.camera_fov = parseFloat(document.getElementById('cameraFov').value);
            baseParams.camera_position = [cameraPosX, cameraPosY, cameraPosZ];
            baseParams.camera_target = [cameraTargetX, cameraTargetY, cameraTargetZ];
        } else {
            // 光场相机模式
            const gridSize = parseInt(document.getElementById('lightfieldGridSize').value);
            const spacingX = parseFloat(document.getElementById('lightfieldSpacingX').value);
            const spacingY = parseFloat(document.getElementById('lightfieldSpacingY').value);
            const centerX = parseFloat(document.getElementById('lightfieldCenterX').value);
            const centerY = parseFloat(document.getElementById('lightfieldCenterY').value);
            const distanceZ = parseFloat(document.getElementById('lightfieldDistanceZ').value);
            const targetX = parseFloat(document.getElementById('lightfieldTargetX').value);
            const targetY = parseFloat(document.getElementById('lightfieldTargetY').value);
            const targetZ = parseFloat(document.getElementById('lightfieldTargetZ').value);

            baseParams.camera_fov = parseFloat(document.getElementById('lightfieldFov').value);
            baseParams.lightfield_config = {
                grid_size: gridSize,
                spacing_x: spacingX,
                spacing_y: spacingY,
                center_position: [centerX, centerY, distanceZ],
                target_position: [targetX, targetY, targetZ]
            };
        }

        return baseParams;
    }

    addDefaultLight() {
        // 添加一个默认点光源（前上方，强光照）
        this.addLight(2, 2, 3, 300, 'point');  // 默认点光源
    }

    addDefaultLights() {
        // 添加4个默认点光源（在物体周围，相机侧，强光照）
        const defaultLights = [
            { x: 2, y: 2, z: 3, intensity: 300, type: 'point' },   // 右上前方
            { x: -2, y: 2, z: 3, intensity: 300, type: 'point' },  // 左上前方
            { x: 2, y: -2, z: 3, intensity: 300, type: 'point' },  // 右下前方
            { x: -2, y: -2, z: 3, intensity: 300, type: 'point' }  // 左下前方
        ];

        defaultLights.forEach(light => {
            this.addLight(light.x, light.y, light.z, light.intensity, light.type);
        });
    }

    addLight(x = 2, y = 2, z = 3, intensity = 300, type = 'point') {
        const lightId = this.lightIdCounter++;
        const light = {
            id: lightId,
            x, y, z,
            intensity,
            type,
            // 平行光方向（归一化向量）
            dirX: 0.5, dirY: 0.5, dirZ: -1  // 默认从右上方向下照射
        };
        this.lights.push(light);

        this.renderLightCard(light);
        this.updateLightCount();
    }

    removeLight(lightId) {
        this.lights = this.lights.filter(light => light.id !== lightId);
        document.getElementById(`light-card-${lightId}`).remove();
        this.updateLightCount();
        // 重新渲染所有光源卡片以更新编号
        this.rerenderAllLightCards();
    }

    updateLight(lightId, field, value) {
        const light = this.lights.find(l => l.id === lightId);
        if (light) {
            if (field === 'type') {
                light[field] = value;
                // 重新渲染光源卡片以显示/隐藏相应的控件
                this.rerenderSingleLightCard(lightId);
            } else {
                light[field] = parseFloat(value);
            }
        }
    }

    updateLightCount() {
        this.lightCount.textContent = this.lights.length;
    }

    rerenderAllLightCards() {
        // 清空容器
        this.lightsContainer.innerHTML = '';
        // 重新渲染所有光源
        this.lights.forEach(light => {
            this.renderLightCard(light);
        });
    }

    rerenderSingleLightCard(lightId) {
        // 找到对应的光源
        const light = this.lights.find(l => l.id === lightId);
        if (!light) return;

        // 移除旧的卡片
        const oldCard = document.getElementById(`light-card-${lightId}`);
        if (oldCard) {
            oldCard.remove();
        }

        // 重新渲染卡片
        this.renderLightCard(light);
    }

    renderLightCard(light) {
        const card = document.createElement('div');
        card.className = 'light-card';
        card.id = `light-card-${light.id}`;
        card.setAttribute('data-type', light.type);

        // 计算当前光源的显示编号（基于在数组中的位置）
        const displayIndex = this.lights.findIndex(l => l.id === light.id) + 1;

        // 根据光源类型选择图标
        const lightIcon = light.type === 'directional' ? 'bi-arrow-down-circle-fill' : 'bi-lightbulb-fill';
        const lightTypeText = light.type === 'directional' ? '平行光' : '点光源';

        // 构建基础HTML
        let cardHTML = `
            <div class="light-card-header">
                <span class="light-card-title">
                    <i class="bi ${lightIcon} text-warning"></i>
                    光源 ${displayIndex} (${lightTypeText})
                </span>
                <button type="button" class="btn btn-sm btn-danger remove-light-btn" onclick="app.removeLight(${light.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="row g-2">
                <!-- 光源类型选择 -->
                <div class="col-12">
                    <label class="form-label" style="font-size: 0.85em;">光源类型</label>
                    <select class="form-select form-select-sm" onchange="app.updateLight(${light.id}, 'type', this.value)">
                        <option value="point" ${light.type === 'point' ? 'selected' : ''}>点光源</option>
                        <option value="directional" ${light.type === 'directional' ? 'selected' : ''}>平行光</option>
                    </select>
                </div>
        `;

        if (light.type === 'point') {
            // 点光源：显示位置控件
            cardHTML += `
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">位置 X</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.x}" step="0.1"
                           onchange="app.updateLight(${light.id}, 'x', this.value)">
                </div>
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">位置 Y</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.y}" step="0.1"
                           onchange="app.updateLight(${light.id}, 'y', this.value)">
                </div>
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">位置 Z</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.z}" step="0.1"
                           onchange="app.updateLight(${light.id}, 'z', this.value)">
                </div>
            `;
        } else {
            // 平行光：显示方向控件
            cardHTML += `
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">方向 X</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.dirX}" step="0.1" min="-1" max="1"
                           onchange="app.updateLight(${light.id}, 'dirX', this.value)">
                </div>
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">方向 Y</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.dirY}" step="0.1" min="-1" max="1"
                           onchange="app.updateLight(${light.id}, 'dirY', this.value)">
                </div>
                <div class="col-4">
                    <label class="form-label" style="font-size: 0.85em;">方向 Z</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.dirZ}" step="0.1" min="-1" max="1"
                           onchange="app.updateLight(${light.id}, 'dirZ', this.value)">
                </div>
                <div class="col-12">
                    <small class="text-muted">
                        <i class="bi bi-info-circle"></i>
                        方向向量会自动归一化。负Z值表示向下照射。
                    </small>
                </div>
            `;
        }

        // 添加强度控件
        cardHTML += `
                <div class="col-12">
                    <label class="form-label" style="font-size: 0.85em;">强度</label>
                    <input type="number" class="form-control form-control-sm" 
                           value="${light.intensity}" min="1" max="500"
                           onchange="app.updateLight(${light.id}, 'intensity', this.value)">
                </div>
            </div>
        `;

        card.innerHTML = cardHTML;
        this.lightsContainer.appendChild(card);
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

            // 根据图像类型显示不同的标签
            if (imageData.type === 'normal') {
                label.innerHTML = `<i class="bi bi-grid-3x3-gap"></i> ${imageData.display_name}`;
                imageItem.style.border = '2px solid #28a745'; // 绿色边框标识法线图
            } else {
                label.innerHTML = `<i class="bi bi-lightbulb-fill"></i> ${imageData.display_name}`;
            }

            // 点击放大功能
            imageItem.addEventListener('click', () => {
                this.showImageModal(imageData);
            });

            imageItem.appendChild(img);
            imageItem.appendChild(label);
            colDiv.appendChild(imageItem);
            this.imageGrid.appendChild(colDiv);
        });

        // 统计不同类型的图像
        const lightImages = images.filter(img => img.type === 'light').length;
        const normalImages = images.filter(img => img.type === 'normal').length;
        console.log(`显示了 ${lightImages} 张光源图像和 ${normalImages} 张法线图，总计 ${images.length} 张图像`);
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

    toggleCameraMode() {
        const cameraModeSelect = document.getElementById('cameraMode');
        if (!cameraModeSelect) return;

        const mode = cameraModeSelect.value;
        this.cameraMode = mode;

        const singleSettings = document.getElementById('singleCameraSettings');
        const lightfieldSettings = document.getElementById('lightfieldCameraSettings');

        if (!singleSettings || !lightfieldSettings) return;

        // 移除之前的active类
        singleSettings.classList.remove('active');
        lightfieldSettings.classList.remove('active');

        if (mode === 'single') {
            singleSettings.style.display = 'block';
            lightfieldSettings.style.display = 'none';
            singleSettings.classList.add('active');
        } else {
            singleSettings.style.display = 'none';
            lightfieldSettings.style.display = 'block';
            lightfieldSettings.classList.add('active');
            this.updateLightfieldPreview();
        }
    }

    updateLightfieldPreview() {
        const lightfieldPreview = document.getElementById('lightfieldPreview');
        if (!lightfieldPreview) return;

        const gridSize = parseInt(document.getElementById('lightfieldGridSize')?.value || 3);
        const spacingX = parseFloat(document.getElementById('lightfieldSpacingX')?.value || 0.5);
        const spacingY = parseFloat(document.getElementById('lightfieldSpacingY')?.value || 0.5);
        const centerX = parseFloat(document.getElementById('lightfieldCenterX')?.value || 0);
        const centerY = parseFloat(document.getElementById('lightfieldCenterY')?.value || 0);

        // 更新总相机数
        const totalCameras = gridSize * gridSize;
        if (this.totalCameras) {
            this.totalCameras.textContent = totalCameras;
        }

        // 生成相机位置预览
        let previewHTML = `<div class="lightfield-grid-preview" style="grid-template-columns: repeat(${gridSize}, 1fr);">`;

        for (let i = 0; i < gridSize; i++) {
            for (let j = 0; j < gridSize; j++) {
                const x = centerX + (j - (gridSize - 1) / 2) * spacingX;
                const y = centerY + (i - (gridSize - 1) / 2) * spacingY;
                const camNum = i * gridSize + j + 1;

                previewHTML += `
                    <div class="camera-position" title="相机 ${camNum}: (${x.toFixed(1)}, ${y.toFixed(1)})">
                        ${camNum}
                    </div>
                `;
            }
        }

        previewHTML += '</div>';
        previewHTML += `
            <div class="mt-3 text-center">
                <small class="text-muted">
                    <i class="bi bi-grid-3x3"></i>
                    网格: ${gridSize}×${gridSize} | 间隔: X=${spacingX}, Y=${spacingY}<br>
                    <i class="bi bi-crosshair"></i>
                    中心: (${centerX}, ${centerY}) | 总计: ${totalCameras} 个视角
                </small>
            </div>
        `;

        lightfieldPreview.innerHTML = previewHTML;
    }

    generateLightfieldCameraPositions() {
        const gridSize = parseInt(document.getElementById('lightfieldGridSize').value);
        const spacingX = parseFloat(document.getElementById('lightfieldSpacingX').value);
        const spacingY = parseFloat(document.getElementById('lightfieldSpacingY').value);
        const centerX = parseFloat(document.getElementById('lightfieldCenterX').value);
        const centerY = parseFloat(document.getElementById('lightfieldCenterY').value);
        const distanceZ = parseFloat(document.getElementById('lightfieldDistanceZ').value);

        const positions = [];
        for (let i = 0; i < gridSize; i++) {
            for (let j = 0; j < gridSize; j++) {
                const x = centerX + (j - (gridSize - 1) / 2) * spacingX;
                const y = centerY + (i - (gridSize - 1) / 2) * spacingY;
                positions.push([x, y, distanceZ]);
            }
        }
        return positions;
    }


}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    // 延迟初始化，确保所有元素都已渲染
    setTimeout(() => {
        app = new RenderApp();
    }, 100);
});