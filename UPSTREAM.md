# 上游与差异

## 上游参考

- [Anthropic Human Resources Plugin](https://github.com/anthropics/knowledge-work-plugins/tree/658e077ffd7bdd50a12c19ec5ff36fe34c88be8a/human-resources) 的 `draft-offer`：提供 offer 薪酬包、条款、offer letter 正文与谈判建议的基础任务定义。
- 固定版本：`658e077ffd7bdd50a12c19ec5ff36fe34c88be8a`
- 核验时间：2026-08-13（Asia/Shanghai）
- 上游插件版本：`1.3.0`

## 上游目录事实

在上述固定提交中，`human-resources/skills/` 实际可见 9 个 Skill 目录：`comp-analysis`、`draft-offer`、`interview-prep`、`onboarding`、`org-planning`、`people-report`、`policy-lookup`、`performance-review`、`recruiting-pipeline`。本包对应其中的 `draft-offer`。

上游 `draft-offer` 假设可接入 HRIS 与 ATS：从 HRIS 拉取薪酬带宽、校验编制审批、自动填充福利，从 ATS 拉取候选人信息并回写 offer 状态。它把薪酬包、条款、offer letter 正文与给招聘经理的谈判建议一次性拼成一封准备发送的信。

## 本项目的改造

本项目把可复用部分收窄为“本地生成 offer 草稿包”，并明确与“对外发送 offer”分开：

- 不连接薪酬数据服务、HRIS 或 ATS。薪酬带宽、编制审批状态、职级映射由用户提供或经授权只读飞书 Base/Sheets 读入；缺失项进入待确认队列，不反推“合理金额”。
- 候选人用匿名 `candidate_ref`，拒绝姓名、联系方式、受保护属性、薪酬历史等敏感字段进入生成器。
- 现金首年总包按明确口径计算（基础薪资 + 目标奖金 + 首年签字费），股权单独按行权安排列出，不折成现金混入总包。
- offer letter 正文使用占位模板（`[候选人姓名]`、`[公司名称]`、`[职位名称]` 等），不写死真实主体，并标注“草稿，需人工与合规复核后发送”。
- 保留只读、隐私、编制/合规审批与人工定薪闸门；Skill 只产草稿，不代发 offer。

它不自动判断薪酬公平或合规，不产生对某个人的最终定薪结论，也不处理原始个人身份信息。

## 许可证

上游仓库根目录声明 Apache License 2.0。本项目保留来源声明，并以 Apache License 2.0 发布；Anthropic 名称仅用于事实性来源说明，不表示关联或背书。分发前应继续保留本文件、许可证文本和上游链接。
