#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mitsuba 配置修复工具
检测可用的 Mitsuba 变体和积分器，并提供修复建议
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_mitsuba_variants():
    """检查可用的 Mitsuba 变体"""
    try:
        import mitsuba as mi
        logger.info(f"Mitsuba 版本: {mi.__version__}")
        
        # 测试不同的变体
        variants_to_test = [
            'scalar_rgb',
            'llvm_ad_rgb', 
            'cuda_ad_rgb',
            'scalar_spectral',
            'llvm_ad_spectral'
        ]
        
        available_variants = []
        
        for variant in variants_to_test:
            try:
                mi.set_variant(variant)
                available_variants.append(variant)
                logger.info(f"✓ 变体 {variant} 可用")
                
                # 测试积分器
                test_integrators(variant)
                
            except Exception as e:
                logger.warning(f"✗ 变体 {variant} 不可用: {e}")
        
        return available_variants
        
    except ImportError:
        logger.error("Mitsuba 未安装！请运行: pip install mitsuba")
        return []
    except Exception as e:
        logger.error(f"Mitsuba 检查失败: {e}")
        return []

def test_integrators(variant):
    """测试指定变体下的积分器"""
    import mitsuba as mi
    
    integrators_to_test = [
        'path',
        'direct',
        'ao',
        'moment',
        'field'
    ]
    
    logger.info(f"  测试变体 {variant} 的积分器:")
    
    for integrator in integrators_to_test:
        try:
            # 创建简单的测试场景
            scene_dict = {
                'type': 'scene',
                'integrator': {'type': integrator},
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
                }
            }
            
            scene = mi.load_dict(scene_dict)
            logger.info(f"    ✓ 积分器 {integrator} 可用")
            
        except Exception as e:
            logger.warning(f"    ✗ 积分器 {integrator} 不可用: {e}")

def get_recommended_config():
    """获取推荐的配置"""
    available_variants = check_mitsuba_variants()
    
    if not available_variants:
        logger.error("没有可用的 Mitsuba 变体！")
        return None
    
    # 推荐优先级
    preferred_variants = ['llvm_ad_rgb', 'cuda_ad_rgb', 'scalar_rgb']
    
    recommended_variant = None
    for variant in preferred_variants:
        if variant in available_variants:
            recommended_variant = variant
            break
    
    if not recommended_variant:
        recommended_variant = available_variants[0]
    
    logger.info(f"\n推荐配置:")
    logger.info(f"  变体: {recommended_variant}")
    logger.info(f"  积分器: direct (如果 path 不可用)")
    
    return {
        'variant': recommended_variant,
        'integrator': 'direct'  # 更兼容的积分器
    }

def create_fixed_config():
    """创建修复后的配置文件"""
    config = get_recommended_config()
    
    if not config:
        return False
    
    # 创建修复后的渲染器配置
    fixed_config = f'''
# Mitsuba 修复配置
# 使用此配置替换原有的 Mitsuba 初始化代码

import mitsuba as mi

# 推荐的变体设置
RECOMMENDED_VARIANT = "{config['variant']}"
RECOMMENDED_INTEGRATOR = "{config['integrator']}"

try:
    mi.set_variant(RECOMMENDED_VARIANT)
    print(f"成功设置 Mitsuba 变体: {{RECOMMENDED_VARIANT}}")
except Exception as e:
    print(f"设置变体失败: {{e}}")
    # 回退到默认变体
    try:
        mi.set_variant('scalar_rgb')
        print("回退到 scalar_rgb 变体")
    except:
        raise Exception("无法设置任何 Mitsuba 变体")

# 在场景配置中使用推荐的积分器
# 将 'integrator': {{'type': 'path'}} 替换为:
# 'integrator': {{'type': RECOMMENDED_INTEGRATOR}}
'''
    
    with open('mitsuba_config_fix.py', 'w', encoding='utf-8') as f:
        f.write(fixed_config)
    
    logger.info("已创建修复配置文件: mitsuba_config_fix.py")
    return True

if __name__ == "__main__":
    print("=== Mitsuba 配置检查工具 ===\n")
    
    if create_fixed_config():
        print("\n=== 修复建议 ===")
        print("1. 查看生成的 mitsuba_config_fix.py 文件")
        print("2. 在渲染代码中将 'path' 积分器替换为 'direct'")
        print("3. 确保使用推荐的 Mitsuba 变体")
        print("\n具体修复步骤:")
        print("- 在 brdf_renderer.py 中找到 'integrator': 'path'")
        print("- 替换为 'integrator': 'direct'")
        print("- 在场景字典中将 {'type': 'path'} 替换为 {'type': 'direct'}")
    else:
        print("无法生成修复配置，请检查 Mitsuba 安装")