# 本地后端技术方案

## 已实现

FastAPI 提供 HTTP 接口，Pydantic 校验输入，SQLAlchemy 管理本地 SQLite。Flutter 暂未初始化，用户选择先用浏览器试用后端。

领域引擎仅接收普通结构化数据，不依赖 HTTP、数据库会话或 Flutter：

- Disease：根据 active 疾病返回约束及演示监测任务。
- Nutrition：按约束键合并；优先级、严重程度、约束严格程度和规则 ID 形成稳定排序。方向相反时标为 review，保留所有来源，不自动消解临床冲突。
- Medication：根据用户记录、起止日期、每日时刻和服药事件生成计划；不进行医学安全判断。
- Interactions：独立读取版本化规则，匹配药药、药病、药食、病食、同通用名重复记录和用餐关系。明确报告未知药物与未知食物。
- Care Plan：整合以上模块，按时间输出服药、餐点和健康监测任务。观察指标只用于标记记录任务完成，不进行诊断。

本版 API 在 backend/app/main.py，模型与输入输出结构分别在 models.py / schemas.py。小型 MVP 使用应用工厂与生命周期初始化数据库，测试注入独立临时数据库。以后路由数量增长时可按领域拆分 APIRouter。

## 数据与时间

Patient、Condition、Medication、MedicationEvent、Observation 持久化。身高和体重计算 BMI。Observation 的 13 类指标限制单位与字段形状，但不解释医学异常值。
数据库时间统一 UTC；SQLite 读取时恢复时区。每日计划明确按 UTC+08:00 计算，避免午夜附近的日期偏移。历史服药事件保留记录时的药物快照；当前用药变更不覆盖快照。

DATABASE_URL 预留数据库替换；PostgreSQL 驱动和 schema migration 后续实现。本版 create_all 不承担迁移工作。药物只支持每天固定时刻，未实现 PRN、隔日或周期疗程调度。

## 规则版本与证据

规则在 data/rules/*.json。安全规则字段由 Pydantic 验证，拒绝未知触发字段与重复规则 ID。结果包含命中规则、版本、来源、触发的记录 ID 和具体字段。

引用的公开资料：

- [NHLBI DASH](https://www.nhlbi.nih.gov/health/dash-eating-plan)：控盐示例。
- [NIDDK Healthy Living with Diabetes](https://www.niddk.nih.gov/health-information/diabetes/overview/healthy-living-with-diabetes)：糖尿病饮食示例。
- [NHLBI Heart-Healthy Foods](https://www.nhlbi.nih.gov/health/heart-healthy-living/healthy-foods)：饮食脂肪与全谷物示例。
- [FDA Grapefruit and Medicines](https://www.fda.gov/consumers/consumer-updates/grapefruit-juice-and-some-drugs-dont-mix)：药食提醒示例。
- [DailyMed Ibuprofen](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2fa4bfc8-386c-433b-bc46-24fc8ec1bca1)：药药提醒示例。
- [DailyMed Ibuprofen / hypertension](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e07d989d-1b0e-4cc1-abf2-93c8b208a29a)：药病提醒示例。

这些资料为规则来源，不代表本软件经过临床验证。高尿酸血症与痛风的饮食摘要已依据国家卫健委 2024 年食养指南核对，但两个诊断与病程不能互相代替；个体饮水量、嘌呤摄入量和药物方案仍需专业评估。提醒严重程度和匹配逻辑均为本 MVP 的演示配置，不构成权威临床分级。

Medical Logic != LLM。本项目无 LLM 调用；不自动诊断、推荐药物、停药、换药或调整剂量。肾功能剂量、肝功能、妊娠、过敏判断、老年 PIM 等均未评估，后续必须增加规则和验证。

## 部署

后端、数据库、规则、Swagger 资源全部位于本机。Swagger UI 5.17.14 的开源静态资源及 LICENSE/NOTICE 保存在 backend/app/static；仅点击证据来源链接时访问外网。

默认仅监听 127.0.0.1，不开放外部访问。当前无身份认证，患者 ID 的归属检查防止子记录错配，但不是多用户权限隔离。生产部署需另行实现认证授权、HTTPS、备份和数据迁移。
