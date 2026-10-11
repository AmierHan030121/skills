# imagen

通过独立图片网关生成图片，无需切换主对话模型分组。

## 默认模型

默认使用 `gpt-image-2.5-sunburst`。通过 `@imagen` 调用时，无需额外指定模型。
如网关不支持此模型，调用会报错，不会自动降级；也可通过 `--model` 显式选择其他模型。

## 安装

将本项目 `imagen/` 目录中的 `SKILL.md` 和 `scripts/` 复制到 `~/.codex/skills/imagen/`。
Python 3.11+ 可直接运行；较早版本需要安装 `tomli`。

## 配置

在 `~/.codex/config.toml` 中设置 `image_base_url` 和 `image_apikey`。
不要将真实 API Key 提交到仓库。

## 使用

```powershell
python "$env:USERPROFILE\.codex\skills\imagen\scripts\imagen.py" --prompt "你的图片描述"
```

默认保存 PNG 到当前工作目录。可用 `--out` 指定文件名，或用 `--n` 指定数量。
使用 `--dry-run` 检查模型和请求配置，不调用生图接口。

## 离线测试

```powershell
python -B -m unittest discover -s imagen/tests -v
```
