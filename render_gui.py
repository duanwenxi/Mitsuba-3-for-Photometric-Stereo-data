#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
渲染参数配置 GUI
提供可视化界面配置渲染参数并实时预览渲染结果
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import threading
import logging
from dataset_generator import PhotometricStereoDataGenerator

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("光度立体渲染器")
        self.root.geometry("1200x800")
        
        # 初始化生成器
        self.generator = PhotometricStereoDataGenerator()
        
        # 获取可用的 OBJ 和 BRDF 文件
        self.obj_files = self._get_obj_files()
        self.brdf_files = self._get_brdf_files()
        
        # 渲染结果图像
        self.rendered_images = []
        self.current_image_index = 0
        
        # 创建界面
        self._create_widgets()
        
    def _get_obj_files(self):
        """获取所有 OBJ 文件"""
        obj_dir = Path("objects")
        if obj_dir.exists():
            return sorted([f.stem for f in obj_dir.glob("*.obj")])
        return []
    
    def _get_brdf_files(self):
        """获取所有 BRDF 文件"""
        brdf_dir = Path("brdfs")
        if brdf_dir.exists():
            return sorted([f.stem for f in brdf_dir.glob("*.binary")])
        return []
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 左侧参数面板
        param_frame = ttk.LabelFrame(main_frame, text="渲染参数", padding="10")
        param_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 右侧预览面板
        preview_frame = ttk.LabelFrame(main_frame, text="渲染预览", padding="10")
        preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # 创建参数输入控件
        self._create_parameter_inputs(param_frame)
        
        # 创建预览区域
        self._create_preview_area(preview_frame)
        
    def _create_parameter_inputs(self, parent):
        """创建参数输入控件"""
        row = 0
        
        # OBJ 文件选择
        ttk.Label(parent, text="物体模型:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.obj_var = tk.StringVar(value=self.obj_files[0] if self.obj_files else "")
        obj_combo = ttk.Combobox(parent, textvariable=self.obj_var, values=self.obj_files, width=25)
        obj_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # BRDF 材质选择
        ttk.Label(parent, text="BRDF 材质:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.brdf_var = tk.StringVar(value=self.brdf_files[0] if self.brdf_files else "")
        brdf_combo = ttk.Combobox(parent, textvariable=self.brdf_var, values=self.brdf_files, width=25)
        brdf_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 分隔线
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 相机参数
        ttk.Label(parent, text="相机 FOV (度):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.fov_var = tk.DoubleVar(value=45.0)
        ttk.Entry(parent, textvariable=self.fov_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="相机位置 X:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cam_x_var = tk.DoubleVar(value=0.0)
        ttk.Entry(parent, textvariable=self.cam_x_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="相机位置 Y:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cam_y_var = tk.DoubleVar(value=0.0)
        ttk.Entry(parent, textvariable=self.cam_y_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="相机位置 Z:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cam_z_var = tk.DoubleVar(value=5.0)
        ttk.Entry(parent, textvariable=self.cam_z_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="目标点 X:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.target_x_var = tk.DoubleVar(value=0.0)
        ttk.Entry(parent, textvariable=self.target_x_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="目标点 Y:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.target_y_var = tk.DoubleVar(value=0.0)
        ttk.Entry(parent, textvariable=self.target_y_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="目标点 Z:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.target_z_var = tk.DoubleVar(value=0.0)
        ttk.Entry(parent, textvariable=self.target_z_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 分隔线
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 光源参数
        ttk.Label(parent, text="光源数量:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.num_lights_var = tk.IntVar(value=4)
        ttk.Entry(parent, textvariable=self.num_lights_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="光源分布:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.light_pattern_var = tk.StringVar(value="hemisphere")
        pattern_combo = ttk.Combobox(parent, textvariable=self.light_pattern_var, 
                                     values=["hemisphere", "circle", "grid"], width=25)
        pattern_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="光源距离:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.light_distance_var = tk.DoubleVar(value=2.0)
        ttk.Entry(parent, textvariable=self.light_distance_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="光源强度:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.light_intensity_var = tk.DoubleVar(value=50.0)
        ttk.Entry(parent, textvariable=self.light_intensity_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 分隔线
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 渲染参数
        ttk.Label(parent, text="图像宽度:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.width_var = tk.IntVar(value=512)
        ttk.Entry(parent, textvariable=self.width_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="图像高度:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.height_var = tk.IntVar(value=512)
        ttk.Entry(parent, textvariable=self.height_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        ttk.Label(parent, text="采样数 (SPP):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.spp_var = tk.IntVar(value=64)
        ttk.Entry(parent, textvariable=self.spp_var, width=27).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 分隔线
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 渲染按钮
        self.render_button = ttk.Button(parent, text="开始渲染", command=self._start_render)
        self.render_button.grid(row=row, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        row += 1
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(parent, textvariable=self.status_var, foreground="blue")
        status_label.grid(row=row, column=0, columnspan=2, pady=5)
        
    def _create_preview_area(self, parent):
        """创建预览区域"""
        # 图像显示区域
        self.canvas = tk.Canvas(parent, bg="gray", width=600, height=600)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 图像导航控制
        nav_frame = ttk.Frame(parent)
        nav_frame.grid(row=1, column=0, pady=10)
        
        self.prev_button = ttk.Button(nav_frame, text="< 上一张", command=self._prev_image, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.image_label = ttk.Label(nav_frame, text="无图像")
        self.image_label.pack(side=tk.LEFT, padx=20)
        
        self.next_button = ttk.Button(nav_frame, text="下一张 >", command=self._next_image, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
    def _start_render(self):
        """开始渲染"""
        # 验证输入
        if not self.obj_var.get():
            messagebox.showerror("错误", "请选择物体模型")
            return
        
        if not self.brdf_var.get():
            messagebox.showerror("错误", "请选择 BRDF 材质")
            return
        
        # 禁用渲染按钮
        self.render_button.config(state=tk.DISABLED)
        self.status_var.set("渲染中...")
        
        # 在新线程中执行渲染
        thread = threading.Thread(target=self._render_thread)
        thread.daemon = True
        thread.start()
        
    def _render_thread(self):
        """渲染线程"""
        try:
            # 在渲染线程中重新初始化 Mitsuba
            try:
                import mitsuba as mi
                # 使用最兼容的变体
                mi.set_variant('scalar_rgb')
                logger.info("成功设置 Mitsuba 变体: scalar_rgb")
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"Mitsuba 初始化失败: {str(e)}"))
                return
            
            # 在渲染线程中重新创建生成器（确保使用正确的 Mitsuba 上下文）
            generator = PhotometricStereoDataGenerator()
            
            # 获取参数
            obj_name = self.obj_var.get()
            brdf_name = self.brdf_var.get()
            obj_path = str(Path("objects") / f"{obj_name}.obj")
            brdf_path = str(Path("brdfs") / f"{brdf_name}.binary")
            
            dataset_name = f"gui_render_{obj_name}_{brdf_name}"
            
            # 执行渲染
            success = generator.generate_single_dataset(
                dataset_name=dataset_name,
                obj_path=obj_path,
                brdf_path=brdf_path,
                num_lights=self.num_lights_var.get(),
                light_pattern=self.light_pattern_var.get(),
                light_distance=self.light_distance_var.get(),
                light_intensity=self.light_intensity_var.get(),
                camera_fov=self.fov_var.get(),
                camera_position=(self.cam_x_var.get(), self.cam_y_var.get(), self.cam_z_var.get()),
                camera_target=(self.target_x_var.get(), self.target_y_var.get(), self.target_z_var.get()),
                image_size=(self.width_var.get(), self.height_var.get()),
                spp=self.spp_var.get()
            )
            
            if success:
                # 加载渲染结果
                self._load_rendered_images(dataset_name)
                self.root.after(0, lambda: self.status_var.set("渲染完成"))
                self.root.after(0, lambda: messagebox.showinfo("成功", "渲染完成！"))
            else:
                self.root.after(0, lambda: self.status_var.set("渲染失败"))
                self.root.after(0, lambda: messagebox.showerror("错误", "渲染失败，请查看日志"))
                
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"错误: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"渲染出错: {str(e)}"))
        
        finally:
            # 重新启用渲染按钮
            self.root.after(0, lambda: self.render_button.config(state=tk.NORMAL))
    
    def _load_rendered_images(self, dataset_name):
        """加载渲染的图像"""
        images_dir = Path("renders") / dataset_name / "images"
        
        if not images_dir.exists():
            return
        
        # 获取所有图像文件
        image_files = sorted(images_dir.glob("*.png"))
        self.rendered_images = [str(f) for f in image_files]
        self.current_image_index = 0
        
        # 更新界面
        self.root.after(0, self._update_image_display)
        
    def _update_image_display(self):
        """更新图像显示"""
        if not self.rendered_images:
            return
        
        # 加载当前图像
        image_path = self.rendered_images[self.current_image_index]
        image = Image.open(image_path)
        
        # 调整图像大小以适应画布
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        # 转换为 PhotoImage
        photo = ImageTk.PhotoImage(image)
        
        # 显示图像
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
        self.canvas.image = photo  # 保持引用
        
        # 更新标签
        image_name = Path(image_path).name
        self.image_label.config(text=f"{self.current_image_index + 1}/{len(self.rendered_images)}: {image_name}")
        
        # 更新按钮状态
        self.prev_button.config(state=tk.NORMAL if self.current_image_index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_image_index < len(self.rendered_images) - 1 else tk.DISABLED)
    
    def _prev_image(self):
        """显示上一张图像"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self._update_image_display()
    
    def _next_image(self):
        """显示下一张图像"""
        if self.current_image_index < len(self.rendered_images) - 1:
            self.current_image_index += 1
            self._update_image_display()


def main():
    root = tk.Tk()
    app = RenderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
