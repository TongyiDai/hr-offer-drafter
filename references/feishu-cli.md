# 飞书可选读取

飞书不是本 Skill 的必要依赖。用户明确要求读取飞书材料时，先确认当前身份：

```bash
lark-cli auth status --json --verify
```

只读取用户指定的脱敏带宽表或编制审批状态表：

```bash
lark-cli sheets +cells-get --url "https://example.feishu.cn/sheets/shtXXXX" \
  --sheet-name "脱敏薪酬带宽" --range "A1:Z200" --include value,formula --as user --json
```

先向用户展示将读取的范围，再将内容转换为本地脱敏 JSON。不要默认搜索“薪酬”“offer”相关全库文档，不要读取候选人个人明细、简历、原始审批意见、聊天或其他非必要内容。

本 Skill 默认没有写入能力，也不代发 offer。需要更新表格、发送录用通知、创建审批或同步 HRIS/ATS 时，先输出草案、获取用户单独确认、调用对应系统能力，并读取目标记录验证。
