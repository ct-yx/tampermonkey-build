#!/usr/bin/env python3
"""Validate a Tampermonkey/Violentmonkey userscript without modifying it.

The checker is intentionally conservative: it reports likely permission and
metadata mistakes, then runs ``node --check`` when Node.js is available. It
does not install, patch, upload, or execute the userscript.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


START = re.compile(r"^\s*//\s*==UserScript==\s*$")
END = re.compile(r"^\s*//\s*==/UserScript==\s*$")
META = re.compile(r"^\s*//\s*@([^\s]+)(?:\s+(.*?))?\s*$")
URL_IN_REQUEST = re.compile(
    r"(?:GM(?:_xmlhttpRequest|\.xmlHttpRequest)|GM_webRequest)[\s\S]{0,180}?"
    r"\burl\s*:\s*['\"](https?://[^'\"]+)['\"]",
    re.IGNORECASE,
)
API_CALL = re.compile(
    r"\b(GM_[A-Za-z0-9]+|GM\.[A-Za-z0-9]+|unsafeWindow|"
    r"window\.(?:close|focus|onurlchange))\b"
)

KNOWN_RUN_AT = {"document-start", "document-body", "document-end", "document-idle", "context-menu"}
KNOWN_SANDBOX = {"raw", "JavaScript", "DOM"}
KNOWN_RUN_IN = {"normal-tabs", "incognito-tabs"}

API_GRANTS = {
    "GM_addElement": "GM_addElement",
    "GM_addStyle": "GM_addStyle",
    "GM_download": "GM_download",
    "GM_getResourceText": "GM_getResourceText",
    "GM_getResourceURL": "GM_getResourceURL",
    "GM_info": "GM_info",
    "GM_log": "GM_log",
    "GM_notification": "GM_notification",
    "GM_openInTab": "GM_openInTab",
    "GM_registerMenuCommand": "GM_registerMenuCommand",
    "GM_unregisterMenuCommand": "GM_unregisterMenuCommand",
    "GM_setClipboard": "GM_setClipboard",
    "GM_getTab": "GM_getTab",
    "GM_saveTab": "GM_saveTab",
    "GM_getTabs": "GM_getTabs",
    "GM_setValue": "GM_setValue",
    "GM_getValue": "GM_getValue",
    "GM_deleteValue": "GM_deleteValue",
    "GM_listValues": "GM_listValues",
    "GM_setValues": "GM_setValues",
    "GM_getValues": "GM_getValues",
    "GM_deleteValues": "GM_deleteValues",
    "GM_addValueChangeListener": "GM_addValueChangeListener",
    "GM_removeValueChangeListener": "GM_removeValueChangeListener",
    "GM_xmlhttpRequest": "GM_xmlhttpRequest",
    "GM_webRequest": "GM_webRequest",
    "GM_cookie": "GM_cookie",
    "GM_audio": "GM_audio",
    "unsafeWindow": "unsafeWindow",
    "GM.info": "GM.info",
    "GM.getValue": "GM.getValue",
    "GM.setValue": "GM.setValue",
    "GM.deleteValue": "GM.deleteValue",
    "GM.listValues": "GM.listValues",
    "GM.setValues": "GM.setValues",
    "GM.getValues": "GM.getValues",
    "GM.deleteValues": "GM.deleteValues",
    "GM.addValueChangeListener": "GM.addValueChangeListener",
    "GM.removeValueChangeListener": "GM.removeValueChangeListener",
    "GM.xmlHttpRequest": "GM.xmlHttpRequest",
    "GM.webRequest": "GM.webRequest",
    "GM.cookie": "GM.cookie",
    "GM.audio": "GM.audio",
    "GM.addElement": "GM.addElement",
    "GM.addStyle": "GM.addStyle",
    "GM.download": "GM.download",
    "GM.getResourceText": "GM.getResourceText",
    "GM.getResourceURL": "GM.getResourceURL",
    "GM.log": "GM.log",
    "GM.notification": "GM.notification",
    "GM.openInTab": "GM.openInTab",
    "GM.registerMenuCommand": "GM.registerMenuCommand",
    "GM.unregisterMenuCommand": "GM.unregisterMenuCommand",
    "GM.setClipboard": "GM.setClipboard",
    "window.close": "window.close",
    "window.focus": "window.focus",
    "window.onurlchange": "window.onurlchange",
}

RISKY_GRANTS = {
    "unsafeWindow": "可访问页面 JavaScript 世界，可能绕过 userscript 隔离边界",
    "GM_cookie": "可读写站点 Cookie，涉及登录态和隐私数据",
    "GM.cookie": "可读写站点 Cookie，涉及登录态和隐私数据",
    "GM_webRequest": "实验性请求拦截/改写能力，兼容性和影响范围较大",
    "GM.webRequest": "实验性请求拦截/改写能力，兼容性和影响范围较大",
    "GM_download": "可发起文件下载并写入用户下载目录",
    "GM.download": "可发起文件下载并写入用户下载目录",
}


def add_finding(findings: list[dict[str, Any]], severity: str, code: str, message: str, suggestion: str, line: int | None = None) -> None:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "suggestion": suggestion,
    }
    if line is not None:
        item["line"] = line
    findings.append(item)


def parse_metadata(lines: list[str]) -> tuple[dict[str, list[str]], str, int | None, int | None, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    start = next((i for i, line in enumerate(lines) if START.match(line)), None)
    if start is None:
        add_finding(findings, "error", "metadata.missing_start", "未找到 // ==UserScript==。", "在脚本开头添加 metadata block。")
        return {}, "", None, None, findings

    end = next((i for i in range(start + 1, len(lines)) if END.match(lines[i])), None)
    if end is None:
        add_finding(findings, "error", "metadata.missing_end", "未找到 // ==/UserScript==。", "补齐 metadata block 结束标记。", start + 1)
        return {}, "\n".join(lines[start + 1:]), start, None, findings

    if start > 10:
        add_finding(findings, "warning", "metadata.too_late", "metadata block 距离文件开头超过 10 行。", "把 metadata block 放到文件开头，减少管理器解析差异。", start + 1)

    metadata: dict[str, list[str]] = {}
    for index in range(start + 1, end):
        match = META.match(lines[index])
        if not match:
            if lines[index].strip() and not lines[index].lstrip().startswith("//"):
                add_finding(findings, "warning", "metadata.non_comment_line", "metadata block 中存在非注释行。", "metadata block 内只保留 // @key value。", index + 1)
            continue
        key, value = match.group(1), (match.group(2) or "").strip()
        metadata.setdefault(key, []).append(value)
    return metadata, "\n".join(lines[end + 1:]), start, end, findings


def host_allowed(host: str, connects: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for item in connects:
        value = item.strip().lower().rstrip("/")
        if value in {"*", "self"}:
            return True
        if value.startswith("*.") and host.endswith(value[1:]):
            return True
        if value == host:
            return True
    return False


def validate(path: Path, strict: bool = False, skip_node: bool = False) -> tuple[dict[str, Any], int]:
    findings: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        report = {"path": str(path.resolve()), "ok": False, "findings": [{"severity": "error", "code": "file.encoding", "message": f"无法按 UTF-8 读取脚本：{exc}", "suggestion": "保存为 UTF-8。"}]}
        return report, 1
    except OSError as exc:
        report = {"path": str(path.resolve()), "ok": False, "findings": [{"severity": "error", "code": "file.read", "message": f"无法读取脚本：{exc}", "suggestion": "确认路径和读取权限。"}]}
        return report, 1

    lines = text.splitlines()
    metadata, code, start, end, parse_findings = parse_metadata(lines)
    findings.extend(parse_findings)

    if start is not None and end is not None:
        duplicate_single = {"name", "namespace", "version", "description", "run-at", "run-in", "sandbox", "noframes", "updateURL", "downloadURL", "supportURL"}
        for key in duplicate_single:
            if len(metadata.get(key, [])) > 1:
                add_finding(findings, "warning", "metadata.duplicate", f"metadata @{key} 出现多次。", "仅保留一个值；@match/@grant/@connect 等列表字段可重复。")

    for required in ("name", "version"):
        if not metadata.get(required) or not metadata[required][0]:
            add_finding(findings, "error", f"metadata.missing_{required}", f"缺少 @{required}。", f"添加唯一的 @{required}。")
    if not metadata.get("namespace"):
        add_finding(findings, "warning", "metadata.missing_namespace", "缺少 @namespace。", "使用稳定且唯一的 namespace，避免脚本身份冲突。")
    if not metadata.get("description"):
        add_finding(findings, "warning", "metadata.missing_description", "缺少 @description。", "补充简短、准确的功能描述。")

    matches = metadata.get("match", [])
    includes = metadata.get("include", [])
    if not matches and not includes:
        add_finding(findings, "error", "metadata.no_scope", "没有 @match 或 @include，脚本不会匹配页面。", "添加最小必要的 @match。")
    if "*://*/*" in matches or "*://*/*" in includes:
        add_finding(findings, "warning", "metadata.broad_scope", "脚本匹配所有网站。", "收紧到实际站点和路径，避免扩大权限面。")
    if includes:
        add_finding(findings, "warning", "metadata.include", "使用了兼容性较宽的 @include。", "优先使用可审计的 @match，除非有明确兼容原因。")

    grants = [item for item in metadata.get("grant", []) if item]
    grant_set = set(grants)
    if not metadata.get("grant"):
        add_finding(findings, "warning", "metadata.grant_absent", "未声明 @grant；这与显式 @grant none 不同。", "按实际 API 需求显式声明 @grant none 或具体 GM 权限。")
    if "none" in grant_set and len(grant_set) > 1:
        add_finding(findings, "error", "grant.none_mixed", "@grant none 与其他权限混用。", "删除 none 或删除其他 grant，不能混用。")
    if "*" in grant_set:
        add_finding(findings, "warning", "grant.wildcard", "使用了 @grant *，权限范围过宽。", "改为只声明代码实际使用的具体 API。")
    for grant in sorted(grant_set & RISKY_GRANTS.keys()):
        add_finding(findings, "warning", "grant.high_impact", f"声明了高影响权限 @{grant}：{RISKY_GRANTS[grant]}。", "确认这是必要能力，并在文档中说明数据边界、失败行为和回滚方式。")

    api_calls = sorted(set(API_CALL.findall(code)))
    required_grants = set()
    for call in api_calls:
        grant = API_GRANTS.get(call)
        if grant and call != "GM_info":
            required_grants.add(grant)
    if "none" in grant_set and required_grants:
        add_finding(findings, "error", "grant.none_with_api", f"代码使用 {', '.join(sorted(required_grants))}，但 metadata 声明了 @grant none。", "改成对应具体 grant，或移除 GM API 调用。")
    for grant in sorted(required_grants):
        if grant not in grant_set and "none" not in grant_set:
            add_finding(findings, "error", "grant.missing", f"代码使用 {grant}，但没有对应 @grant。", f"添加 // @grant {grant}，或改用不需要该权限的实现。")

    if any(call in {"GM_xmlhttpRequest", "GM.xmlHttpRequest"} for call in api_calls):
        connects = metadata.get("connect", [])
        if not connects:
            add_finding(findings, "error", "connect.missing", "使用跨域 GM 请求但没有 @connect。", "只添加实际请求的目标主机。")
        for match in URL_IN_REQUEST.finditer(code):
            url = match.group(1)
            host_match = re.match(r"https?://([^/:?#]+)", url, re.IGNORECASE)
            if host_match and not host_allowed(host_match.group(1), connects):
                add_finding(findings, "error", "connect.host_missing", f"请求目标 {host_match.group(1)} 不在 @connect 白名单。", "添加精确主机或移除该请求。")
    elif metadata.get("connect"):
        add_finding(findings, "warning", "connect.unused", "声明了 @connect，但未检测到 GM 请求 API。", "删除无用的 @connect，或确认请求是动态构造的并补充人工审查。")
    if "*" in metadata.get("connect", []):
        add_finding(findings, "warning", "connect.wildcard", "使用了 @connect *，信任范围过宽。", "优先枚举实际目标主机。")

    for run_at in metadata.get("run-at", []):
        if run_at not in KNOWN_RUN_AT:
            add_finding(findings, "error", "metadata.run_at_unknown", f"未知 @run-at 值：{run_at}。", f"使用：{', '.join(sorted(KNOWN_RUN_AT))}。")
        if run_at == "document-start" and metadata.get("require"):
            add_finding(findings, "warning", "metadata.require_timing", "document-start 搭配 @require 可能因依赖下载而延迟执行。", "在目标页面测量时序，必要时内联关键代码或调整架构。")
    for sandbox in metadata.get("sandbox", []):
        if sandbox not in KNOWN_SANDBOX:
            add_finding(findings, "warning", "metadata.sandbox_unknown", f"未识别的 @sandbox 值：{sandbox}。", "按当前管理器官方文档核对。")
    for run_in in metadata.get("run-in", []):
        if run_in not in KNOWN_RUN_IN and not run_in.startswith("container-id-"):
            add_finding(findings, "warning", "metadata.run_in_unknown", f"未识别的 @run-in 值：{run_in}。", "按 Tampermonkey 当前文档和目标浏览器核对。")
    if "unsafeWindow" in api_calls and metadata.get("sandbox") == ["DOM"]:
        add_finding(findings, "warning", "sandbox.unsafe_window", "@sandbox DOM 与 unsafeWindow 需求不一致。", "改为合适的页面交互上下文，并验证 Firefox/Chromium 差异。")
    for requirement in metadata.get("require", []):
        if requirement.startswith(("http://", "https://")) and not re.search(r"(?:@|[?&])(?:v|version|sha256|integrity)=", requirement, re.IGNORECASE):
            add_finding(findings, "warning", "require.unpinned", f"远程 @require 未看到版本或完整性标记：{requirement}", "固定可信版本并记录来源；必要时使用构建锁定。")

    node_result: dict[str, Any] = {"skipped": skip_node}
    if not skip_node:
        node = shutil.which("node")
        if not node:
            node_result = {"skipped": True, "reason": "node_not_found"}
            add_finding(findings, "warning", "node.missing", "未找到 Node.js，跳过 node --check。", "安装 Node.js 或手动运行 node --check。")
        else:
            completed = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, check=False)
            node_result = {"skipped": False, "ok": completed.returncode == 0, "exit_code": completed.returncode, "stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()}
            if completed.returncode != 0:
                add_finding(findings, "error", "node.syntax", "node --check 失败。", "修复 JavaScript 语法后重新验证。")

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    ok = errors == 0 and (not strict or warnings == 0)
    report = {
        "path": str(path.resolve()),
        "metadata": metadata,
        "metadata_lines": {"start": start + 1 if start is not None else None, "end": end + 1 if end is not None else None},
        "api_calls_detected": api_calls,
        "node_check": node_result,
        "summary": {"errors": errors, "warnings": warnings, "findings": len(findings)},
        "ok": ok,
        "findings": findings,
    }
    return report, 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="只读检查 Tampermonkey/Violentmonkey userscript。默认输出 JSON。")
    parser.add_argument("script", type=Path, help="userscript 文件路径")
    parser.add_argument("--strict", action="store_true", help="将 warning 也视为失败")
    parser.add_argument("--skip-node", action="store_true", help="跳过 node --check")
    parser.add_argument("--compact", action="store_true", help="输出紧凑 JSON")
    args = parser.parse_args()
    if not args.script.is_file():
        print(json.dumps({"ok": False, "findings": [{"severity": "error", "code": "file.not_found", "message": f"文件不存在：{args.script}", "suggestion": "确认脚本路径。"}]}, ensure_ascii=False), file=sys.stdout)
        return 1
    report, exit_code = validate(args.script, strict=args.strict, skip_node=args.skip_node)
    print(json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
