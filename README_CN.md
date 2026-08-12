# 显微图案自动匹配核心算法

## 1. 项目用途

本程序将四张目标显微图像分别与四张辅助结构图像进行独立匹配，自动估计辅助结构到目标图的尺度、旋转和平移，并输出识别字母、自然背景结果图和仅保留匹配证据的二值图。

当前输入对应字母为 `S`、`T`、`U` 和 `Z`。匹配采用单张独立排名，不使用一对一批次分配。

## 2. 目录结构

```text
run_matching.py                    主运行入口
requirements.txt                  Python 依赖
microscopy_matching/
  image_processing.py             暗色响应、前景、骨架和走廊提取
  scale_calibration.py             比例尺检测与像素/微米换算
  registration.py                  尺度、旋转和平移搜索
  topology_metrics.py              端点、方向和缺失笔画评分
  evidence_mask.py                 匹配区域证据门控与二值导出
  pipeline.py                      完整流程编排和结果写出
data/input/
  target_images/                   四张目标图
  reference_images/                四张辅助结构图
```

## 3. 环境要求

- Python 3.10 或更高版本
- Windows、Linux 或 macOS

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 4. 运行方法

在解压后的项目根目录执行：

```powershell
python -B run_matching.py
```

也可以明确指定输入和输出目录：

```powershell
python -B run_matching.py `
  --targets data\input\target_images `
  --references data\input\reference_images `
  --outdir artifacts\matching_results
```

## 5. 输出文件

```text
artifacts/matching_results/
  results.json
  presentation/
    target_01_S.png
    target_02_T.png
    target_03_U.png
    target_04_Z.png
  binary/
    target_01_S.png
    target_02_T.png
    target_03_U.png
    target_04_Z.png
```

`presentation` 保存自然背景展示图。`binary` 保存仅来自目标图、且位于已配准辅助结构走廊内的二值证据。算法不会在二值结果中人为补笔。

## 6. 核心匹配规则

1. 从目标图和辅助图提取暗色响应、前景掩膜与骨架。
2. 检测目标图右下角的比例尺，并使用明确给定的 `200 µm` 物理长度建立尺度约束。
3. 对每一张目标图分别搜索所有辅助候选的尺度、旋转和平移。
4. 使用几何距离、方向一致性、骨架覆盖、端点覆盖和缺失笔画惩罚形成统一分数。
5. 每张目标图独立选择最高分候选，不使用文件顺序强制标签，也不使用批次一对一分配。
6. 最终二值图只保留“目标前景 ∩ 已配准辅助结构走廊”。

## 7. 结果状态

- `accepted`：分差和结构指标满足自动接受条件。
- `flagged_low_margin`：最高分与第二名分差较小，建议人工复核。
- `flagged_topology`：存在关键笔画缺失或端点覆盖不足，建议人工复核。
- 其他状态标志可能记录搜索边界命中或尺度审核信息。

审核状态不会改变最高分候选，只用于表达结果不确定性。

## 8. 当前输入的验证结果

本核心包已通过独立解压运行验证，当前四张输入图的最高分结果依次为：

```text
target_01 -> S
target_02 -> T
target_03 -> U
target_04 -> Z
```

## 9. 注意事项

- 辅助图文件名用于提供候选标签，但不决定某张目标图的最终结果。
- 输入目录必须各包含四张可读取的 JPG 或 PNG 图像。
- 替换输入图时必须确认比例尺物理含义；程序不会通过 OCR 自动猜测标尺文字。
- `python paper_figures/run_all.py` 是审稿人端到端入口：它直接读取 `data/input/` 中四张目标图和四张参考图，重新执行全部 16 个候选配准，再由同一个算法结果生成 Figure H 的八张独立 PNG、五张补充材料总图、42 张补充材料单图以及可审计的 CSV/JSON 数值表。
- 论文图不再读取冻结组合图或写死的论文分数。绘图入口要求系统安装 Arial；如果找不到 Arial 会直接报错，不会静默换字体。
- 论文图均为 RGB、600 dpi PNG，不生成 ZIP、Word、PDF、SVG 或 TIFF。
- `paper_figures/generated/` 不提交到 Git。审稿人使用上述一键入口从仓库中提交的原始输入和当前算法重新生成全部结果，避免旧 PNG 或人工后处理图与代码不一致。
