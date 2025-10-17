#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试数据集生成器
验证数据集生成功能是否正常工作
"""

import sys
from pathlib import Path
import yaml

def test_dataset_structure(dataset_path: Path) -> bool:
    """测试数据集结构是否完整"""
    print(f"\n检查数据集: {dataset_path.name}")
    
    # 检查目录结构
    required_dirs = ['images', 'output']
    for dir_name in required_dirs:
        dir_path = dataset_path / dir_name
        if not dir_path.exists():
            print(f"  ✗ 缺少目录: {dir_name}")
            return False
        print(f"  ✓ 目录存在: {dir_name}")
    
    # 检查配置文件
    config_path = dataset_path / 'config.yaml'
    if not config_path.exists():
        print(f"  ✗ 缺少配置文件: config.yaml")
        return False
    print(f"  ✓ 配置文件存在")
    
    # 读取配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查配置内容
        required_keys = ['camera', 'lights', 'reconstruction']
        for key in required_keys:
            if key not in config:
                print(f"  ✗ 配置缺少键: {key}")
                return False
        print(f"  ✓ 配置格式正确")
        
        # 检查光源数量
        num_lights = config['lights']['count']
        print(f"  ✓ 光源数量: {num_lights}")
        
        # 检查图像文件
        images_dir = dataset_path / 'images'
        
        # 检查光源图像
        for i in range(1, num_lights + 1):
            light_image = images_dir / f"light_{i}.jpg"
            if not light_image.exists():
                # 尝试PNG格式
                light_image = images_dir / f"light_{i}.png"
            
            if not light_image.exists():
                print(f"  ✗ 缺少光源图像: light_{i}")
                return False
        print(f"  ✓ 所有光源图像存在 ({num_lights}个)")
        
        # 检查法线图
        normal_map = images_dir / 'ground_truth_normal.png'
        if not normal_map.exists():
            print(f"  ✗ 缺少法线图: ground_truth_normal.png")
            return False
        print(f"  ✓ 法线图存在")
        
        return True
        
    except Exception as e:
        print(f"  ✗ 配置文件读取失败: {e}")
        return False


def main():
    print("=== 数据集生成器测试 ===")
    
    # 检查renders目录
    renders_dir = Path("renders")
    if not renders_dir.exists():
        print("\n错误: renders目录不存在")
        print("请先运行数据集生成器")
        return 1
    
    # 查找所有数据集
    datasets = [d for d in renders_dir.iterdir() if d.is_dir()]
    
    if not datasets:
        print("\n未找到任何数据集")
        print("请先运行: python generate_sample_dataset.py")
        return 1
    
    print(f"\n找到 {len(datasets)} 个数据集")
    
    # 测试每个数据集
    passed = 0
    failed = 0
    
    for dataset in datasets:
        if test_dataset_structure(dataset):
            passed += 1
        else:
            failed += 1
    
    # 总结
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print(f"总计: {len(datasets)} 个")
    
    if failed == 0:
        print("\n✓ 所有数据集结构完整!")
        return 0
    else:
        print(f"\n✗ {failed} 个数据集存在问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
