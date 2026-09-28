# 数据来源与本地同步

截至 2026-09-26，程序仍只运行一个本机 SQLite 数据库：`data/health.db`。以下是其中的外部数据快照和本地整理的索引；普通页面查询不访问外部 API。

| 来源 | 本地条目 | 用途和范围 |
|---|---:|---|
| [RxNorm](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html) | 25 个药名 | 常见通用名与 RxCUI；中文名是项目人工整理的检索词，不是中国批准药品目录。 |
| [DailyMed](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm) | 23 条说明书链接 | 与药名匹配的美国说明书索引；不等于用户手中产品或处方。 |
| [USDA FoodData Central](https://fdc.nal.usda.gov/download-datasets/) | 10 个演示食品映射；7,793 个 SR Legacy 食品；469 个 Foundation Foods 食品 | 演示映射用于定位来源；新增两个目录可按英文名称查询部分每 100 克营养数值。SR Legacy 是 2018 最终发布版本，Foundation Foods 快照来自 2026-04。 |
| [国家卫健委食养指南](https://www.nhc.gov.cn/sps/c100088/202402/9ba512ba8e314a47a181db11d2fa188d.shtml) | 10 条文件索引 | 按已记录疾病展示官方指南入口；项目的中文摘要和合并规则另在 `data/rules/` 人工维护。 |
| [USDA/ODS 食物嘌呤数据库](https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/methods-and-application-of-food-composition-laboratory/mafcl-site-pages/purine-content-of-foods/) | 475 条食品和酒类样本 | 保留英文食物描述、来源地区、样本数及 mg/100g 或 mg/100mL 单位。 |
| [MedlinePlus 健康主题 XML](https://medlineplus.gov/xml.html) | 1,017 个英文主题 | 美国国家医学图书馆健康科普快照，日期 2026-09-25；10 个常见主题附中文检索名。Source: MedlinePlus, National Library of Medicine. |

`food_composition_references` 存储 USDA 食品成分，`health_topic_references` 存储 MedlinePlus 主题；既有表保存药名、食品样本映射、指南和嘌呤样本。项目自身的疾病约束和科普卡来自 `data/rules/`，不是这些英文数据库自动推导的结论。

## 网页与 API 使用

在浏览器打开 `http://127.0.0.1:8000/`，填写健康资料并生成指南。第二页底部可查询食品成分、嘌呤样本及 MedlinePlus 主题。食品成分和嘌呤查询主要使用英文食物名；主题的 10 个常见名称可用中文查，其余主要用英文。原始来源链接在联网时才能打开。

- `/reference/sources`：当前各快照条目数和来源。
- `/reference/composition?q=oats`：USDA 食品成分；`kind=foundation_food` 或 `sr_legacy_food` 可筛选。
- `/reference/health-topics?q=糖尿病`：MedlinePlus 健康主题；`featured=true` 获取已映射的常见主题。
- `/reference/purines?q=beef`、`/reference/guidelines?condition=hypertension`：嘌呤与官方指南索引。

营养字段中的 `null` 表示该样本未给出这个值。美国食品样本不能直接代表中式菜肴、加工品牌、烹调后的实际份量；MedlinePlus 原文为英文。**新增的食品成分、嘌呤和医学主题不参与当前饮食日记的演示评分，也不扩大药物相互作用安全规则。**

## 更新快照

在项目根目录的 PowerShell 中执行：

```powershell
.\.venv\Scripts\python.exe .\scripts\sync_references.py
.\.venv\Scripts\python.exe .\scripts\sync_health_data.py
.\.venv\Scripts\python.exe .\scripts\sync_more_references.py
```

运行 `sync_references.py` 会访问 RxNorm 和 DailyMed；另外两支脚本在首次缺少官方归档时下载文件，缓存保存在 `.run/`。普通网页查询始终读取本地快照。`sync_more_references.py` 使用固定版本的官方文件，重复运行会在一个数据库事务内替换相关快照。升级到下一次官方发布需要核对文件结构与 URL 后调整脚本，不能把本地快照当作实时资料。

## 临床边界

药名匹配不验证适应证、剂量或中国市场的产品。MedlinePlus 主题和指南索引用于阅读，不能据此诊断疾病或自动生成个人治疗方案。现有药物安全检查仍是独立的少量确定性演示规则；未出现提醒不代表安全。需要更贴近本地饮食的中国食物成分批量数据时，应先核实获取和再利用授权。
