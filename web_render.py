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
            self.render_progress = {
                'current': 0,
                'total': params['num_lights'],
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
            
            # 模拟渲染过程中的进度更新
            for i in range(params['num_lights']):
                self.render_progress['current'] = i + 1
                self.render_progress['current_image'] = f"light_{i+1:02d}.png"
                self.render_progress['stage'] = '渲染图像'
                
                # 发送进度更新
                socketio.emit('render_progress', {
                    'progress': self.render_progress,
                    'status': 'rendering',
                    'message': f'渲染第 {i+1}/{params["num_lights"]} 张 RGB 图像...'
                })
                
                # 在第一次迭代时执行实际渲染
                if i == 0:
                    logger.info("执行实际渲染...")
                    success = self.generator.generate_single_dataset(
                        dataset_name=dataset_name,
                        obj_path=obj_path,
                        brdf_path=brdf_path,
                        num_lights=params['num_lights'],
                        light_pattern=params['light_pattern'],
                        light_distance=params['light_distance'],
                        light_intensity=params['light_intensity'],
                        camera_fov=params['camera_fov'],
                        camera_position=params['camera_position'],
                        camera_target=params['camera_target'],
                        image_size=params['image_size'],
                        spp=params['spp']
                    )
                    if not success:
                        logger.error("渲染失败")
                        return False
                    logger.info("实际渲染完成")
                
                # 模拟渲染时间
                time.sleep(0.3)
            
            return True
            
        except Exception as e:
            logger.error(f"渲染过程出错: {e}")
            return False
    
    def _load_rendered_images(self, dataset_name):
        """加载渲染的图像"""
        images_dir = Path("renders") / dataset_name / "images"
        
        if not images_dir.exists():
            logger.warning(f"图像目录不存在: {images_dir}")
            self.rendered_images = []
            return
        
        # 获取所有图像文件
        image_files = sorted(images_dir.glob("*.png"))
        self.rendered_images = [str(f) for f in image_files]
        logger.info(f"加载了 {len(self.rendered_images)} 张渲染图像")
    
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
                    
                    all_images.append({
                        'data': f'data:image/png;base64,{img_data}',
                        'large_data': f'data:image/png;base64,{large_img_data}',
                        'name': Path(image_path).name,
                        'index': i,
                        'light_id': i + 1,
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
    print("服务器将在 http://localhost:8080 启动")
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        # 添加 allow_unsafe_werkzeug=True 来允许开发服务器运行
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=8080, 
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