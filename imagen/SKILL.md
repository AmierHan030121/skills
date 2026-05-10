---
name: imagen
description: 通过独立图片网关生成图片（默认 gpt-image-2），并把结果保存到当前工作目录。只要用户提到 @imagen、imagen、gpt-image-2 单独分组、中转站图片接口、或希望不切换 ccSwitch 分组直接出图，就应使用本技能。技能会从 ~/.codex/config.toml 读取 image_base_url 与 image_apikey。
---

# imagen

用于在不切换主对话模型分组的情况下，直接走单独图片网关出图。

## 何时使用

- 用户明确提到 `@imagen` 或 `imagen`
- 用户说图片模型和主模型分组不同、切换分组很麻烦
- 用户要求读取 `~/.codex/config.toml` 中的 `image_base_url` / `image_apikey`

## 默认行为

1. 使用 `scripts/imagen.py` 调用图片接口，默认模型 `gpt-image-2`。
2. 默认把文件保存到“当前工作目录”（`$PWD`）。
3. 默认输出格式 `png`，自动带时间戳命名，避免覆盖。

## 命令

PowerShell 示例：

```powershell
python "$env:USERPROFILE\.codex\skills\imagen\scripts\imagen.py" `
  --prompt "a clean dashboard hero image, blue and orange palette" `
  --n 1
```

指定文件名：

```powershell
python "$env:USERPROFILE\.codex\skills\imagen\scripts\imagen.py" `
  --prompt "modern isometric data center illustration" `
  --out ".\hero.png"
```

多图：

```powershell
python "$env:USERPROFILE\.codex\skills\imagen\scripts\imagen.py" `
  --prompt "3 variations of fintech app icon" `
  --n 3 `
  --out-dir "."
```

## 约束

- 不要把 API Key 写死到命令里；由脚本读取配置。
- 如果配置缺失，先报清晰错误并提示用户补齐 `image_base_url` 与 `image_apikey`。
- 除非用户要求，不做额外风格扩写，优先忠实执行用户 prompt。
