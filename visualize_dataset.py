#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据集可视化工具
显示生成的光源图像和法线图
"""

import sys
import argparse
from pathlib import Path
import yaml

try:
    import cv2
    import numpy as np
    import matplotlib.pyplot as plt
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("警告: 缺少可视化库")
    print("请安装: pip install opencv-python matplotlib")


def visualize_dataset(dataset_path: Path, save_output: bool = False):
    """
    可视化数据集
    
    Args:
        dataset_path: 数据集路径
        save_output: 是否保存可视化结果
    """
    if not VISUALIZATION_AVAILABLE:
        print("错误: 可视化功能不可用")
        return False
    
    print(f"\n可视化数据集: {dataset_path.name}")
    
    # 读取配置
    config_path = dataset_path / 'config.yaml'
    if not config_path.exists():
        print("错误: 配置文件不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    num_lights = config['lights']['count']
    images_dir = dataset_path / 'images'
    
    # 读取图像
    light_images = []
    for i in range(1, num_lights + 1):
        # 尝试JPG格式
        img_path = images_dir / f"light_{i}.jpg"
        if not img_path.exists():
            # 尝试PNG格式
            img_path = images_dir / f"light_{i}.png"
        
        if img_path.exists():
            img = cv2.imread(str(img_path))
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                light_images.append(img)
        else:
            print(f"警告: 未找到光源图像 {i}")
    
    # 读取法线图
    normal_map_path = images_dir / 'ground_truth_normal.png'
    normal_map = None
    if normal_map_path.exists():
        normal_map = cv2.imread(str(normal_map_path))
        if normal_map is not None:
            normal_map = cv2.cvtColor(normal_map, cv2.COLOR_BGR2RGB)
    
    # 创建可视化
    if not light_images:
        print("错误: 未找到任何光源图像")
        return False
    
    # 计算布局
    total_images = len(light_images) + (1 if normal_map is not None else 0)
    cols = min(3, total_images)
    rows = (total_images + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4))
    if total_images == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if hasattr(axes, 'flatten') else axes
    
    # 显示光源图像
    for i, img in enumerate(light_images):
        axes[i].imshow(img)
        axes[i].set_title(f'Light {i+1}')
        axes[i].axis('off')
        
        # 显示光源位置
        light_pos = config['lights']['positions'][f'light_{i+1}']
        axes[i].text(0.5, -0.05, f'Pos: ({light_pos[0]:.2f}, {light_pos[1]:.2f}, {light_pos[2]:.2f})',
                    transform=axes[i].transAxes, ha='center', fontsize=8)
    
    # 显示法线图
    if normal_map is not None:
        axes[len(light_images)].imshow(normal_map)
        axes[len(light_images)].set_title('Ground Truth Normal Map')
        axes[len(light_images)].axis('off')
    
    # 隐藏多余的子图
    for i in range(total_images, len(axes)):
        axes[i].axis('off')
    
    plt.suptitle(f'Dataset: {dataset_path.name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # 保存或显示
    if save_output:
        output_path = dataset_path / 'data_visualization.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"可视化结果已保存: {output_path}")
    else:
        plt.show()
    
    plt.close()
    return True


def main():
    parser = argparse.ArgumentParser(description='数据集可视化工具')
    parser.add_argument('dataset', nargs='?', help='数据集名称或路径')
    parser.add_argument('--save', action='store_true', help='保存可视化结果')
    parser.add_argument('--all', action='store_true', help='可视化所有数据集')
    
    args = parser.parse_args()
    
    if not VISUALIZATION_AVAILABLE:
        return 1
    
    renders_dir = Path("renders")
    
    if args.all:
        # 可视化所有数据集
        datasets = [d for d in renders_dir.iterdir() if d.is_dir()]
        
        if not datasets:
            print("未找到任何数据集")
            return 1
        
        print(f"找到 {len(datasets)} 个数据集")
        
        for dataset in datasets:
            visualize_dataset(dataset, save_output=True)
        
        print(f"\n完成! 已可视化 {len(datasets)} 个数据集")
        return 0
    
    elif args.dataset:
        # 可视化指定数据集
        dataset_path = Path(args.dataset)
        
        if not dataset_path.exists():
            # 尝试在renders目录下查找
            dataset_path = renders_dir / args.dataset
        
        if not dataset_path.exists():
            print(f"错误: 数据集不存在: {args.dataset}")
            return 1
        
        return 0 if visualize_dataset(dataset_path, save_output=args.save) else 1
    
    else:
        # 列出所有可用数据集
        datasets = [d for d in renders_dir.iterdir() if d.is_dir()]
        
        if not datasets:
            print("未找到任何数据集")
            print("\n请先生成数据集:")
            print("  python generate_sample_dataset.py")
            return 1
        
        print("可用的数据集:")
        for i, dataset in enumerate(datasets, 1):
            print(f"  {i}. {dataset.name}")
        
        print("\n使用方法:")
        print("  python visualize_dataset.py <数据集名称>")
        print("  python visualize_dataset.py --all  # 可视化所有数据集")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
