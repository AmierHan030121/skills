#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest


def die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_toml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"Config not found: {path}")
    try:
        import tomllib  # py3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as exc:
            die("Missing TOML parser. Install tomli or use Python 3.11+.")
            raise exc
    with path.open("rb") as f:
        return tomllib.load(f)


def find_first_string_key(node: Any, key: str) -> Optional[str]:
    needle = key.lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.lower() == needle and isinstance(v, str):
                text = v.strip()
                if text:
                    return text
        for v in node.values():
            found = find_first_string_key(v, key)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_first_string_key(item, key)
            if found:
                return found
    return None


def resolve_image_credentials(config: Dict[str, Any], config_path: Path) -> tuple[str, str]:
    base_url = find_first_string_key(config, "image_base_url")
    api_key = find_first_string_key(config, "image_apikey")
    if not api_key:
        api_key = find_first_string_key(config, "image_api_key")

    missing: List[str] = []
    if not base_url:
        missing.append("image_base_url")
    if not api_key:
        missing.append("image_apikey")
    if missing:
        die(
            "Missing required key(s) in config.toml: "
            + ", ".join(missing)
            + f". Please add them to {config_path}"
        )

    return base_url.rstrip("/"), api_key


def build_images_endpoint(base_url: str) -> str:
    if base_url.endswith("/v1"):
        return f"{base_url}/images/generations"
    return f"{base_url}/v1/images/generations"


def read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> str:
    if bool(prompt) == bool(prompt_file):
        die("Use exactly one of --prompt or --prompt-file.")
    if prompt_file:
        path = Path(prompt_file)
        if not path.exists():
            die(f"Prompt file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
    else:
        text = (prompt or "").strip()
    if not text:
        die("Prompt cannot be empty.")
    return text


def normalize_output_format(fmt: str) -> str:
    normalized = fmt.lower().strip()
    if normalized == "jpg":
        normalized = "jpeg"
    allowed = {"png", "jpeg", "webp"}
    if normalized not in allowed:
        die("output format must be one of: png, jpeg, webp")
    return normalized


def ext_for(fmt: str) -> str:
    return "jpg" if fmt == "jpeg" else fmt


def ensure_output_paths(
    out: Optional[str],
    out_dir: Optional[str],
    n: int,
    output_format: str,
) -> List[Path]:
    ext = ext_for(output_format)

    if out:
        out_path = Path(out)
        if n == 1:
            if out_path.suffix == "":
                out_path = out_path.with_suffix(f".{ext}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            return [out_path]
        base = out_path.with_suffix("") if out_path.suffix else out_path
        base.parent.mkdir(parents=True, exist_ok=True)
        return [base.with_name(f"{base.name}-{i + 1:02d}.{ext}") for i in range(n)]

    target_dir = Path(out_dir) if out_dir else Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return [target_dir / f"imagen-{stamp}-{i + 1:02d}.{ext}" for i in range(n)]


def decode_image_field(item: Dict[str, Any]) -> bytes:
    b64 = item.get("b64_json")
    if isinstance(b64, str) and b64.strip():
        payload = b64.split(",", 1)[1] if b64.startswith("data:") and "," in b64 else b64
        return base64.b64decode(payload)

    url = item.get("url")
    if isinstance(url, str) and url.strip():
        req = urlrequest.Request(url, method="GET")
        with urlrequest.urlopen(req, timeout=120) as resp:
            return resp.read()

    die("Image response missing b64_json/url payload.")
    return b""


def request_images(
    endpoint: str,
    api_key: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urlerror.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<no-body>"
        die(f"HTTP {exc.code} from image gateway: {err_body}")
    except urlerror.URLError as exc:
        die(f"Network error calling image gateway: {exc.reason}")


def write_outputs(images: Iterable[Dict[str, Any]], paths: List[Path]) -> List[Path]:
    written: List[Path] = []
    for index, item in enumerate(images):
        if index >= len(paths):
            break
        raw = decode_image_field(item)
        out = paths[index]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        written.append(out.resolve())
    if not written:
        die("No image data returned by gateway.")
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate images via image_base_url/image_apikey.")
    parser.add_argument("--prompt", help="Image prompt text")
    parser.add_argument("--prompt-file", help="Path to prompt text file")
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="auto")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--out", help="Single output path or basename")
    parser.add_argument("--out-dir", help="Output directory (default: current directory)")
    parser.add_argument(
        "--config",
        default=str(Path.home() / ".codex" / "config.toml"),
        help="Path to codex config.toml",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.n < 1 or args.n > 10:
        die("--n must be between 1 and 10")
    return args


def main() -> int:
    args = parse_args()
    prompt = read_prompt(args.prompt, args.prompt_file)
    output_format = normalize_output_format(args.output_format)

    config_path = Path(args.config).expanduser()
    config = load_toml(config_path)
    base_url, api_key = resolve_image_credentials(config, config_path)
    endpoint = build_images_endpoint(base_url)

    payload: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "n": args.n,
        "size": args.size,
        "quality": args.quality,
        "output_format": output_format,
    }

    paths = ensure_output_paths(args.out, args.out_dir, args.n, output_format)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "endpoint": endpoint,
                    "model": args.model,
                    "n": args.n,
                    "size": args.size,
                    "quality": args.quality,
                    "output_format": output_format,
                    "paths": [str(p) for p in paths],
                    "config": str(config_path),
                    "has_api_key": bool(api_key),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    response = request_images(endpoint, api_key, payload)
    data = response.get("data")
    if not isinstance(data, list):
        die(f"Unexpected response shape: {json.dumps(response, ensure_ascii=False)}")
    written = write_outputs(data, paths)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
