#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mitsuba场景生成工具
为BRDF渲染创建标准化的测试场景
"""

import os
import math
from pathlib import Path
from typing import Tuple, List

def create_sphere_obj(radius: float = 1.0, 
                     subdivisions: int = 32,
                     output_path: str = "sphere.obj") -> bool:
    """
    创建球体OBJ文件
    
    Args:
        radius: 球体半径
        subdivisions: 细分数
        output_path: 输出文件路径
        
    Returns:
        创建是否成功
    """
    try:
        vertices = []
        faces = []
        
        # 生成顶点
        for i in range(subdivisions + 1):
            theta = i * math.pi / subdivisions  # 纬度角
            for j in range(subdivisions * 2):
                phi = j * 2 * math.pi / (subdivisions * 2)  # 经度角
                
                x = radius * math.sin(theta) * math.cos(phi)
                y = radius * math.cos(theta)
                z = radius * math.sin(theta) * math.sin(phi)
                
                vertices.append((x, y, z))
        
        # 生成面
        for i in range(subdivisions):
            for j in range(subdivisions * 2):
                # 当前四边形的四个顶点索引
                v1 = i * (subdivisions * 2) + j
                v2 = i * (subdivisions * 2) + (j + 1) % (subdivisions * 2)
                v3 = (i + 1) * (subdivisions * 2) + (j + 1) % (subdivisions * 2)
                v4 = (i + 1) * (subdivisions * 2) + j
                
                # 避免极点处的退化三角形
                if i == 0:  # 北极
                    faces.append((v1 + 1, v3 + 1, v4 + 1))  # OBJ索引从1开始
                elif i == subdivisions - 1:  # 南极
                    faces.append((v1 + 1, v2 + 1, v4 + 1))
                else:  # 普通四边形，分成两个三角形
                    faces.append((v1 + 1, v2 + 1, v4 + 1))
                    faces.append((v2 + 1, v3 + 1, v4 + 1))
        
        # 写入OBJ文件
        with open(output_path, 'w') as f:
            f.write("# Sphere OBJ file\n")
            f.write(f"# Radius: {radius}, Subdivisions: {subdivisions}\n\n")
            
            # 写入顶点
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # 写入面
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        
        print(f"球体OBJ文件已创建: {output_path}")
        return True
        
    except Exception as e:
        print(f"创建球体OBJ文件失败: {e}")
        return False

def create_cube_obj(size: float = 1.0, 
                   output_path: str = "cube.obj") -> bool:
    """
    创建立方体OBJ文件
    
    Args:
        size: 立方体边长
        output_path: 输出文件路径
        
    Returns:
        创建是否成功
    """
    try:
        half_size = size / 2
        
        # 立方体的8个顶点
        vertices = [
            (-half_size, -half_size, -half_size),  # 0
            ( half_size, -half_size, -half_size),  # 1
            ( half_size,  half_size, -half_size),  # 2
            (-half_size,  half_size, -half_size),  # 3
            (-half_size, -half_size,  half_size),  # 4
            ( half_size, -half_size,  half_size),  # 5
            ( half_size,  half_size,  half_size),  # 6
            (-half_size,  half_size,  half_size),  # 7
        ]
        
        # 立方体的12个三角形面（每个面2个三角形）
        faces = [
            # 前面 (z = half_size)
            (5, 6, 7), (5, 7, 4),
            # 后面 (z = -half_size)
            (1, 3, 2), (1, 4, 3),
            # 右面 (x = half_size)
            (2, 6, 5), (2, 5, 1),
            # 左面 (x = -half_size)
            (4, 7, 3), (4, 3, 0),
            # 上面 (y = half_size)
            (3, 7, 6), (3, 6, 2),
            # 下面 (y = -half_size)
            (0, 1, 5), (0, 5, 4),
        ]
        
        # 写入OBJ文件
        with open(output_path, 'w') as f:
            f.write("# Cube OBJ file\n")
            f.write(f"# Size: {size}\n\n")
            
            # 写入顶点
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # 写入面（OBJ索引从1开始）
            for face in faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
        
        print(f"立方体OBJ文件已创建: {output_path}")
        return True
        
    except Exception as e:
        print(f"创建立方体OBJ文件失败: {e}")
        return False

def create_plane_obj(width: float = 2.0, 
                    height: float = 2.0,
                    subdivisions: int = 1,
                    output_path: str = "plane.obj") -> bool:
    """
    创建平面OBJ文件
    
    Args:
        width: 平面宽度
        height: 平面高度
        subdivisions: 细分数
        output_path: 输出文件路径
        
    Returns:
        创建是否成功
    """
    try:
        vertices = []
        faces = []
        
        # 生成顶点
        for i in range(subdivisions + 1):
            for j in range(subdivisions + 1):
                x = (j / subdivisions - 0.5) * width
                y = 0.0
                z = (i / subdivisions - 0.5) * height
                vertices.append((x, y, z))
        
        # 生成面
        for i in range(subdivisions):
            for j in range(subdivisions):
                # 四边形的四个顶点
                v1 = i * (subdivisions + 1) + j
                v2 = i * (subdivisions + 1) + j + 1
                v3 = (i + 1) * (subdivisions + 1) + j + 1
                v4 = (i + 1) * (subdivisions + 1) + j
                
                # 分成两个三角形
                faces.append((v1 + 1, v2 + 1, v4 + 1))  # OBJ索引从1开始
                faces.append((v2 + 1, v3 + 1, v4 + 1))
        
        # 写入OBJ文件
        with open(output_path, 'w') as f:
            f.write("# Plane OBJ file\n")
            f.write(f"# Width: {width}, Height: {height}, Subdivisions: {subdivisions}\n\n")
            
            # 写入顶点
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # 写入面
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        
        print(f"平面OBJ文件已创建: {output_path}")
        return True
        
    except Exception as e:
        print(f"创建平面OBJ文件失败: {e}")
        return False

def create_cylinder_obj(radius: float = 1.0,
                       height: float = 2.0,
                       subdivisions: int = 16,
                       output_path: str = "cylinder.obj") -> bool:
    """
    创建圆柱体OBJ文件
    
    Args:
        radius: 圆柱体半径
        height: 圆柱体高度
        subdivisions: 圆周细分数
        output_path: 输出文件路径
        
    Returns:
        创建是否成功
    """
    try:
        vertices = []
        faces = []
        
        half_height = height / 2
        
        # 生成底面和顶面的顶点
        for level in [0, 1]:  # 0=底面, 1=顶面
            y = -half_height if level == 0 else half_height
            
            # 中心点
            vertices.append((0.0, y, 0.0))
            
            # 圆周上的点
            for i in range(subdivisions):
                angle = 2 * math.pi * i / subdivisions
                x = radius * math.cos(angle)
                z = radius * math.sin(angle)
                vertices.append((x, y, z))
        
        # 生成底面三角形
        center_bottom = 0
        for i in range(subdivisions):
            v1 = center_bottom
            v2 = 1 + i
            v3 = 1 + (i + 1) % subdivisions
            faces.append((v1 + 1, v3 + 1, v2 + 1))  # 逆时针
        
        # 生成顶面三角形
        center_top = subdivisions + 1
        for i in range(subdivisions):
            v1 = center_top
            v2 = center_top + 1 + i
            v3 = center_top + 1 + (i + 1) % subdivisions
            faces.append((v1 + 1, v2 + 1, v3 + 1))  # 顺时针
        
        # 生成侧面四边形
        for i in range(subdivisions):
            # 底面边上的点
            v1 = 1 + i
            v2 = 1 + (i + 1) % subdivisions
            # 顶面边上的点
            v3 = center_top + 1 + (i + 1) % subdivisions
            v4 = center_top + 1 + i
            
            # 分成两个三角形
            faces.append((v1 + 1, v2 + 1, v4 + 1))
            faces.append((v2 + 1, v3 + 1, v4 + 1))
        
        # 写入OBJ文件
        with open(output_path, 'w') as f:
            f.write("# Cylinder OBJ file\n")
            f.write(f"# Radius: {radius}, Height: {height}, Subdivisions: {subdivisions}\n\n")
            
            # 写入顶点
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # 写入面
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        
        print(f"圆柱体OBJ文件已创建: {output_path}")
        return True
        
    except Exception as e:
        print(f"创建圆柱体OBJ文件失败: {e}")
        return False

def create_torus_obj(major_radius: float = 1.0,
                    minor_radius: float = 0.3,
                    major_subdivisions: int = 16,
                    minor_subdivisions: int = 8,
                    output_path: str = "torus.obj") -> bool:
    """
    创建环面OBJ文件
    
    Args:
        major_radius: 主半径（环的中心到管中心的距离）
        minor_radius: 次半径（管的半径）
        major_subdivisions: 主方向细分数
        minor_subdivisions: 次方向细分数
        output_path: 输出文件路径
        
    Returns:
        创建是否成功
    """
    try:
        vertices = []
        faces = []
        
        # 生成顶点
        for i in range(major_subdivisions):
            theta = 2 * math.pi * i / major_subdivisions  # 主角度
            
            for j in range(minor_subdivisions):
                phi = 2 * math.pi * j / minor_subdivisions  # 次角度
                
                # 环面参数方程
                x = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta)
                y = minor_radius * math.sin(phi)
                z = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta)
                
                vertices.append((x, y, z))
        
        # 生成面
        for i in range(major_subdivisions):
            for j in range(minor_subdivisions):
                # 当前四边形的四个顶点
                v1 = i * minor_subdivisions + j
                v2 = i * minor_subdivisions + (j + 1) % minor_subdivisions
                v3 = ((i + 1) % major_subdivisions) * minor_subdivisions + (j + 1) % minor_subdivisions
                v4 = ((i + 1) % major_subdivisions) * minor_subdivisions + j
                
                # 分成两个三角形
                faces.append((v1 + 1, v2 + 1, v4 + 1))
                faces.append((v2 + 1, v3 + 1, v4 + 1))
        
        # 写入OBJ文件
        with open(output_path, 'w') as f:
            f.write("# Torus OBJ file\n")
            f.write(f"# Major radius: {major_radius}, Minor radius: {minor_radius}\n")
            f.write(f"# Major subdivisions: {major_subdivisions}, Minor subdivisions: {minor_subdivisions}\n\n")
            
            # 写入顶点
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # 写入面
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        
        print(f"环面OBJ文件已创建: {output_path}")
        return True
        
    except Exception as e:
        print(f"创建环面OBJ文件失败: {e}")
        return False

def create_all_test_objects(output_dir: str = "objects"):
    """
    创建所有测试对象
    
    Args:
        output_dir: 输出目录
    """
    # 创建输出目录
    Path(output_dir).mkdir(exist_ok=True)
    
    print("创建测试OBJ文件...")
    
    # 创建各种几何体
    objects_to_create = [
        ("sphere", lambda: create_sphere_obj(1.0, 32, f"{output_dir}/sphere.obj")),
        ("sphere_lowpoly", lambda: create_sphere_obj(1.0, 16, f"{output_dir}/sphere_lowpoly.obj")),
        ("cube", lambda: create_cube_obj(1.5, f"{output_dir}/cube.obj")),
        ("plane", lambda: create_plane_obj(2.0, 2.0, 4, f"{output_dir}/plane.obj")),
        ("cylinder", lambda: create_cylinder_obj(0.8, 2.0, 24, f"{output_dir}/cylinder.obj")),
        ("torus", lambda: create_torus_obj(1.0, 0.3, 24, 12, f"{output_dir}/torus.obj")),
    ]
    
    created_count = 0
    for name, create_func in objects_to_create:
        try:
            if create_func():
                created_count += 1
        except Exception as e:
            print(f"创建 {name} 失败: {e}")
    
    print(f"\n成功创建 {created_count}/{len(objects_to_create)} 个测试对象")
    print(f"输出目录: {output_dir}")

def main():
    """主函数"""
    print("=== Mitsuba场景生成工具 ===\n")
    
    import argparse
    parser = argparse.ArgumentParser(description='创建测试用的OBJ文件')
    parser.add_argument('--output-dir', '-o', default='objects', 
                       help='输出目录')
    parser.add_argument('--object', choices=['sphere', 'cube', 'plane', 'cylinder', 'torus', 'all'],
                       default='all', help='要创建的对象类型')
    
    args = parser.parse_args()
    
    if args.object == 'all':
        create_all_test_objects(args.output_dir)
    else:
        Path(args.output_dir).mkdir(exist_ok=True)
        
        if args.object == 'sphere':
            create_sphere_obj(1.0, 32, f"{args.output_dir}/sphere.obj")
        elif args.object == 'cube':
            create_cube_obj(1.5, f"{args.output_dir}/cube.obj")
        elif args.object == 'plane':
            create_plane_obj(2.0, 2.0, 4, f"{args.output_dir}/plane.obj")
        elif args.object == 'cylinder':
            create_cylinder_obj(0.8, 2.0, 24, f"{args.output_dir}/cylinder.obj")
        elif args.object == 'torus':
            create_torus_obj(1.0, 0.3, 24, 12, f"{args.output_dir}/torus.obj")

if __name__ == "__main__":
    main()