#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
光度立体数据集生成器
生成包含多光源图像、法线图和配置文件的完整数据集
"""

import os
import sys
import json
import yaml
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# 先设置 logging 配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import mitsuba as mi
    # 使用最兼容的变体
    mi.set_variant('scalar_rgb')
    MITSUBA_AVAILABLE = True
    logger.info("Mitsuba 3.7.1 加载成功，使用 scalar_rgb 变体")
except ImportError:
    MITSUBA_AVAILABLE = False
    logger.warning("Mitsuba未安装，无法生成渲染数据")
except Exception as e:
    MITSUBA_AVAILABLE = False
    logger.error(f"Mitsuba 初始化失败: {e}")

from brdf_renderer import MitsubaBRDFRenderer, LightingConfig, CameraConfig


class PhotometricStereoDataGenerator:
    """光度立体数据集生成器"""
    
    def __init__(self, 
                 output_base_dir: str = "renders",
                 brdf_dir: str = "brdfs",
                 obj_dir: str = "objects"):
        self.output_base_dir = Path(output_base_dir)
        self.brdf_dir = Path(brdf_dir)
        self.obj_dir = Path(obj_dir)
        
        if MITSUBA_AVAILABLE:
            self.renderer = MitsubaBRDFRenderer(
                brdf_dir=str(brdf_dir),
                output_dir=str(output_base_dir),
                obj_dir=str(obj_dir)
            )
        else:
            self.renderer = None
    
    def generate_light_positions(self, 
                                num_lights: int = 4,
                                distance: float = 1.0,
                                pattern: str = "hemisphere") -> List[Tuple[float, float, float]]:
        """
        生成光源位置
        
        Args:
            num_lights: 光源数量
            distance: 光源距离
            pattern: 分布模式 ("hemisphere", "circle", "grid")
            
        Returns:
            光源位置列表
        """
        positions = []
        
        if pattern == "hemisphere":
            # 半球均匀分布
            for i in range(num_lights):
                theta = np.arccos(1 - (i + 0.5) / num_lights)  # 极角
                phi = np.pi * (1 + 5**0.5) * i  # 黄金角
                
                x = distance * np.sin(theta) * np.cos(phi)
                y = distance * np.sin(theta) * np.sin(phi)
                z = distance * np.cos(theta)
                
                positions.append((float(x), float(y), float(z)))
        
        elif pattern == "circle":
            # 圆形分布（固定高度）
            z = distance * 0.7  # 固定高度
            radius = distance * 0.7
            
            for i in range(num_lights):
                angle = 2 * np.pi * i / num_lights
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                positions.append((float(x), float(y), float(z)))
        
        elif pattern == "grid":
            # 网格分布
            grid_size = int(np.ceil(np.sqrt(num_lights)))
            for i in range(num_lights):
                row = i // grid_size
                col = i % grid_size
                
                x = (col - grid_size/2 + 0.5) * distance / grid_size
                y = (row - grid_size/2 + 0.5) * distance / grid_size
                z = distance
                
                positions.append((float(x), float(y), float(z)))
        
        return positions

    
    def create_dataset_config(self,
                            light_positions: List[Tuple[float, float, float]],
                            dataset_name: str,
                            image_size: Tuple[int, int] = (256, 256),
                            focal_length: float = 500.0) -> Dict:
        """
        创建数据集配置
        
        Args:
            light_positions: 光源位置列表
            dataset_name: 数据集名称
            image_size: 图像尺寸
            focal_length: 焦距
            
        Returns:
            配置字典
        """
        width, height = image_size
        cx, cy = width / 2, height / 2
        
        config = {
            'camera': {
                'intrinsic_matrix': {
                    'fx': focal_length,
                    'fy': focal_length,
                    'cx': cx,
                    'cy': cy
                }
            },
            'lights': {
                'count': len(light_positions),
                'positions': {},
                'intensities': {}
            },
            'reconstruction': {
                'input_images': [],
                'ground_truth_normal': f"{dataset_name}\\images\\ground_truth_normal.png",
                'output_normal_map': f"{dataset_name}\\output\\normal_map.png",
                'mask_threshold': 0.1,
                'shadow_threshold': 0.05,
                'hog_regularization': {
                    'enabled': False,
                    'lambda': 0.2,
                    'orientations': 9,
                    'pixels_per_cell': (8, 8),
                    'cells_per_block': (2, 2)
                }
            }
        }
        
        # 添加光源信息
        for i, pos in enumerate(light_positions, 1):
            light_name = f"light_{i}"
            config['lights']['positions'][light_name] = list(pos)
            config['lights']['intensities'][light_name] = 1.0
            config['reconstruction']['input_images'].append(
                f"{dataset_name}\\images\\{light_name}.png"
            )
        
        return config
    
    def _load_brdf_albedo(self, brdf_path: str) -> float:
        """
        从 BRDF 文件中提取平均反射率（亮度）
        
        注意：MERL BRDF 数据库是灰度的，不包含颜色信息
        
        Args:
            brdf_path: BRDF 文件路径
            
        Returns:
            平均反射率 (0-1)
        """
        try:
            import struct
            with open(brdf_path, 'rb') as f:
                # 读取维度
                dims = struct.unpack('3i', f.read(12))
                total_points = dims[0] * dims[1] * dims[2]
                
                # 读取 BRDF 数据（只读取一个通道即可，因为是灰度的）
                brdf_bytes = f.read(total_points * 3 * 8)
                brdf_flat = struct.unpack(f'{total_points * 3}d', brdf_bytes)
                brdf_data = np.array(brdf_flat).reshape(dims[0], dims[1], dims[2], 3)
                
                # 不应用缩放因子，使用原始数据
                brdf_data = np.maximum(brdf_data, 0.0)
                
                # 计算平均反射率（使用中等角度的数据）
                start_idx = dims[0] // 4
                end_idx = dims[0] * 3 // 4
                mid_data = brdf_data[start_idx:end_idx, start_idx:end_idx, :, 0]  # 只用R通道
                
                # 计算平均值并归一化
                mean_albedo = mid_data.mean()
                
                # 归一化到 0.5-0.9 范围（提高最小值以确保可见性）
                # MERL 数据范围很大，需要对数缩放
                if mean_albedo > 0:
                    # 使用对数缩放
                    log_albedo = np.log10(mean_albedo + 1)
                    normalized = np.clip(log_albedo / 5.0, 0.5, 0.9)
                else:
                    normalized = 0.7
                
                logger.info(f"从 BRDF 提取反射率: {Path(brdf_path).name} -> {normalized:.3f}")
                return float(normalized)
                
        except Exception as e:
            logger.warning(f"无法从 BRDF 提取反射率 {brdf_path}: {e}")
            return 0.7
    
    def _create_simple_material(self, brdf_name: str, brdf_path: str = None) -> Dict:
        """
        创建简单材质（根据名称选择颜色，从 BRDF 提取亮度）
        
        Args:
            brdf_name: BRDF文件名
            brdf_path: BRDF文件路径（可选）
            
        Returns:
            材质字典
        """
        brdf_lower = brdf_name.lower()
        
        # 从 BRDF 文件加载反射率（亮度）
        albedo = 0.7  # 默认值
        if brdf_path and Path(brdf_path).exists():
            albedo = self._load_brdf_albedo(brdf_path)
        
        # 检测是否为纯金属（排除金属漆等涂层材质）
        pure_metal_keywords = ['steel', 'brass', 'chrome', 'alumin', 'silver', 'copper', 'nickel']
        is_pure_metal = any(kw in brdf_lower for kw in pure_metal_keywords)
        
        # 金属漆等涂层材质应该使用漫反射
        is_paint = 'paint' in brdf_lower or 'coat' in brdf_lower
        
        if is_pure_metal and not is_paint:
            # 根据名称选择金属类型和颜色
            # 注意：只能使用 material 或 (eta, k)，不能同时使用
            if 'gold' in brdf_lower:
                # 金色 - 使用预定义材质
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Au'
                }
            elif 'silver' in brdf_lower:
                # 银色
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Ag'
                }
            elif 'copper' in brdf_lower:
                # 铜色
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Cu'
                }
            elif 'alumin' in brdf_lower:
                # 铝色
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Al'
                }
            elif 'chrome' in brdf_lower:
                # 铬色
                return {
                    'type': 'roughconductor',
                    'alpha': 0.05,
                    'material': 'Cr'
                }
            elif 'brass' in brdf_lower:
                # 黄铜色 - 使用自定义 eta/k
                return {
                    'type': 'roughconductor',
                    'alpha': 0.15,
                    'eta': {'type': 'rgb', 'value': [0.618, 0.425, 0.206]},
                    'k': {'type': 'rgb', 'value': [3.580, 2.376, 1.560]}
                }
            elif 'nickel' in brdf_lower:
                # 镍色
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Ni'
                }
            else:
                # 默认铝
                return {
                    'type': 'roughconductor',
                    'alpha': 0.1,
                    'material': 'Al'
                }
        else:
            # 非金属材质（包括漆面、织物等）- 根据名称选择基础颜色，用 BRDF 反射率调整亮度
            if 'red' in brdf_lower or 'brick' in brdf_lower:
                base_color = np.array([1.0, 0.2, 0.2])  # 红色
            elif 'blue' in brdf_lower:
                base_color = np.array([0.2, 0.4, 1.0])  # 蓝色
            elif 'green' in brdf_lower:
                base_color = np.array([0.2, 1.0, 0.3])  # 绿色
            elif 'yellow' in brdf_lower:
                base_color = np.array([1.0, 1.0, 0.2])  # 黄色
            elif 'orange' in brdf_lower:
                base_color = np.array([1.0, 0.5, 0.1])  # 橙色
            elif 'purple' in brdf_lower or 'violet' in brdf_lower:
                base_color = np.array([0.8, 0.2, 1.0])  # 紫色
            elif 'pink' in brdf_lower:
                base_color = np.array([1.0, 0.4, 0.6])  # 粉色
            elif 'brown' in brdf_lower or 'wood' in brdf_lower:
                base_color = np.array([0.8, 0.5, 0.3])  # 棕色
            elif 'aventurine' in brdf_lower or 'aventurnine' in brdf_lower:
                base_color = np.array([0.3, 0.8, 0.5])  # 东陵石绿色
            elif 'pearl' in brdf_lower:
                base_color = np.array([1.0, 1.0, 0.9])  # 珍珠白
            elif 'gold' in brdf_lower:
                base_color = np.array([1.0, 0.8, 0.2])  # 金色
            elif 'beige' in brdf_lower:
                base_color = np.array([0.9, 0.85, 0.7])  # 米色
            elif 'white' in brdf_lower:
                base_color = np.array([1.0, 1.0, 1.0])  # 白色
            elif 'black' in brdf_lower:
                base_color = np.array([0.3, 0.3, 0.3])  # 黑色（提高亮度以确保可见性）
            else:
                # 默认中性色
                base_color = np.array([0.8, 0.8, 0.8])
            
            # 用 BRDF 反射率调整颜色亮度
            color = (base_color * albedo).tolist()
            
            return {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': color
                }
            }
    
    def render_light_images(self,
                          obj_path: str,
                          brdf_path: str,
                          light_positions: List[Tuple[float, float, float]],
                          output_dir: Path,
                          image_size: Tuple[int, int] = (256, 256),
                          spp: int = 64,
                          light_intensity: float = 50.0,
                          camera_fov: float = 45.0,
                          camera_position: Tuple[float, float, float] = (0, 0, 5),
                          camera_target: Tuple[float, float, float] = (0, 0, 0)) -> bool:
        """
        渲染多光源图像
        
        Args:
            obj_path: OBJ文件路径
            brdf_path: BRDF文件路径
            light_positions: 光源位置列表
            output_dir: 输出目录
            image_size: 图像尺寸
            spp: 采样数
            light_intensity: 光源强度
            camera_fov: 相机视场角
            camera_position: 相机位置
            camera_target: 相机目标点
            
        Returns:
            是否成功
        """
        if not MITSUBA_AVAILABLE:
            logger.error("Mitsuba不可用，无法渲染")
            return False
        
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建简单材质（传入 BRDF 路径以提取真实颜色）
        brdf_name = Path(brdf_path).stem
        material = self._create_simple_material(brdf_name, brdf_path)
        
        # 渲染每个光源
        for i, light_pos in enumerate(light_positions, 1):
            light_name = f"light_{i}"
            output_path = images_dir / f"{light_name}.png"
            
            logger.info(f"渲染光源 {i}/{len(light_positions)}: {light_name}")
            
            try:
                # 创建场景
                scene_dict = {
                    'type': 'scene',
                    'integrator': {'type': 'direct'},
                    'sensor': {
                        'type': 'perspective',
                        'fov': camera_fov,
                        'to_world': mi.ScalarTransform4f().look_at(
                            mi.ScalarPoint3f(list(camera_position)),
                            mi.ScalarPoint3f(list(camera_target)),
                            mi.ScalarPoint3f([0, 1, 0])
                        ),
                        'film': {
                            'type': 'hdrfilm',
                            'width': image_size[0],
                            'height': image_size[1],
                            'rfilter': {'type': 'gaussian'}
                        }
                    },
                    'light': {
                        'type': 'point',
                        'position': list(light_pos),
                        'intensity': {'type': 'rgb', 'value': light_intensity}
                    }
                }
                
                # 直接加载 OBJ 文件
                if Path(obj_path).exists():
                    scene_dict['object'] = {
                        'type': 'obj',
                        'filename': str(obj_path),
                        'bsdf': material
                    }
                else:
                    # 如果文件不存在，使用默认球体
                    scene_dict['object'] = {
                        'type': 'sphere',
                        'center': [0, 0, 0],
                        'radius': 1.0,
                        'bsdf': material
                    }
                
                # 渲染
                scene = mi.load_dict(scene_dict)
                image = mi.render(scene, spp=spp)
                
                # 保存
                mi.util.write_bitmap(str(output_path), image)
                logger.info(f"✓ 渲染成功: {light_name}")
                
            except Exception as e:
                logger.error(f"渲染失败 {light_name}: {e}")
                return False
        
        return True
    
    def render_normal_map(self,
                        obj_path: str,
                        output_path: Path,
                        image_size: Tuple[int, int] = (256, 256),
                        spp: int = 64,
                        camera_fov: float = 45.0,
                        camera_position: Tuple[float, float, float] = (0, 0, 5),
                        camera_target: Tuple[float, float, float] = (0, 0, 0)) -> bool:
        """
        渲染法线图
        
        Args:
            obj_path: OBJ文件路径
            output_path: 输出路径
            image_size: 图像尺寸
            spp: 采样数
            camera_fov: 相机视场角
            camera_position: 相机位置
            camera_target: 相机目标点
            
        Returns:
            是否成功
        """
        if not MITSUBA_AVAILABLE:
            logger.error("Mitsuba不可用，无法渲染法线图")
            return False
        
        try:
            # 创建法线渲染场景
            scene_dict = {
                'type': 'scene',
                'integrator': {
                    'type': 'aov',
                    'aovs': 'sh_normal:sh_normal'
                },
                'sensor': {
                    'type': 'perspective',
                    'fov': camera_fov,
                    'to_world': mi.ScalarTransform4f().look_at(
                        mi.ScalarPoint3f(list(camera_position)),
                        mi.ScalarPoint3f(list(camera_target)),
                        mi.ScalarPoint3f([0, 1, 0])
                    ),
                    'film': {
                        'type': 'hdrfilm',
                        'width': image_size[0],
                        'height': image_size[1],
                        'rfilter': {'type': 'gaussian'}
                    }
                }
            }
            
            # 直接加载 OBJ 文件
            if Path(obj_path).exists():
                scene_dict['object'] = {
                    'type': 'obj',
                    'filename': str(obj_path),
                    'bsdf': {'type': 'diffuse', 'reflectance': 0.8}
                }
            else:
                # 如果文件不存在，使用默认球体
                scene_dict['object'] = {
                    'type': 'sphere',
                    'center': [0, 0, 0],
                    'radius': 1.0,
                    'bsdf': {'type': 'diffuse', 'reflectance': 0.8}
                }
            
            # 渲染
            scene = mi.load_dict(scene_dict)
            image = mi.render(scene, spp=spp)
            
            # 保存法线图
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mi.util.write_bitmap(str(output_path), image)
            
            logger.info(f"法线图渲染完成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"法线图渲染失败: {e}")
            return False

    
    def generate_single_dataset(self,
                              dataset_name: str,
                              obj_path: str,
                              brdf_path: str,
                              num_lights: int = 4,
                              light_pattern: str = "hemisphere",
                              light_distance: float = 2.0,
                              light_intensity: float = 50.0,
                              camera_fov: float = 45.0,
                              camera_position: Tuple[float, float, float] = (0, 0, 5),
                              camera_target: Tuple[float, float, float] = (0, 0, 0),
                              image_size: Tuple[int, int] = (256, 256),
                              spp: int = 64) -> bool:
        """
        生成单个数据集
        
        Args:
            dataset_name: 数据集名称
            obj_path: OBJ文件路径
            brdf_path: BRDF文件路径
            num_lights: 光源数量
            light_pattern: 光源分布模式
            light_distance: 光源距离
            light_intensity: 光源强度
            camera_fov: 相机视场角
            camera_position: 相机位置
            camera_target: 相机目标点
            image_size: 图像尺寸
            spp: 采样数
            
        Returns:
            是否成功
        """
        logger.info(f"开始生成数据集: {dataset_name}")
        
        # 创建数据集目录
        dataset_dir = self.output_base_dir / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        images_dir = dataset_dir / "images"
        output_dir = dataset_dir / "output"
        
        # 清理旧的图像文件（保留目录结构）
        if images_dir.exists():
            import shutil
            logger.info(f"清理旧的渲染结果: {images_dir}")
            shutil.rmtree(images_dir)
        
        images_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        
        # 生成光源位置
        light_positions = self.generate_light_positions(
            num_lights=num_lights,
            distance=light_distance,
            pattern=light_pattern
        )
        
        # 创建配置
        config = self.create_dataset_config(
            light_positions=light_positions,
            dataset_name=dataset_name,
            image_size=image_size
        )
        
        # 保存配置文件
        config_path = dataset_dir / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"配置文件已保存: {config_path}")
        
        # 渲染光源图像
        if not self.render_light_images(
            obj_path=obj_path,
            brdf_path=brdf_path,
            light_positions=light_positions,
            output_dir=dataset_dir,
            image_size=image_size,
            spp=spp,
            light_intensity=light_intensity,
            camera_fov=camera_fov,
            camera_position=camera_position,
            camera_target=camera_target
        ):
            logger.error(f"光源图像渲染失败: {dataset_name}")
            return False
        
        # 渲染法线图
        normal_map_path = images_dir / "ground_truth_normal.png"
        if not self.render_normal_map(
            obj_path=obj_path,
            output_path=normal_map_path,
            image_size=image_size,
            spp=spp,
            camera_fov=camera_fov,
            camera_position=camera_position,
            camera_target=camera_target
        ):
            logger.error(f"法线图渲染失败: {dataset_name}")
            return False
        
        logger.info(f"数据集生成完成: {dataset_name}")
        return True
    
    def generate_custom_dataset(self,
                              dataset_name: str,
                              obj_path: str,
                              brdf_path: str,
                              lights: List[Dict],
                              camera_fov: float = 45.0,
                              camera_position: Tuple[float, float, float] = (0, 0, 5),
                              camera_target: Tuple[float, float, float] = (0, 0, 0),
                              image_size: Tuple[int, int] = (256, 256),
                              spp: int = 64) -> bool:
        """
        使用自定义光源生成数据集
        
        Args:
            dataset_name: 数据集名称
            obj_path: OBJ文件路径
            brdf_path: BRDF文件路径
            lights: 光源列表，每个光源包含 position 和 intensity
            camera_fov: 相机视场角
            camera_position: 相机位置
            camera_target: 相机目标点
            image_size: 图像尺寸
            spp: 采样数
            
        Returns:
            是否成功
        """
        logger.info(f"开始生成自定义数据集: {dataset_name}")
        logger.info(f"光源数量: {len(lights)}")
        
        # 创建数据集目录
        dataset_dir = self.output_base_dir / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        images_dir = dataset_dir / "images"
        output_dir = dataset_dir / "output"
        
        # 清理旧的图像文件（保留目录结构）
        if images_dir.exists():
            import shutil
            logger.info(f"清理旧的渲染结果: {images_dir}")
            shutil.rmtree(images_dir)
        
        images_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        
        # 创建配置（支持不同类型的光源）
        config = {
            'dataset_name': dataset_name,
            'image_size': list(image_size),
            'num_lights': len(lights),
            'lights': [
                {
                    'type': light.get('type', 'point'),
                    'position': light.get('position'),
                    'direction': light.get('direction'),
                    'intensity': light['intensity']
                }
                for light in lights
            ],
            'camera': {
                'fov': camera_fov,
                'position': list(camera_position),
                'target': list(camera_target)
            }
        }
        
        # 保存配置文件
        config_path = dataset_dir / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"配置文件已保存: {config_path}")
        
        # 渲染每个光源的图像
        for i, light in enumerate(lights):
            light_name = f"light_{i+1}"
            output_path = images_dir / f"{light_name}.png"
            
            logger.info(f"渲染光源 {i+1}/{len(lights)}: {light}")
            
            if not self._render_single_light_image(
                obj_path=obj_path,
                brdf_path=brdf_path,
                light_config=light,
                output_path=output_path,
                image_size=image_size,
                spp=spp,
                camera_fov=camera_fov,
                camera_position=camera_position,
                camera_target=camera_target
            ):
                logger.error(f"光源 {i+1} 渲染失败")
                return False
        
        # 渲染法线图
        normal_map_path = images_dir / "ground_truth_normal.png"
        if not self.render_normal_map(
            obj_path=obj_path,
            output_path=normal_map_path,
            image_size=image_size,
            spp=spp,
            camera_fov=camera_fov,
            camera_position=camera_position,
            camera_target=camera_target
        ):
            logger.error(f"法线图渲染失败: {dataset_name}")
            return False
        
        logger.info(f"自定义数据集生成完成: {dataset_name}")
        return True
    
    def _render_single_light_image(self,
                                   obj_path: str,
                                   brdf_path: str,
                                   light_config: Dict,
                                   output_path: Path,
                                   image_size: Tuple[int, int],
                                   spp: int,
                                   camera_fov: float,
                                   camera_position: Tuple[float, float, float],
                                   camera_target: Tuple[float, float, float]) -> bool:
        """渲染单个光源的图像"""
        try:
            # 打印调试信息
            logger.info(f"渲染参数:")
            logger.info(f"  相机位置: {camera_position}")
            logger.info(f"  相机目标: {camera_target}")
            logger.info(f"  光源配置: {light_config}")
            
            # 加载材质
            brdf_name = Path(brdf_path).stem
            material = self._create_simple_material(brdf_name, brdf_path)
            
            # 根据光源类型构建光源配置
            light_type = light_config.get('type', 'point')
            light_intensity = light_config.get('intensity', 100.0)
            
            if light_type == 'point':
                if 'position' not in light_config:
                    logger.error(f"点光源缺少position字段: {light_config}")
                    return False
                light_dict = {
                    'type': 'point',
                    'position': light_config['position'],
                    'intensity': {'type': 'rgb', 'value': light_intensity * 2.0}
                }
            elif light_type == 'directional':
                if 'direction' not in light_config:
                    logger.error(f"平行光缺少direction字段: {light_config}")
                    return False
                    
                # 平行光：使用很远的点光源来模拟
                direction = light_config['direction']
                logger.info(f"平行光方向: {direction}")
                
                # 将方向向量放大到很远的距离来模拟平行光
                distance = 100.0  # 很远的距离
                far_position = [d * distance for d in direction]
                
                light_dict = {
                    'type': 'point',
                    'position': far_position,
                    'intensity': {'type': 'rgb', 'value': light_intensity * 10.0}  # 增加强度补偿距离
                }
            else:
                logger.error(f"不支持的光源类型: {light_type}")
                return False
            
            # 构建场景
            scene_dict = {
                'type': 'scene',
                'integrator': {
                    'type': 'path',
                    'max_depth': 8
                },
                'sensor': {
                    'type': 'perspective',
                    'fov': camera_fov,
                    'to_world': mi.ScalarTransform4f().look_at(
                        mi.ScalarPoint3f(list(camera_position)),
                        mi.ScalarPoint3f(list(camera_target)),
                        mi.ScalarPoint3f([0, 1, 0])
                    ),
                    'film': {
                        'type': 'hdrfilm',
                        'width': image_size[0],
                        'height': image_size[1],
                        'rfilter': {'type': 'gaussian'}
                    }
                },
                'light': light_dict
            }
            
            # 直接加载 OBJ 文件
            if Path(obj_path).exists():
                scene_dict['object'] = {
                    'type': 'obj',
                    'filename': str(obj_path),
                    'bsdf': material
                }
            else:
                # 如果文件不存在，使用默认球体
                scene_dict['object'] = {
                    'type': 'sphere',
                    'center': [0, 0, 0],
                    'radius': 1.0,
                    'bsdf': material
                }
            
            # 渲染
            scene = mi.load_dict(scene_dict)
            image = mi.render(scene, spp=spp)
            
            # 保存
            mi.util.write_bitmap(str(output_path), image)
            logger.info(f"✓ 渲染成功: {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            return False
    
    def generate_batch_datasets(self,
                              obj_files: List[str],
                              brdf_files: List[str],
                              num_lights: int = 4,
                              light_pattern: str = "hemisphere",
                              image_size: Tuple[int, int] = (256, 256),
                              spp: int = 64,
                              max_datasets: int = None) -> Dict[str, bool]:
        """
        批量生成数据集
        
        Args:
            obj_files: OBJ文件列表
            brdf_files: BRDF文件列表
            num_lights: 光源数量
            light_pattern: 光源分布模式
            image_size: 图像尺寸
            spp: 采样数
            max_datasets: 最大数据集数量
            
        Returns:
            生成结果字典 {dataset_name: success}
        """
        results = {}
        count = 0
        
        for obj_file in obj_files:
            obj_name = Path(obj_file).stem
            
            for brdf_file in brdf_files:
                brdf_name = Path(brdf_file).stem
                
                # 检查是否达到最大数量
                if max_datasets and count >= max_datasets:
                    logger.info(f"已达到最大数据集数量: {max_datasets}")
                    return results
                
                # 生成数据集名称
                dataset_name = f"{obj_name}_{brdf_name}_data"
                
                # 生成数据集
                success = self.generate_single_dataset(
                    dataset_name=dataset_name,
                    obj_path=obj_file,
                    brdf_path=brdf_file,
                    num_lights=num_lights,
                    light_pattern=light_pattern,
                    image_size=image_size,
                    spp=spp
                )
                
                results[dataset_name] = success
                count += 1
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='光度立体数据集生成器',
        epilog='''
使用示例:
  生成单个数据集:
    python dataset_generator.py --single sphere,aluminium --num-lights 4
  
  批量生成:
    python dataset_generator.py --obj-files sphere cube --brdf-files aluminium brass
  
  快速测试:
    python generate_sample_dataset.py
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--obj-dir', default='objects', help='OBJ文件目录')
    parser.add_argument('--brdf-dir', default='brdfs', help='BRDF文件目录')
    parser.add_argument('--output-dir', default='renders', help='输出目录')
    parser.add_argument('--obj-files', nargs='+', help='指定OBJ文件名（不含扩展名）')
    parser.add_argument('--brdf-files', nargs='+', help='指定BRDF文件名（不含扩展名）')
    parser.add_argument('--num-lights', type=int, default=4, help='光源数量')
    parser.add_argument('--light-pattern', choices=['hemisphere', 'circle', 'grid'],
                       default='hemisphere', help='光源分布模式')
    parser.add_argument('--image-size', type=int, nargs=2, default=[256, 256],
                       help='图像尺寸 (宽 高)')
    parser.add_argument('--spp', type=int, default=64, help='每像素采样数')
    parser.add_argument('--max-datasets', type=int, help='最大数据集数量')
    parser.add_argument('--single', help='生成单个数据集（格式: obj_name,brdf_name）')
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n提示: 使用 'python generate_sample_dataset.py' 快速生成示例数据集")
        return 0
    
    args = parser.parse_args()
    
    if not MITSUBA_AVAILABLE:
        print("错误: Mitsuba未安装")
        print("请运行: pip install mitsuba")
        return 1
    
    # 创建生成器
    generator = PhotometricStereoDataGenerator(
        output_base_dir=args.output_dir,
        brdf_dir=args.brdf_dir,
        obj_dir=args.obj_dir
    )
    
    # 单个数据集模式
    if args.single:
        try:
            obj_name, brdf_name = args.single.split(',')
            obj_path = Path(args.obj_dir) / f"{obj_name}.obj"
            brdf_path = Path(args.brdf_dir) / f"{brdf_name}.binary"
            
            if not obj_path.exists():
                print(f"错误: OBJ文件不存在: {obj_path}")
                return 1
            
            if not brdf_path.exists():
                print(f"错误: BRDF文件不存在: {brdf_path}")
                return 1
            
            dataset_name = f"{obj_name}_{brdf_name}_data"
            success = generator.generate_single_dataset(
                dataset_name=dataset_name,
                obj_path=str(obj_path),
                brdf_path=str(brdf_path),
                num_lights=args.num_lights,
                light_pattern=args.light_pattern,
                image_size=tuple(args.image_size),
                spp=args.spp
            )
            
            return 0 if success else 1
            
        except ValueError:
            print("错误: --single 参数格式错误，应为: obj_name,brdf_name")
            return 1
    
    # 批量生成模式
    obj_dir = Path(args.obj_dir)
    brdf_dir = Path(args.brdf_dir)
    
    # 查找OBJ文件
    if args.obj_files:
        obj_files = [str(obj_dir / f"{name}.obj") for name in args.obj_files]
    else:
        obj_files = [str(f) for f in obj_dir.glob("*.obj")]
    
    if not obj_files:
        print(f"错误: 未找到OBJ文件")
        return 1
    
    # 查找BRDF文件
    if args.brdf_files:
        brdf_files = [str(brdf_dir / f"{name}.binary") for name in args.brdf_files]
    else:
        brdf_files = [str(f) for f in brdf_dir.glob("*.binary")]
    
    if not brdf_files:
        print(f"错误: 未找到BRDF文件")
        return 1
    
    # 显示概览
    total_datasets = len(obj_files) * len(brdf_files)
    if args.max_datasets:
        total_datasets = min(total_datasets, args.max_datasets)
    
    print(f"\n数据集生成概览:")
    print(f"  OBJ文件: {len(obj_files)} 个")
    print(f"  BRDF材质: {len(brdf_files)} 个")
    print(f"  光源数量: {args.num_lights}")
    print(f"  光源模式: {args.light_pattern}")
    print(f"  图像尺寸: {args.image_size[0]}x{args.image_size[1]}")
    print(f"  采样数: {args.spp} spp")
    print(f"  总数据集: {total_datasets} 个")
    print(f"  输出目录: {args.output_dir}\n")
    
    # 确认
    try:
        response = input(f"确认生成 {total_datasets} 个数据集? (y/N): ")
        if response.lower() != 'y':
            print("取消生成")
            return 0
    except KeyboardInterrupt:
        print("\n取消生成")
        return 0
    
    # 批量生成
    results = generator.generate_batch_datasets(
        obj_files=obj_files,
        brdf_files=brdf_files,
        num_lights=args.num_lights,
        light_pattern=args.light_pattern,
        image_size=tuple(args.image_size),
        spp=args.spp,
        max_datasets=args.max_datasets
    )
    
    # 统计结果
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count
    
    print(f"\n=== 数据集生成完成 ===")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print(f"总计: {len(results)} 个")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
