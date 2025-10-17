# 光度立体数据集生成器

基于 Mitsuba 3 和 MERL BRDF 数据库的光度立体数据集自动生成工具。

## 功能特性

- 🎨 **真实材质渲染**: 支持 MERL BRDF 数据库的 100+ 种真实材质
- 💡 **多光源配置**: 自动生成多个光源位置（半球、圆形、网格分布）
- 📷 **法线图生成**: 自动渲染真实法线图作为 ground truth
- ⚙️ **高度可配置**: 可调节光源数量、图像尺寸、采样质量
- 🔄 **批量生成**: 支持批量生成多个对象和材质的组合
- 📊 **完整配置**: 自动生成包含相机参数、光源信息的配置文件

## 数据集结构

每个生成的数据集包含：

```
renders/
└── {obj_name}_{brdf_name}_data/
    ├── images/
    │   ├── light_1.jpg              # 光源1图像
    │   ├── light_2.jpg              # 光源2图像
    │   ├── light_3.jpg              # 光源3图像
    │   ├── light_4.jpg              # 光源4图像
    │   └── ground_truth_normal.png  # 真实法线图
    ├── output/                      # 重建结果输出目录
    └── config.yaml                  # 完整配置文件
```

## 安装

### 依赖要求

- Python 3.8+
- Mitsuba 3
- NumPy
- PyYAML
- OpenCV (可选，用于图像格式转换)
- Matplotlib (可选，用于可视化)

### 安装步骤

```bash
# 安装核心依赖
pip install mitsuba numpy pyyaml

# 安装可选依赖（推荐）
pip install opencv-python matplotlib

# 或使用 requirements.txt
pip install -r requirements.txt
```

## 快速开始

### 1. 准备数据

确保有以下目录和文件：

```
项目根目录/
├── brdfs/          # MERL BRDF 文件 (.binary)
├── objects/        # OBJ 文件
└── renders/        # 输出目录（自动创建）
```

如果没有 OBJ 文件，可以生成测试对象：

```bash
python scene_generator.py
```

### 2. 生成示例数据集

最简单的方式：

```bash
python generate_sample_dataset.py
```

### 3. 生成单个数据集

```bash
python dataset_generator.py --single sphere,aluminium --num-lights 4
```

### 4. 批量生成数据集

```bash
# 生成所有组合
python dataset_generator.py

# 指定对象和材质
python dataset_generator.py \
    --obj-files sphere cube cylinder \
    --brdf-files aluminium brass chrome \
    --num-lights 6
```

## 使用示例

### 快速测试（低质量，快速）

```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 4 \
    --image-size 128 128 \
    --spp 32
```

### 标准质量（推荐）

```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 6 \
    --image-size 256 256 \
    --spp 64
```

### 高质量（慢但质量好）

```bash
python dataset_generator.py \
    --single sphere,aluminium \
    --num-lights 8 \
    --image-size 512 512 \
    --spp 256
```

### 批量生成训练数据

```bash
python dataset_generator.py \
    --obj-files sphere cube cylinder \
    --brdf-files aluminium brass chrome steel \
    --num-lights 6 \
    --max-datasets 20
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--obj-dir` | OBJ文件目录 | `objects` |
| `--brdf-dir` | BRDF文件目录 | `brdfs` |
| `--output-dir` | 输出目录 | `renders` |
| `--obj-files` | 指定OBJ文件名（不含扩展名） | 所有 |
| `--brdf-files` | 指定BRDF文件名（不含扩展名） | 所有 |
| `--num-lights` | 光源数量 | 4 |
| `--light-pattern` | 光源分布（hemisphere/circle/grid） | `hemisphere` |
| `--image-size` | 图像尺寸（宽 高） | `256 256` |
| `--spp` | 每像素采样数 | 64 |
| `--max-datasets` | 最大数据集数量 | 无限制 |
| `--single` | 生成单个数据集（格式: obj,brdf） | - |

## 工具脚本

### 验证数据集

检查生成的数据集是否完整：

```bash
python test_dataset_generator.py
```

### 可视化数据集

查看生成的图像：

```bash
# 查看特定数据集
python visualize_dataset.py sphere_aluminium_data

# 可视化所有数据集
python visualize_dataset.py --all

# 保存可视化结果
python visualize_dataset.py --all --save
```

## 性能参考

| 质量级别 | 分辨率 | 采样数 | 时间/数据集 | 存储/数据集 |
|---------|--------|--------|------------|------------|
| 低 | 128×128 | 32 | ~1-2分钟 | ~2 MB |
| 中 | 256×256 | 64 | ~3-5分钟 | ~5 MB |
| 高 | 512×512 | 256 | ~15-30分钟 | ~20 MB |

## 配置文件格式

生成的 `config.yaml` 包含：

```yaml
camera:
  intrinsic_matrix:
    fx: 500.0      # 焦距
    fy: 500.0
    cx: 128.0      # 主点
    cy: 128.0

lights:
  count: 4         # 光源数量
  positions:       # 每个光源的3D位置
    light_1: [x, y, z]
    light_2: [x, y, z]
    # ...
  intensities:     # 每个光源的强度
    light_1: 1.0
    light_2: 1.0
    # ...

reconstruction:
  input_images:    # 输入图像列表
    - dataset_name\images\light_1.jpg
    - dataset_name\images\light_2.jpg
    # ...
  ground_truth_normal: dataset_name\images\ground_truth_normal.png
  output_normal_map: dataset_name\output\normal_map.png
  mask_threshold: 0.1
  shadow_threshold: 0.05
```

## 应用场景

生成的数据集可用于：

1. **光度立体重建**: 使用多光源图像重建物体表面法线
2. **机器学习训练**: 作为训练数据训练深度学习模型
3. **算法测试**: 测试和评估不同的光度立体算法
4. **质量评估**: 与 ground truth 法线图对比评估重建质量

## 文件说明

### 核心文件

- `brdf_renderer.py` - BRDF渲染器（核心依赖）
- `dataset_generator.py` - 数据集生成器（主要功能）
- `scene_generator.py` - 场景/对象生成器
- `generate_sample_dataset.py` - 快速示例生成
- `test_dataset_generator.py` - 数据集验证工具
- `visualize_dataset.py` - 数据集可视化工具

### 文档文件

- `README.md` - 本文件
- `DATASET_README.md` - 快速参考指南
- `数据集生成说明.md` - 中文详细指南
- `DATASET_GENERATION_GUIDE.md` - 英文详细指南

## 常见问题

### Q: 渲染速度太慢？

降低图像尺寸和采样数：
```bash
--image-size 128 128 --spp 32
```

### Q: 如何生成更多光源？

使用 `--num-lights` 参数：
```bash
--num-lights 8
```

### Q: 如何只生成特定材质？

使用 `--brdf-files` 参数：
```bash
--brdf-files aluminium brass chrome
```

### Q: Mitsuba 导入失败？

```bash
pip install --upgrade mitsuba
```

### Q: 未找到 BRDF 文件？

确保 `brdfs/` 目录包含 `.binary` 格式的 MERL BRDF 文件。

### Q: 未找到 OBJ 文件？

运行以下命令生成测试对象：
```bash
python scene_generator.py
```

## 详细文档

- [快速参考 (DATASET_README.md)](DATASET_README.md)
- [中文详细指南 (数据集生成说明.md)](数据集生成说明.md)
- [English Guide (DATASET_GENERATION_GUIDE.md)](DATASET_GENERATION_GUIDE.md)

## 许可证

本项目遵循 MIT 许可证。MERL BRDF 数据库仅供学术和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！
