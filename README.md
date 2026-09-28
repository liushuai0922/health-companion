# Health Companion · 本地后端 MVP

疾病 + 用药 + 饮食统一数据模型和确定性规则引擎。现在首页提供两步体验：① 录入年龄、身高、体重、疾病与药物；② 查看按疾病整理及多病合并的饮食指南，记录每日饮食并查看透明的演示评分。后端 API 保留。按照用户选择，暂不安装 Flutter / Android SDK，`mobile/` 仍为占位目录。

默认示例为 42 岁、172 cm、82 kg、血脂异常且有脂肪肝的虚拟患者，不预设处方。第二页有待改善和调整后两份饮食示例。示例分数是未经过临床验证的产品规则，不能用于诊断、判断营养足量或决定用药。详细验证见 [docs/two-page-demo.md](docs/two-page-demo.md)。

本机 SQLite 已保存 RxNorm 药名、DailyMed 说明书索引、国家卫健委指南索引、USDA/ODS 嘌呤样本，以及新增的 USDA 食品成分目录（SR Legacy 7,793 条、Foundation Foods 469 条）和 MedlinePlus 英文健康主题（1,017 条）。第二页可检索食物成分和医学主题；来源状态见 `/reference/sources`，同步与适用边界见 [docs/data-sources.md](docs/data-sources.md)。这些目录不扩大现有药物安全规则覆盖范围，也不直接参与饮食日记演示评分。

## 立即试用（Windows PowerShell）

先在 PowerShell 中进入下载或克隆后的 `health-companion` 项目目录，再运行：

首次在新电脑运行时，先安装 Python（本项目在 3.14 上测试）并创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

已有 `.venv` 时直接启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1
```

`data/health.db` 是本机生成的数据库，不随 GitHub 代码上传。启动脚本会创建演示患者；若要下载并建立完整的药品、食品和医学主题参考索引，再按 [数据来源与本地同步](docs/data-sources.md#更新快照) 执行同步命令，首次同步需要联网。

打开 <http://127.0.0.1:8000/>。交互式 API 文档：<http://127.0.0.1:8000/docs>。
首页预填可编辑的脂肪肝示例；点击“生成我的饮食指南”后保存资料。浏览器记住最近保存的资料 ID，饮食记录和评分存入本地 SQLite。种子脚本可重复执行，不覆盖或重置既有数据；旧版风险组合演示记录仍保留，但不作为首页默认示例。
若已有服务占用 8000，直接打开入口；另启服务可传入 `-Port 8001`。
前台运行按 Ctrl+C 停止。本次协作启动的后台服务可用以下命令停止：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-backend.ps1
```

脚本的 Bypass 只用于该进程，不修改系统执行策略。

## 什么在本地运行

| 组件 | 位置 | 需要外部服务器吗 |
|---|---|---|
| FastAPI / Uvicorn | 本机 Windows Python 虚拟环境 | 不需要 |
| SQLite | `data/health.db` | 不需要 |
| 疾病、营养、安全、Care Plan 引擎 | 本机 Python；规则在 `data/rules/` | 不需要 |
| 浏览器入口和 Swagger 文档 | 本机，JS/CSS 已保存在项目内 | 不需要 |
| Flutter 手机 App | 尚未初始化 | 开发时可连接本机；不是本阶段功能 |

安装依赖时需要网络；安装完成后的本地功能不调用外部 API。证据来源链接只有点击阅读时需要网络。没有接入大模型服务或云数据库。
手机与电脑在同一局域网时可在后续开发中联调，不要求云服务器；当前只监听 127.0.0.1，手机暂时不能直接访问。远程访问、多设备同步、生产部署需另行设计服务器、身份认证、HTTPS 和备份。

## 可试用的流程

1. 打开首页，填写或直接使用虚拟示例，点击“生成我的饮食指南”。第二页切换“记录饮食 · 查看评分”，逐餐添加食物、确认完整记录，再保存评分。可选择日期读取已保存记录。
2. 在 `/docs` 中使用 POST `/patients` 创建自己的虚拟测试患者，不要求年龄大于 65。
3. 添加 conditions、medications、observations。疾病编码、药物别名、食物编码和指标单位可通过 `/catalog/*` 查询。
4. 获取 `/patients/{id}/care-plan`，可指定 `day=2026-09-25`；省略日期时按 UTC+08:00 的今天计算。
5. 用 PUT `/patients/{id}/medications/{medication_id}/events` 登记 `taken`、`missed` 或 `delayed`，再获取计划查看状态变化。

更完整的请求示例见 [docs/try-it.md](docs/try-it.md)。

## 安装和测试

已有 `.venv` 无需重新安装。新环境使用已验证的锁定版本：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

smoke test 临时监听 18765，验证 `/health` 后停止；可用 `-Port` 指定其他端口。
SQLite 路径不受启动目录影响。可通过 `DATABASE_URL` 配置未来数据库连接；PostgreSQL 驱动、迁移及部署尚未实现。本阶段 `create_all` 仅创建缺失表，不自动迁移旧表结构。

## 结构

- `backend/app/`：FastAPI、Pydantic、SQLAlchemy、静态试用入口。
- `core/{disease,medication,nutrition,interactions,care_plan}/`：低耦合确定性引擎。
- `data/{rules,drugs,foods,diseases}/`：JSON 规则、别名字典；疾病目录位于疾病规则文件内。
- `tests/`：隔离数据库测试，覆盖单/多疾病、冲突、重复用药、相互作用、历史、时区和 API。
- `scripts/`：PowerShell 启停/测试，以及演示数据脚本。
- `docs/`：设计、试用说明和验证记录。

## 当前边界

旧版交互规则测试数据故意包含风险组合和重复药物，不能作为处方；新版默认示例不预设药物。所有规则标为 demo；安全提示保留规则版本、证据来源和触发记录。未命中规则不代表安全；不诊断疾病、不推荐处方药、不自动改剂量、停药或换药。饮食评分仅对少量食物和过敏名称做字典匹配，不能判断过敏安全性；妊娠、肾功能剂量等尚不参与安全判断。

仅支持每天固定时刻的用药计划，尚无系统推送/闹钟、按需用药、隔日方案或跨日延迟。停用操作只是用户维护记录，不是系统临床决策。当前计划按现有药物记录生成；历史接口保留已登记服药事件和当时药物快照，不重建每一天的旧处方。每个时刻保留最新登记状态，尚不是完整审计日志。

疾病监测和餐点时刻为演示安排，不能代替个人已确认的监测计划。偏好和过敏信息会传入计划，但未生成食谱。当前无登录与用户隔离授权，只适合本机虚拟数据试用。
