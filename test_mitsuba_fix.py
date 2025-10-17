#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 Mitsuba 修复是否有效
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mitsuba_import():
    """测试 Mitsuba 导入和基本功能"""
    try:
        import mitsuba as mi
        mi.set_variant('scalar_rgb')
        logger.info(f"✓ Mitsuba {mi.__version__} 导入成功")
        
        # 测试创建简单场景
        scene_dict = {
            'type': 'scene',
            'integrator': {'type': 'direct'},  # 使用 direct 积分器
            'sensor': {
                'type': 'perspective',
                'fov': 45,
                'to_world': mi.ScalarTransform4f.look_at(
                    origin=[0, 0, 5],
                    target=[0, 0, 0],
                    up=[0, 1, 0]
                ),
                'film': {
                    'type': 'hdrfilm',
                    'width': 64,
                    'height': 64,
                }
            },
            'shape': {
                'type': 'sphere',
                'center': [0, 0, 0],
                'radius': 1.0,
                'bsdf': {
                    'type': 'diffuse',
                    'reflectance': {'type': 'rgb', 'value': [0.5, 0.5, 0.5]}
                }
            },
            'emitter': {
                'type': 'point',
                'position': [2, 2, 2],
                'intensity': {'type': 'rgb', 'value': [1.0, 1.0, 1.0]}
            }
        }
        
        scene = mi.load_dict(scene_dict)
        logger.info("✓ 场景创建成功")
        
        # 测试渲染
        image = mi.render(scene, spp=1)
        logger.info("✓ 渲染测试成功")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Mitsuba 导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Mitsuba 测试失败: {e}")
        return False

def test_dataset_generator():
    """测试数据集生成器导入"""
    try:
        from dataset_generator import PhotometricStereoDataGenerator
        generator = PhotometricStereoDataGenerator()
        logger.info("✓ 数据集生成器导入成功")
        return True
    except Exception as e:
        logger.error(f"✗ 数据集生成器导入失败: {e}")
        return False

def test_brdf_renderer():
    """测试 BRDF 渲染器导入"""
    try:
        from brdf_renderer import MitsubaBRDFRenderer
        logger.info("✓ BRDF 渲染器导入成功")
        return True
    except Exception as e:
        logger.error(f"✗ BRDF 渲染器导入失败: {e}")
        return False

if __name__ == "__main__":
    print("=== Mitsuba 修复验证 ===\n")
    
    tests = [
        ("Mitsuba 基本功能", test_mitsuba_import),
        ("数据集生成器", test_dataset_generator),
        ("BRDF 渲染器", test_brdf_renderer)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"测试 {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"=== 测试结果: {passed}/{total} 通过 ===")
    
    if passed == total:
        print("🎉 所有测试通过！修复成功。")
        print("\n现在可以尝试运行 render_gui.py:")
        print("python render_gui.py")
    else:
        print("❌ 仍有问题需要解决。")
        
        if passed == 0:
            print("\n建议:")
            print("1. 检查 Mitsuba 是否正确安装: pip install mitsuba")
            print("2. 或尝试安装预编译版本")
        else:
            print("\n部分功能正常，可以尝试运行但可能有问题。")