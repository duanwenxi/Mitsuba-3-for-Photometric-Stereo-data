# 光度立体渲染器

基于 Mitsuba 3 和 MERL BRDF 数据库的光度立体数据集生成工具，提供 Web 界面和命令行两种使用方式。

## 核心特性

- **Web 界面渲染** - 现代化浏览器界面，实时进度显示，网格预览
- **RGB 彩色渲染** - 生成高质量 RGB 图像和法线图
- **真实材质** - 支持 MERL BRDF 数据库 100+ 种真实材质
- **灵活光源配置** - 点光源、平行光，支持自定义位置和强度
- **批量生成** - 命令行工具支持批量生成数据集
- **完整配置** - 自动生成包含相机、光源参数的配置文件

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- Python 3.8+
- Mitsuba 3
- Flask + Flask-SocketIO（Web 版）
- NumPy, PyYAML, Pillow

### 方式一：Web 界面（推荐）

```bash
# 启动 Web 服务器
python start_web.py

# 或直接运行
python web_render.py
```

然后在浏览器中访问 `http://localhost:8081`

**Web 界面功能：**
- 选择 OBJ 模型和 BRDF 材质
- 配置相机参数（FOV、位置）
- 设置光源（数量、分布、强度）
- 调整渲染质量（分辨率、采样数）
- 实时查看渲染进度
- 网格预览所有结果
- 点击图像放大查看

### 方式二：命令行批量生成

```bash
# 生成单个数据集
python dataset_generator.py --single sphere,aluminium --num-lights 4

# 批量生成
python dataset_generator.py --obj-files sphere cube --brdf-files aluminium brass --num-lights 6

# 自定义参数
python dataset_generator.py \
    --single sphere,chrome \
    --num-lights 8 \
    --image-size 512 512 \
    --spp 128 \
    --light-pattern hemisphere
```

## 数据集结构

生成的数据集包含：

```
renders/
└── {dataset_name}/
    ├── images/
    │   ├── light_1.png              # 光源1图像
    │   ├── light_2.png              # 光源2图像
    │   ├── ...
    │   └── ground_truth_normal.png  # 法线图（Ground Truth）
    ├── output/                      # 重建结果输出目录
    └── config.yaml                  # 配置文件
```

配置文件包含：
- 相机参数（FOV、位置、内参矩阵）
- 光源信息（位置、类型、强度）
- 图像路径和元数据

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--obj-dir` | `objects` | OBJ 文件目录 |
| `--brdf-dir` | `brdfs` | BRDF 文件目录 |
| `--output-dir` | `renders` | 输出目录 |
| `--num-lights` | `4` | 光源数量 |
| `--light-pattern` | `hemisphere` | 光源分布（hemisphere/circle/grid） |
| `--image-size` | `256 256` | 图像尺寸 |
| `--spp` | `64` | 每像素采样数 |
| `--single` | - | 生成单个数据集（格式：obj,brdf） |

## 项目结构

```
├── web_render.py           # Web 应用主程序
├── start_web.py            # Web 启动脚本
├── dataset_generator.py    # 数据集生成器（核心）
├── brdf_renderer.py        # BRDF 渲染器
├── scene_generator.py      # 场景生成器
├── visualize_dataset.py    # 数据集可视化工具
├── mitsuba_config_fix.py   # Mitsuba 配置修复
├── templates/              # Web 模板
│   └── index.html
├── static/                 # Web 静态资源
│   └── app.js
├── objects/                # OBJ 模型文件
├── brdfs/                  # BRDF 材质文件
└── renders/                # 渲染输出目录
```

## 技术栈

- **渲染引擎**: Mitsuba 3 (scalar_rgb)
- **Web 框架**: Flask + Flask-SocketIO
- **前端**: Bootstrap 5 + Vanilla JavaScript
- **图像处理**: Pillow, NumPy
- **配置**: PyYAML

## 常见问题

**Q: Web 界面无法访问？**
- 检查端口 8081 是否被占用
- 确保防火墙允许访问

**Q: 渲染失败？**
- 确保 `objects/` 和 `brdfs/` 目录中有文件
- 检查 Mitsuba 是否正确安装
- 查看控制台日志获取详细错误信息

**Q: 如何生成测试模型？**
```bash
python scene_generator.py
```

**Q: 如何可视化已生成的数据集？**
```bash
python visualize_dataset.py --all
```

## 许可证

MIT License - 允许自由使用、修改和分发

**注意**: MERL BRDF 数据库仅供学术和研究使用