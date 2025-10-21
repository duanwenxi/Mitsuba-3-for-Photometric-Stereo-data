#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web 版本的光度立体渲染器 - 最终版本
支持 RGB 渲染、进度显示和网格预览
"""

import os
import sys
import json
import base64
from pathlib import Path
from io import BytesIO
import threading
import logging
import time

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from PIL import Image
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'photometric_stereo_renderer'
socketio = SocketIO(app, cors_allowed_origins="*")

class WebRenderController:
    def __init__(self):
        self.generator = None  # 延迟初始化
        self.current_render_task = None
        self.rendered_images = []
        self.render_progress = {
            'current': 0,
            'total': 0,
            'current_image': '',
            'stage': ''
        }
        
    def get_available_files(self):
        """获取可用的 OBJ 和 BRDF 文件"""
        obj_files = []
        brdf_files = []
        
        obj_dir = Path("objects")
        if obj_dir.exists():
            obj_files = sorted([f.stem for f in obj_dir.glob("*.obj")])
        
        brdf_dir = Path("brdfs")
        if brdf_dir.exists():
            brdf_files = sorted([f.stem for f in brdf_dir.glob("*.binary")])
        
        logger.info(f"找到 {len(obj_files)} 个 OBJ 文件，{len(brdf_files)} 个 BRDF 文件")
        return obj_files, brdf_files
    
    def start_render(self, params):
        """开始渲染任务"""
        if self.current_render_task and self.current_render_task.is_alive():
            return False, "渲染任务正在进行中"
        
        logger.info(f"启动渲染任务: {params['obj_name']} + {params['brdf_name']}")
        
        self.current_render_task = threading.Thread(
            target=self._render_thread, 
            args=(params,)
        )
        self.current_render_task.daemon = True
        self.current_render_task.start()
        return True, "渲染任务已启动"
    
    def _render_thread(self, params):
        """渲染线程"""
        try:
            logger.info("渲染线程开始")
            
            # 初始化进度
            num_lights = len(params.get('lights', []))
            self.render_progress = {
                'current': 0,
                'total': num_lights,
                'current_image': '',
                'stage': '初始化'
            }
            
            socketio.emit('render_progress', {
                'progress': self.render_progress,
                'status': 'starting', 
                'message': '初始化渲染器...'
            })
            
            # 延迟初始化 Mitsuba 和生成器
            try:
                logger.info("初始化 Mitsuba...")
                import mitsuba as mi
                mi.set_variant('scalar_rgb')  # 确保使用 RGB 变体
                logger.info("成功设置 Mitsuba 变体: scalar_rgb")
                
                if self.generator is None:
                    from dataset_generator import PhotometricStereoDataGenerator
                    self.generator = PhotometricStereoDataGenerator()
                    logger.info("DatasetGenerator 初始化完成")
                    
            except Exception as e:
                logger.error(f"Mitsuba 初始化失败: {e}")
                socketio.emit('render_status', {'status': 'error', 'message': f'Mitsuba 初始化失败: {str(e)}'})
                return
            
            # 构建文件路径
            obj_path = str(Path("objects") / f"{params['obj_name']}.obj")
            brdf_path = str(Path("brdfs") / f"{params['brdf_name']}.binary")
            dataset_name = f"web_render_{params['obj_name']}_{params['brdf_name']}"
            
            logger.info(f"OBJ 路径: {obj_path}")
            logger.info(f"BRDF 路径: {brdf_path}")
            
            # 检查文件是否存在
            if not Path(obj_path).exists():
                socketio.emit('render_status', {'status': 'error', 'message': f'OBJ 文件不存在: {obj_path}'})
                return
            
            if not Path(brdf_path).exists():
                socketio.emit('render_status', {'status': 'error', 'message': f'BRDF 文件不存在: {brdf_path}'})
                return
            
            # 执行渲染，使用自定义的进度回调
            success = self._render_with_progress(obj_path, brdf_path, dataset_name, params)
            
            if success:
                # 加载渲染结果
                self.render_progress['stage'] = '加载结果'
                socketio.emit('render_progress', {
                    'progress': self.render_progress,
                    'status': 'loading', 
                    'message': '加载渲染结果...'
                })
                
                self._load_rendered_images(dataset_name)
                
                # 发送所有图像数据
                all_images = self._get_all_images_data()
                
                logger.info(f"渲染完成，生成了 {len(all_images)} 张图像")
                
                socketio.emit('render_complete', {
                    'status': 'completed',
                    'message': f'渲染完成！生成了 {len(all_images)} 张 RGB 图像',
                    'images': all_images,
                    'total': len(all_images)
                })
            else:
                socketio.emit('render_status', {'status': 'error', 'message': '渲染失败，请查看日志'})
                
        except Exception as e:
            logger.error(f"渲染出错: {e}")
            socketio.emit('render_status', {'status': 'error', 'message': f'渲染出错: {str(e)}'})
    
    def _render_with_progress(self, obj_path, brdf_path, dataset_name, params):
        """带进度回调的渲染"""
        try:
            logger.info("开始渲染过程")
            
            # 检查相机模式
            camera_mode = params.get('camera_mode', 'single')
            
            if camera_mode == 'lightfield':
                return self._render_lightfield_with_progress(obj_path, brdf_path, dataset_name, params)
            else:
                return self._render_single_camera_with_progress(obj_path, brdf_path, dataset_name, params)
            
        except Exception as e:
            logger.error(f"渲染过程出错: {e}")
            return False
    
    def _render_single_camera_with_progress(self, obj_path, brdf_path, dataset_name, params):
        """单相机渲染"""
        try:
            # 获取光源数量
            num_lights = len(params.get('lights', []))
            # 即使没有光源，也要渲染法线图
            total_tasks = max(num_lights, 1)  # 至少有一个任务（法线图）
            
            # 更新总任务数（光源图像 + 法线图）
            self.render_progress['total'] = total_tasks + 1  # +1 for normal map
            
            # 渲染光源图像（如果有光源的话）
            if num_lights > 0:
                for i in range(num_lights):
                    self.render_progress['current'] = i + 1
                    self.render_progress['current_image'] = f"light_{i+1:02d}.png"
                    self.render_progress['stage'] = '渲染光源图像'
                    
                    # 发送进度更新
                    socketio.emit('render_progress', {
                        'progress': self.render_progress,
                        'status': 'rendering',
                        'message': f'渲染第 {i+1}/{num_lights} 张光源图像...'
                    })
                    
                    # 在第一次迭代时执行实际渲染
                    if i == 0:
                        logger.info("执行光源图像渲染...")
                        success = self.generator.generate_custom_dataset(
                            dataset_name=dataset_name,
                            obj_path=obj_path,
                            brdf_path=brdf_path,
                            lights=params['lights'],
                            camera_fov=params['camera_fov'],
                            camera_position=params['camera_position'],
                            camera_target=params['camera_target'],
                            image_size=params['image_size'],
                            spp=params['spp']
                        )
                        if not success:
                            logger.error("光源图像渲染失败")
                            return False
                        logger.info("光源图像渲染完成")
                    
                    # 模拟渲染时间
                    time.sleep(0.3)
            
            # 渲染法线图
            self.render_progress['current'] = total_tasks + 1
            self.render_progress['current_image'] = "ground_truth_normal.png"
            self.render_progress['stage'] = '渲染法线图'
            
            socketio.emit('render_progress', {
                'progress': self.render_progress,
                'status': 'rendering',
                'message': '渲染法线图...'
            })
            
            # 如果没有光源，只渲染法线图
            if num_lights == 0:
                logger.info("没有光源，只渲染法线图...")
                success = self._render_normal_only(
                    obj_path=obj_path,
                    dataset_name=dataset_name,
                    camera_fov=params['camera_fov'],
                    camera_position=params['camera_position'],
                    camera_target=params['camera_target'],
                    image_size=params['image_size'],
                    spp=params['spp']
                )
                if not success:
                    logger.error("法线图渲染失败")
                    return False
                logger.info("法线图渲染完成")
            
            time.sleep(0.3)
            
            return True
            
        except Exception as e:
            logger.error(f"单相机渲染过程出错: {e}")
            return False
    
    def _render_lightfield_with_progress(self, obj_path, brdf_path, dataset_name, params):
        """光场相机渲染"""
        try:
            logger.info("开始光场相机渲染")
            
            # 获取光场配置
            lightfield_config = params.get('lightfield_config', {})
            grid_size = lightfield_config.get('grid_size', 3)
            spacing_x = lightfield_config.get('spacing_x', 0.5)
            spacing_y = lightfield_config.get('spacing_y', 0.5)
            center_pos = lightfield_config.get('center_position', [0, 0, 5])
            target_pos = lightfield_config.get('target_position', [0, 0, 0])
            
            # 生成相机位置
            camera_positions = []
            for i in range(grid_size):
                for j in range(grid_size):
                    x = center_pos[0] + (j - (grid_size - 1) / 2) * spacing_x
                    y = center_pos[1] + (i - (grid_size - 1) / 2) * spacing_y
                    z = center_pos[2]
                    camera_positions.append([x, y, z])
            
            num_cameras = len(camera_positions)
            num_lights = len(params.get('lights', []))
            
            # 计算总任务数：每个相机位置 × (光源数 + 法线图)
            tasks_per_camera = max(num_lights, 1) + 1  # 光源图像 + 法线图
            total_tasks = num_cameras * tasks_per_camera
            
            self.render_progress['total'] = total_tasks
            current_task = 0
            
            # 为每个相机位置渲染
            for cam_idx, camera_pos in enumerate(camera_positions):
                logger.info(f"渲染相机位置 {cam_idx + 1}/{num_cameras}: {camera_pos}")
                
                # 创建子数据集名称
                sub_dataset_name = f"{dataset_name}_cam_{cam_idx:02d}"
                
                # 渲染光源图像（如果有光源）
                if num_lights > 0:
                    for light_idx in range(num_lights):
                        current_task += 1
                        self.render_progress['current'] = current_task
                        self.render_progress['current_image'] = f"cam_{cam_idx:02d}_light_{light_idx+1:02d}.png"
                        self.render_progress['stage'] = f'渲染相机 {cam_idx+1} 光源图像'
                        
                        socketio.emit('render_progress', {
                            'progress': self.render_progress,
                            'status': 'rendering',
                            'message': f'相机 {cam_idx+1}/{num_cameras} - 光源 {light_idx+1}/{num_lights}'
                        })
                        
                        # 在第一个光源时执行实际渲染
                        if light_idx == 0:
                            success = self.generator.generate_custom_dataset(
                                dataset_name=sub_dataset_name,
                                obj_path=obj_path,
                                brdf_path=brdf_path,
                                lights=params['lights'],
                                camera_fov=params['camera_fov'],
                                camera_position=camera_pos,
                                camera_target=target_pos,
                                image_size=params['image_size'],
                                spp=params['spp']
                            )
                            if not success:
                                logger.error(f"相机 {cam_idx+1} 光源图像渲染失败")
                                return False
                        
                        time.sleep(0.1)
                
                # 渲染法线图
                current_task += 1
                self.render_progress['current'] = current_task
                self.render_progress['current_image'] = f"cam_{cam_idx:02d}_normal.png"
                self.render_progress['stage'] = f'渲染相机 {cam_idx+1} 法线图'
                
                socketio.emit('render_progress', {
                    'progress': self.render_progress,
                    'status': 'rendering',
                    'message': f'相机 {cam_idx+1}/{num_cameras} - 法线图'
                })
                
                # 如果没有光源，只渲染法线图
                if num_lights == 0:
                    success = self._render_normal_only(
                        obj_path=obj_path,
                        dataset_name=sub_dataset_name,
                        camera_fov=params['camera_fov'],
                        camera_position=camera_pos,
                        camera_target=target_pos,
                        image_size=params['image_size'],
                        spp=params['spp']
                    )
                    if not success:
                        logger.error(f"相机 {cam_idx+1} 法线图渲染失败")
                        return False
                
                time.sleep(0.1)
            
            # 合并所有相机的渲染结果到主数据集目录
            self._merge_lightfield_results(dataset_name, num_cameras)
            
            logger.info("光场相机渲染完成")
            return True
            
        except Exception as e:
            logger.error(f"光场相机渲染过程出错: {e}")
            return False
    
    def _merge_lightfield_results(self, dataset_name, num_cameras):
        """合并光场相机的渲染结果"""
        try:
            main_images_dir = Path("renders") / dataset_name / "images"
            main_images_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制所有子数据集的图像到主目录
            for cam_idx in range(num_cameras):
                sub_dataset_name = f"{dataset_name}_cam_{cam_idx:02d}"
                sub_images_dir = Path("renders") / sub_dataset_name / "images"
                
                if sub_images_dir.exists():
                    for image_file in sub_images_dir.glob("*.png"):
                        # 重命名文件以包含相机索引
                        new_name = f"cam_{cam_idx:02d}_{image_file.name}"
                        new_path = main_images_dir / new_name
                        
                        # 复制文件
                        import shutil
                        shutil.copy2(image_file, new_path)
                        logger.info(f"复制图像: {image_file} -> {new_path}")
            
            logger.info(f"光场结果合并完成: {main_images_dir}")
            
        except Exception as e:
            logger.error(f"合并光场结果失败: {e}")
    
    def _render_normal_only(self, obj_path, dataset_name, camera_fov, camera_position, camera_target, image_size, spp):
        """只渲染法线图"""
        try:
            # 创建数据集目录
            dataset_dir = Path("renders") / dataset_name
            images_dir = dataset_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # 渲染法线图
            normal_map_path = images_dir / "ground_truth_normal.png"
            success = self.generator.render_normal_map(
                obj_path=obj_path,
                output_path=normal_map_path,
                image_size=tuple(image_size),
                spp=spp,
                camera_fov=camera_fov,
                camera_position=tuple(camera_position),
                camera_target=tuple(camera_target)
            )
            
            return success
            
        except Exception as e:
            logger.error(f"法线图渲染失败: {e}")
            return False
    
    def _load_rendered_images(self, dataset_name):
        """加载渲染的图像（包含光源图像和法线图）"""
        images_dir = Path("renders") / dataset_name / "images"
        
        if not images_dir.exists():
            logger.warning(f"图像目录不存在: {images_dir}")
            self.rendered_images = []
            return
        
        # 加载所有图像文件
        all_files = list(images_dir.glob("*.png"))
        
        # 分类图像文件
        light_files = []
        normal_files = []
        
        for file in all_files:
            filename = file.name.lower()
            if 'normal' in filename:
                normal_files.append(file)
            elif 'light' in filename or 'cam_' in filename:
                light_files.append(file)
        
        # 排序文件
        light_files = sorted(light_files)
        normal_files = sorted(normal_files)
        
        # 合并所有图像文件
        self.rendered_images = [str(f) for f in light_files] + [str(f) for f in normal_files]
        
        logger.info(f"加载了 {len(light_files)} 张光源图像和 {len(normal_files)} 张法线图，总计 {len(self.rendered_images)} 张图像")
    
    def _get_all_images_data(self):
        """获取所有图像数据"""
        all_images = []
        
        logger.info(f"开始处理 {len(self.rendered_images)} 张图像")
        
        for i, image_path in enumerate(self.rendered_images):
            try:
                if not Path(image_path).exists():
                    logger.error(f"图像文件不存在: {image_path}")
                    continue
                
                with Image.open(image_path) as img:
                    # 确保是 RGB 模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 创建缩略图
                    thumbnail = img.copy()
                    thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)
                    
                    # 创建大图用于放大显示
                    large_img = img.copy()
                    large_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                    
                    # 转换为 Base64
                    buffer = BytesIO()
                    thumbnail.save(buffer, format='PNG')
                    img_data = base64.b64encode(buffer.getvalue()).decode()
                    
                    large_buffer = BytesIO()
                    large_img.save(large_buffer, format='PNG')
                    large_img_data = base64.b64encode(large_buffer.getvalue()).decode()
                    
                    # 判断图像类型
                    filename = Path(image_path).name.lower()
                    import re
                    
                    if 'normal' in filename:
                        image_type = 'normal'
                        # 检查是否是光场相机的法线图
                        cam_match = re.search(r'cam_(\d+)', filename)
                        if cam_match:
                            cam_id = int(cam_match.group(1)) + 1  # 从0开始转为从1开始
                            display_name = f'相机 {cam_id} - 法线图'
                            light_id = f'cam_{cam_id}'
                        else:
                            display_name = '法线图'
                            light_id = None
                    else:
                        image_type = 'light'
                        # 检查是否是光场相机的光源图像
                        cam_match = re.search(r'cam_(\d+)', filename)
                        light_match = re.search(r'light_(\d+)', filename)
                        
                        if cam_match and light_match:
                            cam_id = int(cam_match.group(1)) + 1  # 从0开始转为从1开始
                            light_num = int(light_match.group(1))
                            display_name = f'相机 {cam_id} - 光源 {light_num}'
                            light_id = f'cam_{cam_id}_light_{light_num}'
                        elif light_match:
                            light_num = int(light_match.group(1))
                            display_name = f'光源 {light_num}'
                            light_id = light_num
                        else:
                            display_name = f'光源 {i + 1}'
                            light_id = i + 1
                    
                    all_images.append({
                        'data': f'data:image/png;base64,{img_data}',
                        'large_data': f'data:image/png;base64,{large_img_data}',
                        'name': Path(image_path).name,
                        'display_name': display_name,
                        'index': i,
                        'light_id': light_id,
                        'type': image_type,
                        'size': thumbnail.size,
                        'original_size': img.size
                    })
                    
            except Exception as e:
                logger.error(f"加载图像 {image_path} 失败: {e}")
                continue
        
        logger.info(f"成功处理了 {len(all_images)} 张图像")
        return all_images

# 全局控制器实例
controller = WebRenderController()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/files')
def get_files():
    """获取可用文件列表"""
    obj_files, brdf_files = controller.get_available_files()
    return jsonify({
        'obj_files': obj_files,
        'brdf_files': brdf_files
    })

@app.route('/api/render', methods=['POST'])
def start_render():
    """启动渲染任务"""
    params = request.json
    logger.info(f"收到渲染请求: {params}")
    success, message = controller.start_render(params)
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/images')
def get_all_images():
    """获取所有渲染图像（用于调试）"""
    try:
        if not controller.rendered_images:
            return jsonify({
                'success': False,
                'message': '没有可用的渲染图像',
                'images': []
            })
        
        all_images = controller._get_all_images_data()
        return jsonify({
            'success': True,
            'message': f'找到 {len(all_images)} 张图像',
            'images': all_images,
            'total': len(all_images)
        })
    except Exception as e:
        logger.error(f"获取图像失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取图像失败: {str(e)}',
            'images': []
        })

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info('客户端已断开连接')

def main():
    """启动 Web 应用"""
    print("=== 光度立体渲染器 Web 版本 ===")
    print("功能特性:")
    print("- RGB 图像渲染")
    print("- 实时进度显示")
    print("- 网格预览模式")
    print("- 图像点击放大")
    print()
    
    # 检查必要的目录
    for dir_name in ['objects', 'brdfs', 'renders']:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ 目录 {dir_name}")
    
    print()
    print("服务器将在 http://localhost:8082 启动")
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        # 添加 allow_unsafe_werkzeug=True 来允许开发服务器运行
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=8082, 
            debug=False, 
            log_output=True,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == "__main__":
    main()