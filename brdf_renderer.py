#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mitsuba BRDF渲染器
使用MERL BRDF数据库对不同OBJ文件进行固定机位多光照渲染
"""

import os
import sys
import json
import struct
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import mitsuba as mi
    # 使用最兼容的变体
    mi.set_variant('scalar_rgb')
    MITSUBA_AVAILABLE = True
    logger.info(f"Mitsuba {mi.__version__} 加载成功，使用 scalar_rgb 变体")
except ImportError:
    MITSUBA_AVAILABLE = False
    logger.warning("Mitsuba未安装，请运行: pip install mitsuba")
except Exception as e:
    MITSUBA_AVAILABLE = False
    logger.error(f"Mitsuba 初始化失败: {e}")

class MERLBRDFLoader:
    """
    MERL BRDF数据加载器
    """
    
    def __init__(self):
        self.brdf_cache = {}
        
    def load_brdf(self, brdf_path: str) -> Optional[np.ndarray]:
        """
        加载MERL BRDF二进制文件
        
        Args:
            brdf_path: BRDF文件路径
            
        Returns:
            BRDF数据数组或None
        """
        if brdf_path in self.brdf_cache:
            return self.brdf_cache[brdf_path]
            
        try:
            with open(brdf_path, 'rb') as f:
                # 读取维度信息
                dims_data = f.read(3 * 4)
                dims = list(struct.unpack('3i', dims_data))
                
                # 验证维度
                expected_size = 90 * 90 * 180  # MERL标准维度
                actual_size = dims[0] * dims[1] * dims[2]
                
                if actual_size != expected_size:
                    logger.warning(f"BRDF维度不匹配: 期望{expected_size}, 实际{actual_size}")
                
                # 读取BRDF数据
                total_points = actual_size
                brdf_bytes = f.read(total_points * 3 * 8)  # 3通道，double类型8字节
                
                # 解析数据
                brdf_flat = struct.unpack(f'{total_points * 3}d', brdf_bytes)
                brdf_data = np.array(brdf_flat).reshape(dims[0], dims[1], dims[2], 3)
                
                # 应用MERL缩放因子
                scales = np.array([1.0/1500.0, 1.15/1500.0, 1.66/1500.0])
                brdf_data *= scales
                
                # 确保非负值
                brdf_data = np.maximum(brdf_data, 0.0)
                
                self.brdf_cache[brdf_path] = brdf_data
                logger.info(f"成功加载BRDF: {Path(brdf_path).name}")
                
                return brdf_data
                
        except Exception as e:
            logger.error(f"加载BRDF文件失败 {brdf_path}: {e}")
            return None

class LightingConfig:
    """
    光照配置类
    """
    
    def __init__(self, name: str, light_type: str, **kwargs):
        self.name = name
        self.light_type = light_type
        self.params = kwargs
    
    @staticmethod
    def create_preset_configs() -> List['LightingConfig']:
        """
        创建预设光照配置
        """
        configs = []
        
        # 1. 环境光照
        configs.append(LightingConfig(
            "ambient", "constant",
            radiance=0.3
        ))
        
        # 2. 顶部点光源
        configs.append(LightingConfig(
            "top_point", "point",
            position=[0, 5, 0],
            intensity=50.0
        ))
        
        # 3. 侧面方向光
        configs.append(LightingConfig(
            "side_directional", "directional",
            direction=[-1, -1, -1],
            irradiance=2.0
        ))
        
        # 4. 多点光源组合
        configs.append(LightingConfig(
            "multi_point", "multi_point",
            lights=[
                {"position": [2, 3, 2], "intensity": 20.0},
                {"position": [-2, 3, 2], "intensity": 20.0},
                {"position": [0, 3, -2], "intensity": 15.0}
            ]
        ))
        
        # 5. 环境贴图光照（如果有HDR环境贴图）
        configs.append(LightingConfig(
            "envmap", "envmap",
            filename="envmaps/studio.exr",  # 需要提供HDR环境贴图
            scale=1.0
        ))
        
        return configs

class CameraConfig:
    """
    相机配置类
    """
    
    def __init__(self, 
                 position: Tuple[float, float, float] = (0, 0, 5),
                 target: Tuple[float, float, float] = (0, 0, 0),
                 up: Tuple[float, float, float] = (0, 1, 0),
                 fov: float = 45.0,
                 width: int = 512,
                 height: int = 512):
        self.position = position
        self.target = target
        self.up = up
        self.fov = fov
        self.width = width
        self.height = height

class MitsubaBRDFRenderer:
    """
    Mitsuba BRDF渲染器主类
    """
    
    def __init__(self, 
                 brdf_dir: str = "brdfs",
                 output_dir: str = "renders",
                 obj_dir: str = "objects"):
        
        if not MITSUBA_AVAILABLE:
            raise ImportError("Mitsuba未安装，无法使用渲染功能")
            
        self.brdf_dir = Path(brdf_dir)
        self.output_dir = Path(output_dir)
        self.obj_dir = Path(obj_dir)
        
        # 创建输出目录
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化组件
        self.brdf_loader = MERLBRDFLoader()
        self.camera_config = CameraConfig()
        self.lighting_configs = LightingConfig.create_preset_configs()
        
        logger.info("Mitsuba BRDF渲染器初始化完成")
    
    def create_brdf_material(self, brdf_path: str, material_name: str) -> Optional[Dict]:
        """
        创建基于MERL BRDF的材质
        
        Args:
            brdf_path: BRDF文件路径
            material_name: 材质名称
            
        Returns:
            Mitsuba材质字典或None
        """
        brdf_data = self.brdf_loader.load_brdf(brdf_path)
        if brdf_data is None:
            logger.warning(f"BRDF数据加载失败，使用默认材质: {material_name}")
            return self._create_default_material()
        
        # 由于Mitsuba不直接支持MERL BRDF格式，我们分析BRDF特性并近似为标准材质
        return self._approximate_brdf_material(brdf_data, material_name)
    
    def _create_default_material(self) -> Dict:
        """创建默认材质"""
        return {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [0.8, 0.8, 0.8]
            }
        }
    
    def _approximate_brdf_material(self, brdf_data: np.ndarray, material_name: str) -> Dict:
        """
        将MERL BRDF近似为标准Mitsuba材质
        
        Args:
            brdf_data: BRDF数据
            material_name: 材质名称
            
        Returns:
            近似的Mitsuba材质字典
        """
        try:
            # 分析BRDF特性
            mean_reflectance = np.mean(brdf_data, axis=(0, 1, 2))
            max_reflectance = np.max(brdf_data, axis=(0, 1, 2))
            
            # 确保反射率在合理范围内
            mean_reflectance = np.clip(mean_reflectance, 0.0, 1.0)
            
            # 估算粗糙度（基于BRDF的峰值宽度）
            roughness = self._estimate_roughness(brdf_data)
            
            # 检测是否为金属材质
            is_metallic = self._detect_metallic(brdf_data, material_name)
            
            if is_metallic:
                # 金属材质 - 使用粗糙导体材质
                # 根据材质名称选择合适的金属类型
                metal_type = self._guess_metal_type(material_name)
                material = {
                    'type': 'roughconductor',
                    'alpha': roughness,
                    'material': metal_type  # 使用预定义的金属材质
                }
            else:
                # 非金属材质 - 使用漫反射材质
                material = {
                    'type': 'diffuse',
                    'reflectance': {
                        'type': 'rgb',
                        'value': mean_reflectance.tolist()
                    }
                }
            
            logger.info(f"材质近似完成: {material_name} -> {material['type']}")
            return material
            
        except Exception as e:
            logger.error(f"材质近似失败: {material_name} - {e}")
            return self._create_default_material()
    
    def _estimate_roughness(self, brdf_data: np.ndarray) -> float:
        """
        从BRDF数据估算表面粗糙度
        """
        # 分析镜面反射峰的宽度
        # 这是一个简化的估算方法
        peak_width = np.std(brdf_data)
        roughness = np.clip(peak_width * 10, 0.01, 1.0)
        return float(roughness)
    
    def _detect_metallic(self, brdf_data: np.ndarray, material_name: str) -> bool:
        """
        检测材质是否为金属
        """
        # 基于材质名称的简单检测
        metallic_keywords = ['metal', 'steel', 'brass', 'chrome', 'alumin', 'gold', 'silver', 'copper', 'nickel']
        name_lower = material_name.lower()
        
        return any(keyword in name_lower for keyword in metallic_keywords)
    
    def _guess_metal_type(self, material_name: str) -> str:
        """
        根据材质名称猜测金属类型
        """
        name_lower = material_name.lower()
        
        if 'gold' in name_lower:
            return 'Au'
        elif 'silver' in name_lower:
            return 'Ag'
        elif 'copper' in name_lower:
            return 'Cu'
        elif 'alumin' in name_lower:
            return 'Al'
        elif 'chrome' in name_lower:
            return 'Cr'
        else:
            return 'Al'  # 默认铝
    
    def create_lighting(self, lighting_config: LightingConfig) -> Dict:
        """
        根据配置创建光照
        
        Args:
            lighting_config: 光照配置
            
        Returns:
            Mitsuba光照字典
        """
        if lighting_config.light_type == "constant":
            return {
                'type': 'constant',
                'radiance': lighting_config.params.get('radiance', 1.0)
            }
        
        elif lighting_config.light_type == "point":
            return {
                'type': 'point',
                'position': lighting_config.params['position'],
                'intensity': lighting_config.params.get('intensity', 1.0)
            }
        
        elif lighting_config.light_type == "directional":
            return {
                'type': 'directional',
                'direction': lighting_config.params['direction'],
                'irradiance': lighting_config.params.get('irradiance', 1.0)
            }
        
        elif lighting_config.light_type == "envmap":
            envmap_path = lighting_config.params.get('filename')
            if envmap_path and Path(envmap_path).exists():
                return {
                    'type': 'envmap',
                    'filename': envmap_path,
                    'scale': lighting_config.params.get('scale', 1.0)
                }
            else:
                # 回退到常量光照
                return {'type': 'constant', 'radiance': 0.5}
        
        elif lighting_config.light_type == "multi_point":
            # 对于多点光源，返回第一个光源，其他的需要在场景中单独添加
            lights = lighting_config.params.get('lights', [])
            if lights:
                return {
                    'type': 'point',
                    'position': lights[0]['position'],
                    'intensity': lights[0]['intensity']
                }
        
        # 默认光照
        return {'type': 'constant', 'radiance': 1.0}
    
    def create_scene(self, 
                     obj_path: str, 
                     brdf_path: str, 
                     lighting_config: LightingConfig) -> Dict:
        """
        创建渲染场景
        
        Args:
            obj_path: OBJ文件路径
            brdf_path: BRDF文件路径
            lighting_config: 光照配置
            
        Returns:
            Mitsuba场景字典
        """
        # 创建材质
        material_name = Path(brdf_path).stem
        material = self.create_brdf_material(brdf_path, material_name)
        
        if material is None:
            # 使用默认材质
            material = {
                'type': 'diffuse',
                'reflectance': 0.8
            }
        
        # 创建场景字典
        scene_dict = {
            'type': 'scene',
            'integrator': {
                'type': 'direct'  # 使用直接光照积分器（更兼容）
            },
            'sensor': {
                'type': 'perspective',
                'fov': self.camera_config.fov,
                'to_world': mi.ScalarTransform4f().look_at(
                    mi.ScalarPoint3f(self.camera_config.position),
                    mi.ScalarPoint3f(self.camera_config.target),
                    mi.ScalarPoint3f(self.camera_config.up)
                ),
                'film': {
                    'type': 'hdrfilm',
                    'width': self.camera_config.width,
                    'height': self.camera_config.height,
                    'rfilter': {'type': 'gaussian'}
                }
            }
        }
        
        # 添加主光源
        scene_dict['light'] = self.create_lighting(lighting_config)
        
        # 添加多点光源（如果是多点光源配置）
        if lighting_config.light_type == "multi_point":
            lights = lighting_config.params.get('lights', [])
            for i, light_params in enumerate(lights[1:], 1):  # 跳过第一个（已作为主光源）
                scene_dict[f'light_{i}'] = {
                    'type': 'point',
                    'position': light_params['position'],
                    'intensity': light_params['intensity']
                }
        
        # 添加物体
        if Path(obj_path).exists():
            scene_dict['object'] = {
                'type': 'obj',
                'filename': obj_path,
                'bsdf': material
            }
        else:
            # 使用默认球体
            scene_dict['object'] = {
                'type': 'sphere',
                'center': [0, 0, 0],
                'radius': 1.0,
                'bsdf': material
            }
        
        return scene_dict
    
    def render_single(self, 
                      obj_path: str, 
                      brdf_path: str, 
                      lighting_config: LightingConfig,
                      output_path: str,
                      spp: int = 64) -> bool:
        """
        渲染单个场景
        
        Args:
            obj_path: OBJ文件路径
            brdf_path: BRDF文件路径
            lighting_config: 光照配置
            output_path: 输出文件路径
            spp: 每像素采样数
            
        Returns:
            渲染是否成功
        """
        try:
            # 创建场景
            scene_dict = self.create_scene(obj_path, brdf_path, lighting_config)
            scene = mi.load_dict(scene_dict)
            
            # 渲染
            image = mi.render(scene, spp=spp)
            
            # 保存图像
            mi.util.write_bitmap(output_path, image)
            
            logger.info(f"渲染完成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            return False
    
    def batch_render(self, 
                     obj_files: List[str], 
                     brdf_files: List[str] = None,
                     lighting_configs: List[LightingConfig] = None,
                     spp: int = 64) -> Dict[str, List[str]]:
        """
        批量渲染
        
        Args:
            obj_files: OBJ文件列表
            brdf_files: BRDF文件列表（如果为None，使用所有可用的BRDF）
            lighting_configs: 光照配置列表（如果为None，使用所有预设配置）
            spp: 每像素采样数
            
        Returns:
            渲染结果字典 {obj_name: [rendered_files]}
        """
        if brdf_files is None:
            brdf_files = list(self.brdf_dir.glob("*.binary"))
        
        if lighting_configs is None:
            lighting_configs = self.lighting_configs
        
        results = {}
        total_renders = len(obj_files) * len(brdf_files) * len(lighting_configs)
        current_render = 0
        
        for obj_file in obj_files:
            obj_name = Path(obj_file).stem
            results[obj_name] = []
            
            for brdf_file in brdf_files:
                brdf_name = Path(brdf_file).stem
                
                for lighting_config in lighting_configs:
                    current_render += 1
                    
                    # 生成输出文件名
                    output_filename = f"{obj_name}_{brdf_name}_{lighting_config.name}.png"
                    output_path = self.output_dir / output_filename
                    
                    logger.info(f"渲染进度 {current_render}/{total_renders}: {output_filename}")
                    
                    # 渲染
                    if self.render_single(obj_file, str(brdf_file), lighting_config, str(output_path), spp):
                        results[obj_name].append(str(output_path))
        
        return results
    
    def create_render_config(self, config_path: str = "render_config.json"):
        """
        创建渲染配置文件
        
        Args:
            config_path: 配置文件路径
        """
        config = {
            "camera": {
                "position": list(self.camera_config.position),
                "target": list(self.camera_config.target),
                "up": list(self.camera_config.up),
                "fov": self.camera_config.fov,
                "width": self.camera_config.width,
                "height": self.camera_config.height
            },
            "lighting": [
                {
                    "name": lc.name,
                    "type": lc.light_type,
                    "params": lc.params
                }
                for lc in self.lighting_configs
            ],
            "render": {
                "spp": 64,
                "integrator": "direct",
                "max_depth": 8
            },
            "paths": {
                "brdf_dir": str(self.brdf_dir),
                "obj_dir": str(self.obj_dir),
                "output_dir": str(self.output_dir)
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置文件已保存: {config_path}")

def main():
    """
    主函数 - 演示用法
    """
    print("=== Mitsuba BRDF渲染器 ===\n")
    
    if not MITSUBA_AVAILABLE:
        print("错误: Mitsuba未安装")
        print("请运行: pip install mitsuba")
        return
    
    # 创建渲染器
    renderer = MitsubaBRDFRenderer()
    
    # 创建配置文件
    renderer.create_render_config()
    
    # 示例：渲染单个场景
    print("示例渲染...")
    
    # 查找可用的BRDF文件
    brdf_files = list(renderer.brdf_dir.glob("*.binary"))
    if not brdf_files:
        print(f"错误: 在 {renderer.brdf_dir} 中未找到BRDF文件")
        return
    
    # 使用第一个BRDF文件进行测试
    test_brdf = brdf_files[0]
    test_lighting = renderer.lighting_configs[0]
    
    # 创建测试OBJ文件路径（如果不存在，将使用默认球体）
    test_obj = "test_sphere.obj"
    
    output_path = renderer.output_dir / "test_render.png"
    
    success = renderer.render_single(
        test_obj, 
        str(test_brdf), 
        test_lighting, 
        str(output_path)
    )
    
    if success:
        print(f"测试渲染成功: {output_path}")
    else:
        print("测试渲染失败")
    
    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()