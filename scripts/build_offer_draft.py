#!/usr/bin/env python3
"""Validate de-identified offer inputs and render a reviewable offer draft package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SENSITIVE = {
    "name", "full_name", "candidate_name", "employee_name", "email", "phone", "mobile", "address",
    "age", "gender", "sex", "ethnicity", "race", "religion", "health", "disability",
    "medical", "family", "marital", "pregnancy", "salary_history", "previous_salary", "resume", "cv",
    "姓名", "邮箱", "电话", "住址", "年龄", "性别", "民族", "宗教", "健康", "家庭",
    "婚姻", "怀孕", "薪酬历史", "前薪", "简历",
}
APPROVAL_TYPES = {"headcount", "compensation", "legal"}
APPROVAL_STATUS = {"approved", "pending", "rejected"}
APPROVAL_LABELS = {"headcount": "编制审批", "compensation": "薪酬审批", "legal": "法务审批"}


def normalized_key(value: Any) -> str:
    return str(value).strip().casefold().replace("-", "_").replace(" ", "_")


def reject_unknown_fields(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(str(key) for key in value if str(key) not in allowed)
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: " + ", ".join(unknown))


def sensitive_paths(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}" if path else str(key)
            if normalized_key(key) in SENSITIVE:
                hits.append(current)
            hits.extend(sensitive_paths(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(sensitive_paths(child, f"{path}[{index}]"))
    return hits


def require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    return text


def require_amount(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number") from exc
    if amount < 0:
        raise ValueError(f"{label} cannot be negative")
    return amount


def optional_amount(value: Any, label: str) -> float | None:
    if value is None:
        return None
    return require_amount(value, label)


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("input root must be an object")
    reject_unknown_fields(spec, {"offer_scope", "candidate", "compensation", "terms", "band", "approvals", "source_materials"}, "input root")
    hits = sensitive_paths(spec)
    if hits:
        raise ValueError("sensitive fields are not allowed: " + ", ".join(hits))

    scope = spec.get("offer_scope")
    if not isinstance(scope, dict):
        raise ValueError("offer_scope is required")
    reject_unknown_fields(scope, {"role", "level", "location", "currency", "period"}, "offer_scope")
    scope_clean = {field: require_text(scope.get(field), f"offer_scope.{field}") for field in ("role", "level", "location", "currency", "period")}

    candidate = spec.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate is required")
    reject_unknown_fields(candidate, {"candidate_ref", "band_id"}, "candidate")
    candidate_clean = {"candidate_ref": require_text(candidate.get("candidate_ref"), "candidate.candidate_ref")}
    if candidate.get("band_id") is not None:
        candidate_clean["band_id"] = require_text(candidate.get("band_id"), "candidate.band_id")

    comp = spec.get("compensation")
    if not isinstance(comp, dict):
        raise ValueError("compensation is required")
    reject_unknown_fields(comp, {"base_salary", "target_bonus_pct", "signing_bonus", "equity"}, "compensation")
    base_salary = require_amount(comp.get("base_salary"), "compensation.base_salary")
    target_bonus_pct = comp.get("target_bonus_pct")
    if target_bonus_pct is not None:
        target_bonus_pct = require_amount(target_bonus_pct, "compensation.target_bonus_pct")
        if target_bonus_pct > 1:
            raise ValueError("compensation.target_bonus_pct must be a ratio between 0 and 1")
    signing_bonus = optional_amount(comp.get("signing_bonus"), "compensation.signing_bonus")
    equity = comp.get("equity")
    equity_clean: dict[str, Any] | None = None
    if equity is not None:
        if not isinstance(equity, dict):
            raise ValueError("compensation.equity must be an object")
        reject_unknown_fields(equity, {"units", "unit_label", "vesting"}, "compensation.equity")
        equity_clean = {
            "units": require_amount(equity.get("units"), "compensation.equity.units"),
            "unit_label": require_text(equity.get("unit_label"), "compensation.equity.unit_label"),
            "vesting": require_text(equity.get("vesting"), "compensation.equity.vesting"),
        }

    terms = spec.get("terms") or {}
    if not isinstance(terms, dict):
        raise ValueError("terms must be an object")
    reject_unknown_fields(terms, {"start_date", "reports_to_ref", "work_mode", "employment_type"}, "terms")
    terms_clean = {field: str(terms.get(field) or "").strip() for field in ("start_date", "reports_to_ref", "work_mode", "employment_type")}

    band = spec.get("band")
    band_clean: dict[str, Any] | None = None
    if band is not None:
        if not isinstance(band, dict):
            raise ValueError("band must be an object")
        reject_unknown_fields(band, {"band_id", "job_family", "level", "location", "minimum", "midpoint", "maximum"}, "band")
        minimum = require_amount(band.get("minimum"), "band.minimum")
        midpoint = require_amount(band.get("midpoint"), "band.midpoint")
        maximum = require_amount(band.get("maximum"), "band.maximum")
        if not minimum < midpoint < maximum:
            raise ValueError("band must satisfy minimum < midpoint < maximum")
        band_clean = {
            "band_id": require_text(band.get("band_id"), "band.band_id"),
            "job_family": str(band.get("job_family") or "").strip(),
            "level": str(band.get("level") or "").strip(),
            "location": str(band.get("location") or "").strip(),
            "minimum": minimum, "midpoint": midpoint, "maximum": maximum,
        }

    approvals = spec.get("approvals") or []
    if not isinstance(approvals, list):
        raise ValueError("approvals must be a list")
    approvals_clean = []
    for index, approval in enumerate(approvals, 1):
        if not isinstance(approval, dict):
            raise ValueError(f"approvals[{index}] must be an object")
        reject_unknown_fields(approval, {"type", "status", "as_of"}, f"approvals[{index}]")
        a_type = normalized_key(approval.get("type"))
        if a_type not in APPROVAL_TYPES:
            raise ValueError(f"approvals[{index}].type must be one of headcount, compensation, legal")
        a_status = normalized_key(approval.get("status"))
        if a_status not in APPROVAL_STATUS:
            raise ValueError(f"approvals[{index}].status must be one of approved, pending, rejected")
        approvals_clean.append({"type": a_type, "status": a_status, "as_of": str(approval.get("as_of") or "").strip()})

    sources = spec.get("source_materials") or []
    if not isinstance(sources, list):
        raise ValueError("source_materials must be a list")
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            raise ValueError(f"source_materials[{index}] must be an object")
        reject_unknown_fields(source, {"id", "type", "label", "as_of"}, f"source_materials[{index}]")
        for field in ("id", "type", "label", "as_of"):
            require_text(source.get(field), f"source_materials[{index}].{field}")
        if {"content", "body", "raw", "path", "token", "access_token"}.intersection(map(normalized_key, source)):
            raise ValueError(f"source_materials[{index}] must contain metadata only")

    return {
        "scope": scope_clean, "candidate": candidate_clean,
        "compensation": {"base_salary": base_salary, "target_bonus_pct": target_bonus_pct, "signing_bonus": signing_bonus, "equity": equity_clean},
        "terms": terms_clean, "band": band_clean, "approvals": approvals_clean, "sources": sources,
    }


def classify(salary: float, band: dict[str, Any]) -> str:
    if salary < band["minimum"]:
        return "低于带宽"
    if salary > band["maximum"]:
        return "高于带宽"
    return "区间内"


def build(spec: dict[str, Any]) -> dict[str, Any]:
    data = validate_spec(spec)
    comp = data["compensation"]
    base = comp["base_salary"]

    review_queue: list[dict[str, str]] = []

    target_bonus_amount: float | None = None
    if comp["target_bonus_pct"] is not None:
        target_bonus_amount = round(base * comp["target_bonus_pct"], 2)
    else:
        review_queue.append({"item": "目标奖金", "reason": "缺目标奖金比例", "next_step": "确认是否设目标奖金及比例，再计入首年现金总包"})

    signing = comp["signing_bonus"] or 0.0
    first_year_cash = round(base + (target_bonus_amount or 0.0) + signing, 2)

    band_position = None
    if data["band"] is not None:
        band = data["band"]
        band_position = {
            "band_id": band["band_id"],
            "compa_ratio": round(base / band["midpoint"], 4),
            "range_penetration": round((base - band["minimum"]) / (band["maximum"] - band["minimum"]), 4),
            "position": classify(base, band),
            "minimum": band["minimum"], "midpoint": band["midpoint"], "maximum": band["maximum"],
        }
        if band_position["position"] != "区间内":
            review_queue.append({"item": band["band_id"], "reason": f"基础薪资{band_position['position']}", "next_step": "核对带宽映射与已批准例外，带宽外通常需要额外薪酬审批"})
    else:
        review_queue.append({"item": "薪酬带宽", "reason": "缺带宽映射", "next_step": "提供岗位/职级/地点对应带宽，才能核对区间位置"})

    for approval in data["approvals"]:
        label = APPROVAL_LABELS[approval["type"]]
        if approval["status"] != "approved":
            review_queue.append({"item": label, "reason": f"{label}状态为 {approval['status']}", "next_step": "发送前需完成该审批"})
    covered = {approval["type"] for approval in data["approvals"]}
    for missing in sorted(APPROVAL_TYPES - covered):
        review_queue.append({"item": APPROVAL_LABELS[missing], "reason": "未提供审批状态", "next_step": "确认该审批是否需要及当前状态"})

    return {
        "schema_version": "1.0", "skill": "hr-offer-drafter", "display_name": "Offer 起草",
        "offer_scope": data["scope"], "candidate_ref": data["candidate"]["candidate_ref"],
        "compensation": {
            "base_salary": base, "target_bonus_pct": comp["target_bonus_pct"], "target_bonus_amount": target_bonus_amount,
            "signing_bonus": comp["signing_bonus"], "first_year_cash": first_year_cash, "equity": comp["equity"],
        },
        "terms": data["terms"], "band_position": band_position,
        "approvals": data["approvals"], "source_materials": data["sources"], "review_queue": review_queue,
    }


def number(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def render_markdown(report: dict[str, Any]) -> str:
    scope = report["offer_scope"]
    comp = report["compensation"]
    lines = [
        f"# Offer 草稿包｜{scope['role']} · {scope['level']}",
        "",
        "> 本文件是 offer 草稿，需人工与合规复核后由有权限的人发送。Agent 不代发 offer。",
        "",
        f"- 候选人：`{report['candidate_ref']}`（匿名）",
        f"- 地点：{scope['location']}",
        f"- 货币：{scope['currency']}",
        f"- 周期：{scope['period']}",
        "",
        "## 薪酬包",
        "",
        "| 项目 | 金额/内容 |",
        "|---|---|",
        f"| 基础薪资 | {number(comp['base_salary'])} |",
    ]
    if comp["target_bonus_amount"] is not None:
        lines.append(f"| 目标奖金 | {number(comp['target_bonus_amount'])}（基础薪资 × {comp['target_bonus_pct']:.0%}，目标值非保证） |")
    else:
        lines.append("| 目标奖金 | 待确认（未提供比例） |")
    lines.append(f"| 签字费（首年） | {number(comp['signing_bonus'])} |" if comp["signing_bonus"] else "| 签字费（首年） | 无 |")
    lines.append(f"| **现金首年总包** | **{number(comp['first_year_cash'])}** |")
    if comp["equity"]:
        equity = comp["equity"]
        lines.append(f"| 股权（单列，不计入现金总包） | {number(equity['units'])} {equity['unit_label']}；{equity['vesting']} |")
    else:
        lines.append("| 股权 | 无 |")

    lines.extend(["", "现金首年总包口径：基础薪资 + 目标奖金金额 + 首年签字费。股权按行权安排单独列出，不折算成现金。此口径用于沟通对齐，不代表到手金额或长期年化收入。"])

    if report["band_position"]:
        band = report["band_position"]
        lines.extend([
            "", "## 带宽位置", "",
            "| 带宽 | compa-ratio | range penetration | 位置 |",
            "|---|---:|---:|---|",
            f"| {band['band_id']} | {band['compa_ratio']:.2f} | {band['range_penetration']:.1%} | {band['position']} |",
        ])

    terms = report["terms"]
    lines.extend(["", "## 录用条款", ""])
    term_rows = [("入职日期", terms.get("start_date")), ("汇报对象", terms.get("reports_to_ref")), ("办公方式", terms.get("work_mode")), ("用工类型", terms.get("employment_type"))]
    for label, value in term_rows:
        lines.append(f"- {label}：{value if value else '待确认'}")

    lines.extend([
        "", "## Offer Letter 正文（占位草稿）", "",
        "```text",
        "尊敬的 [候选人姓名]：",
        "",
        f"我们很高兴向你发出 [公司名称] [职位名称]（{scope['role']} · {scope['level']}）的录用意向。",
        f"工作地点为 {scope['location']}，汇报对象为 [汇报对象]，计划入职日期为 [入职日期]。",
        "",
        f"你的基础薪资为 {number(comp['base_salary'])} {scope['currency']}（{scope['period']}）。",
        "薪酬包的其他部分（目标奖金、签字费、股权）以本草稿薪酬包表格为准，具体条款以正式录用文件为准。",
        "",
        "本意向以完成必要的内部审批与合规核查为前提。",
        "",
        "[公司名称] 敬上",
        "```",
        "",
        "> 占位符 `[...]` 需由人工替换为真实主体；正文措辞与法律条款需经合规复核后再发送。",
    ])

    lines.extend(["", "## 给招聘经理的谈判提示", ""])
    if report["band_position"]:
        band = report["band_position"]
        lines.append(f"- 带宽上下文：offer 基础薪资位于 {band['band_id']} 的 {band['position']}（compa-ratio {band['compa_ratio']:.2f}）。")
    else:
        lines.append("- 带宽上下文：未提供带宽，暂无法给出区间位置。")
    lines.append("- 事实与目标值分开讲：目标奖金是目标值，股权按归属安排兑现，均非保证现金。")
    lines.append("- 越权承诺（提薪、加签字费、改条款）需要对应审批通过后才能对候选人确认。")

    lines.extend(["", "## 待确认队列（发送前）", ""])
    if report["review_queue"]:
        for item in report["review_queue"]:
            lines.append(f"- `{item['item']}`：{item['reason']}；{item['next_step']}。")
    else:
        lines.append("- 当前输入未发现需要自动标记的项目；这不构成可以发送的结论，仍需人工与合规确认。")

    if report["source_materials"]:
        lines.extend(["", "## 材料来源与时效", "", "| 来源 | 类型 | 截止日期 |", "|---|---|---|"])
        lines.extend(f"| {source['label']} | {source['type']} | {source['as_of']} |" for source in report["source_materials"])

    lines.extend([
        "", "## 人工决策边界", "",
        "- 本草稿只整理已提供的脱敏 offer 要素与计算结果。",
        "- 现金首年总包与带宽位置不代表最终定薪、到手金额或对候选人价值的判断。",
        "- 最终定薪、编制与合规审批、向候选人发送 offer 由有权限的人类负责人承担。",
        "",
    ])
    return "\n".join(lines)


def load_spec(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON input: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        report = build(load_spec(args.input))
        output = render_markdown(report) if args.format == "markdown" else json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
