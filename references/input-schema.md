# 输入结构

生成器读取一个脱敏 JSON。

```json
{
  "offer_scope": {
    "role": "后端工程师",
    "level": "5",
    "location": "中国",
    "currency": "CNY",
    "period": "annual base salary"
  },
  "candidate": {
    "candidate_ref": "C-2026-0142",
    "band_id": "ENG-5-CN"
  },
  "compensation": {
    "base_salary": 620000,
    "target_bonus_pct": 0.15,
    "signing_bonus": 60000,
    "equity": {"units": 4000, "unit_label": "RSU", "vesting": "4 年归属，每年 25%，首年后 12 个月悬崖"}
  },
  "terms": {
    "start_date": "2026-09-01",
    "reports_to_ref": "M-014",
    "work_mode": "混合办公",
    "employment_type": "全职"
  },
  "band": {
    "band_id": "ENG-5-CN", "job_family": "工程", "level": "5", "location": "中国",
    "minimum": 480000, "midpoint": 600000, "maximum": 720000
  },
  "approvals": [
    {"type": "headcount", "status": "approved", "as_of": "2026-08-01"},
    {"type": "compensation", "status": "pending", "as_of": "2026-08-12"}
  ],
  "source_materials": [
    {"id": "band-v1", "type": "local-sheet", "label": "薪酬带宽", "as_of": "2026-07-01"}
  ]
}
```

## 字段说明

- `offer_scope`：`role`、`level`、`location`、`currency`、`period` 必填。口径不同的薪酬项不能直接相加。
- `candidate`：`candidate_ref` 必填，是匿名标识；`band_id` 可选，用于与 `band` 对齐。不接受姓名、联系方式、简历等字段。
- `compensation`：`base_salary` 必填。`target_bonus_pct`（0 到 1 的比例）、`signing_bonus`、`equity` 可选；缺失项进入待确认队列，不推测补齐。
- `compensation.equity`：`units` 必填数值，`unit_label`（如 `RSU`、`期权`）和 `vesting`（行权安排文字）必填。股权单独列出，不折成现金混入首年总包。
- `terms`：`start_date`、`reports_to_ref`（匿名管理者标识）、`work_mode`、`employment_type` 可选；`reports_to_ref` 只用匿名标识，不用真实姓名。
- `band`：可选。提供时 `minimum < midpoint < maximum`，用于计算 compa-ratio 与 range penetration。
- `approvals`：可选。`type` 取 `headcount`、`compensation`、`legal` 之一，`status` 取 `approved`、`pending`、`rejected` 之一。非 `approved` 的审批进入待确认队列。
- `source_materials`：只保留 `id`、`type`、`label`、`as_of` 元数据，不含原始内容、路径或凭证。

`band` 与 `approvals` 可为空。生成器不联网补带宽或市场数据；缺失口径一律进入待确认队列。
