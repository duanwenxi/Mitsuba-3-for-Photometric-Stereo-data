# 🌟 光度立体数据集生成器

> 基于 Mitsuba 3 和 MERL BRDF 数据库的专业光度立体数据集自动生成工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Mitsuba](https://img.shields.io/badge/Mitsuba-3.0+-green.svg)](https://mitsuba-renderer.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🎨 **真实材质渲染** | 支持 MERL BRDF 数据库的 100+ 种真实材质 |
| 💡 **智能光源配置** | 自动生成多个光源位置（半球、圆形、网格分布） |
| 📷 **Ground Truth 生成** | 自动渲染真实法线图作为标准答案 |
| ⚙️ **高度可配置** | 灵活调节光源数量、图像尺寸、采样质量 |
| 🔄 **批量处理** | 支持批量生成多个对象和材质的组合 |
| 📊 **完整元数据** | 自动生成包含相机参数、光源信息的配置文件 |

## 📁 数据集结构

每个生成的数据集遵循标准化结构，便于后续处理和分析：

```
renders/
└── {obj_name}_{brdf_name}_data/
    ├── images/                      # 📸 渲染图像
    │   ├── light_1.jpg              #   光源1图像
    │   ├── light_2.jpg              #   光源2图像
    │   ├── light_3.jpg              #   光源3图像
    │   ├── light_4.jpg              #   光源4图像
    │   └── ground_truth_normal.png  #   真实法线图 (Ground Truth)
    ├── output/                      # 📊 重建结果输出目录
    └── config.yaml                  # ⚙️ 完整配置文件
```

> **💡 提示**: 每个数据集都是自包含的，包含了进行光度立体重建所需的全部信息。

## 🚀 快速开始

### 📋 系统要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | 3.8+ | 核心运行环境 |
| **Mitsuba 3** | 最新版 | 渲染引擎 |
| **NumPy** | 任意版本 | 数值计算 |
| **PyYAML** | 任意版本 | 配置文件处理 |
| **OpenCV** | 可选 | 图像格式转换 |
| **Matplotlib** | 可选 | 数据可视化 |

### 🔧 安装步骤

#### 方式一：一键安装（推荐）
```bash
pip install -r requirements.txt
```

#### 方式二：分步安装
```bash
# 1. 安装核心依赖
pip install mitsuba numpy pyyaml

# 2. 安装可选依赖（推荐）
pip install opencv-python matplotlib
```

#### 方式三：Conda 环境
```bash
conda create -n photometric-stereo python=3.8
conda activate photometric-stereo
pip install mitsuba numpy pyyaml opencv-python matplotlib
```

### 📂 项目初始化

#### 1. 目录结构准备
确保项目根目录包含以下结构：

```
项目根目录/
├── brdfs/          # 📦 MERL BRDF 文件 (.binary)
├── objects/        # 🎯 3D 对象文件 (.obj)
├── renders/        # 📁 输出目录（自动创建）
├── analysis/       # 📊 分析脚本
└── README.md       # 📖 项目文档
```

#### 2. 生成测试对象（可选）
如果没有 OBJ 文件，可以生成基础几何体：

```bash
python scene_generator.py
```

### 🎯 使用示例

#### 🚀 一键生成示例数据集
```bash
python generate_sample_dataset.py
```

#### 🎨 生成单个数据集
```bash
python dataset_generator.py --single sphere,aluminium --num-lights 4
```

#### 🔄 批量生成数据集
```bash
# 生成所有可能的组合
python dataset_generator.py

# 指定特定对象和材质
python dataset_generator.py \
    --obj-files sphere cube cylinder \
    --brdf-files aluminium brass chrome \
    --num-lights 6
```

## ⚙️ 配置选项

### 🎛️ 质量预设

| 质量级别 | 命令示例 | 适用场景 |
|----------|----------|----------|
| **🚀 快速测试** | `--image-size 128 128 --spp 32` | 原型验证、快速迭代 |
| **⭐ 标准质量** | `--image-size 256 256 --spp 64` | 一般研究、算法开发 |
| **💎 高质量** | `--image-size 512 512 --spp 256` | 论文发表、精确分析 |

#### 快速测试配置
```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 4 \
    --image-size 128 128 \
    --spp 32
```

#### 标准质量配置（推荐）
```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 6 \
    --image-size 256 256 \
    --spp 64
```

#### 高质量配置
```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 8 \
    --image-size 512 512 \
    --spp 256
```

#### 批量生成训练数据
```bash
python dataset_generator.py \
    --obj-files sphere cube cylinder \
    --brdf-files aluminium brass chrome steel \
    --num-lights 6 \
    --max-datasets 20
```

### 📋 完整参数列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--obj-dir` | 路径 | `objects` | 3D对象文件目录 |
| `--brdf-dir` | 路径 | `brdfs` | BRDF材质文件目录 |
| `--output-dir` | 路径 | `renders` | 数据集输出目录 |
| `--obj-files` | 列表 | 全部 | 指定对象文件名（不含扩展名） |
| `--brdf-files` | 列表 | 全部 | 指定材质文件名（不含扩展名） |
| `--num-lights` | 整数 | `4` | 光源数量 |
| `--light-pattern` | 枚举 | `hemisphere` | 光源分布模式 |
| `--image-size` | 整数对 | `256 256` | 图像尺寸（宽×高） |
| `--spp` | 整数 | `64` | 每像素采样数（影响质量） |
| `--max-datasets` | 整数 | 无限制 | 最大生成数据集数量 |
| `--single` | 字符串 | - | 生成单个数据集（格式: `obj,brdf`） |

#### 光源分布模式说明
- **`hemisphere`**: 半球面均匀分布（推荐）
- **`circle`**: 圆形平面分布
- **`grid`**: 网格规律分布

## 🛠️ 辅助工具

### 🔍 数据集验证
检查生成的数据集完整性和有效性：

```bash
python test_dataset_generator.py
```

### 📊 数据集可视化
提供多种可视化选项：

```bash
# 查看特定数据集
python visualize_dataset.py sphere_aluminium_data

# 可视化所有数据集
python visualize_dataset.py --all

# 保存可视化结果到文件
python visualize_dataset.py --all --save

# 生成对比图表
python visualize_dataset.py --compare --save
```

## 📈 性能基准

| 质量级别 | 分辨率 | 采样数 | 渲染时间 | 存储空间 | 推荐用途 |
|---------|--------|--------|----------|----------|----------|
| 🚀 **快速** | 128×128 | 32 | ~1-2分钟 | ~2 MB | 原型开发、快速测试 |
| ⭐ **标准** | 256×256 | 64 | ~3-5分钟 | ~5 MB | 研究开发、算法验证 |
| 💎 **高质量** | 512×512 | 256 | ~15-30分钟 | ~20 MB | 论文发表、精确分析 |
| 🔬 **超高质量** | 1024×1024 | 512 | ~1-2小时 | ~80 MB | 商业应用、最终产品 |

> **💡 性能提示**: 
> - 使用 GPU 加速可显著提升渲染速度
> - 批量生成时建议使用中等质量设置
> - 存储空间会随光源数量线性增长

## 📄 配置文件详解

每个数据集自动生成的 `config.yaml` 包含完整的元数据信息：

```yaml
# 📷 相机参数
camera:
  intrinsic_matrix:
    fx: 500.0      # X轴焦距
    fy: 500.0      # Y轴焦距  
    cx: 128.0      # 主点X坐标
    cy: 128.0      # 主点Y坐标
  resolution: [256, 256]  # 图像分辨率

# 💡 光源配置
lights:
  count: 4         # 光源总数
  pattern: "hemisphere"  # 分布模式
  positions:       # 3D空间位置
    light_1: [x, y, z]
    light_2: [x, y, z]
    light_3: [x, y, z]
    light_4: [x, y, z]
  intensities:     # 光源强度
    light_1: 1.0
    light_2: 1.0
    light_3: 1.0
    light_4: 1.0

# 🎯 重建配置
reconstruction:
  input_images:    # 输入图像路径
    - "images/light_1.jpg"
    - "images/light_2.jpg"
    - "images/light_3.jpg"
    - "images/light_4.jpg"
  ground_truth_normal: "images/ground_truth_normal.png"
  output_normal_map: "output/normal_map.png"
  
  # 🔧 算法参数
  mask_threshold: 0.1      # 掩码阈值
  shadow_threshold: 0.05   # 阴影检测阈值
  
# 📊 元数据
metadata:
  object_name: "sphere"
  material_name: "aluminium"
  generation_time: "2024-01-01T12:00:00"
  mitsuba_version: "3.x.x"
```

## 🎯 应用场景

生成的数据集适用于多种研究和应用场景：

### 🔬 学术研究
- **光度立体重建**: 使用多光源图像重建物体表面法线
- **算法验证**: 测试和评估不同的光度立体算法
- **质量评估**: 与 Ground Truth 法线图对比评估重建质量

### 🤖 机器学习
- **训练数据**: 为深度学习模型提供大规模训练数据
- **数据增强**: 生成多样化的材质和光照条件
- **基准测试**: 建立标准化的评估基准

### 🏭 工业应用
- **质量检测**: 表面缺陷检测和质量控制
- **3D 重建**: 工业零件的精确三维重建
- **材质分析**: 材料属性的光学特征分析

## 📚 项目文件说明

### 🔧 核心文件
| 文件 | 功能 | 重要性 |
|------|------|--------|
| `brdf_renderer.py` | BRDF渲染器核心模块 | ⭐⭐⭐ |
| `dataset_generator.py` | 数据集生成主程序 | ⭐⭐⭐ |
| `scene_generator.py` | 3D场景和对象生成器 | ⭐⭐ |
| `generate_sample_dataset.py` | 快速示例生成脚本 | ⭐⭐ |

### 🛠️ 工具文件
| 文件 | 功能 | 用途 |
|------|------|------|
| `test_dataset_generator.py` | 数据集验证工具 | 质量检查 |
| `visualize_dataset.py` | 数据集可视化工具 | 结果展示 |

### 📖 文档文件
| 文件 | 内容 | 目标读者 |
|------|------|----------|
| `README.md` | 项目主文档（本文件） | 所有用户 |
| `DATASET_README.md` | 快速参考指南 | 新手用户 |
| `数据集生成说明.md` | 中文详细指南 | 中文用户 |
| `DATASET_GENERATION_GUIDE.md` | 英文详细指南 | 国际用户 |

## ❓ 常见问题与解决方案

### 🐌 性能问题

**Q: 渲染速度太慢？**
```bash
# 解决方案：降低质量设置
python dataset_generator.py --image-size 128 128 --spp 32
```

**Q: 内存不足？**
```bash
# 解决方案：减少批量处理数量
python dataset_generator.py --max-datasets 5
```

### ⚙️ 配置问题

**Q: 如何生成更多光源？**
```bash
python dataset_generator.py --num-lights 8
```

**Q: 如何只生成特定材质？**
```bash
python dataset_generator.py --brdf-files aluminium brass chrome
```

### 🔧 安装问题

**Q: Mitsuba 导入失败？**
```bash
pip install --upgrade mitsuba
# 或者使用 conda
conda install -c conda-forge mitsuba
```

**Q: 未找到 BRDF 文件？**
- 确保 `brdfs/` 目录包含 `.binary` 格式的 MERL BRDF 文件
- 可从 [MERL BRDF Database](https://www.merl.com/brdf/) 下载

**Q: 未找到 OBJ 文件？**
```bash
# 生成测试对象
python scene_generator.py
```

### 🔍 调试技巧

1. **启用详细日志**:
   ```bash
   python dataset_generator.py --verbose
   ```

2. **检查数据集完整性**:
   ```bash
   python test_dataset_generator.py
   ```

3. **可视化结果**:
   ```bash
   python visualize_dataset.py --all
   ```

## 📖 详细文档

| 文档 | 描述 | 适用场景 |
|------|------|----------|
| [快速参考 (DATASET_README.md)](DATASET_README.md) | 简明使用指南 | 快速上手 |
| [中文详细指南 (数据集生成说明.md)](数据集生成说明.md) | 完整中文教程 | 深入学习 |
| [English Guide (DATASET_GENERATION_GUIDE.md)](DATASET_GENERATION_GUIDE.md) | Complete English tutorial | International users |

## 📄 许可证与致谢

### 📜 许可证
本项目遵循 **MIT 许可证**，允许自由使用、修改和分发。

### 🙏 致谢
- **Mitsuba 3**: 提供强大的渲染引擎
- **MERL BRDF Database**: 提供真实材质数据（仅供学术和研究使用）
- **开源社区**: 感谢所有贡献者和用户的支持

### ⚠️ 使用限制
- MERL BRDF 数据库仅供**学术和研究使用**
- 商业用途请确保遵循相关许可证要求

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 🐛 报告问题
- 使用 [GitHub Issues](../../issues) 报告 Bug
- 提供详细的错误信息和复现步骤
- 包含系统环境信息

### 💡 功能建议
- 在 Issues 中提出新功能建议
- 详细描述功能需求和使用场景
- 欢迎提供设计方案

### 🔧 代码贡献
1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 📝 文档贡献
- 改进现有文档
- 添加使用示例
- 翻译文档到其他语言

---

<div align="center">

**🌟 如果这个项目对您有帮助，请给我们一个 Star！**

[![GitHub stars](https://img.shields.io/github/stars/your-username/your-repo.svg?style=social&label=Star)](https://github.com/your-username/your-repo)

</div>