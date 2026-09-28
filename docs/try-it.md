# 浏览器试用说明

首页：<http://127.0.0.1:8000/>；Swagger：<http://127.0.0.1:8000/docs>。
在 Swagger 展开接口，点 **Try it out**，输入请求后点 **Execute**。

## 新建虚拟患者

POST `/patients`：

```json
{"name":"测试用户","age":35,"sex":"unspecified","height_cm":170,"weight_kg":68,"allergies":[],"dietary_preferences":["清淡"]}
```

记住返回的 `id`，后续填入 `patient_id`。不要直接假定新建的患者 ID 为 1。

## 添加已记录疾病

POST `/patients/{patient_id}/conditions`：

```json
{"disease_code":"hypertension","status":"active","severity":"unspecified","notes":"虚构数据"}
```

也可分别添加 `type2_diabetes`、`hyperlipidemia`、`hyperuricemia`。同一患者同一疾病重复添加返回 409。

## 用药记录与状态

演示药物用于验证软件功能，不代表建议使用。没有真实药理含义的测试药物可输入：

```json
{"drug_name":"演示药 A","generic_name":"demo_a","dose":1,"unit":"片","route":"oral","frequency":"once_daily","administration_time":["08:30"],"meal_relation":"after_meal","start_date":"2026-09-25","end_date":null,"indication":"虚构数据","active":true}
```

药物名不在当前规则字典时，安全检查会返回 `coverage.unknown_drugs`。中英文别名只按字典匹配，不做猜测或模糊识别。

PUT `/patients/{patient_id}/medications/{medication_id}/events` 登记已服：

```json
{"scheduled_date":"2026-09-25","scheduled_time":"08:30","status":"taken","taken_at":"2026-09-25T08:35:00+08:00","notes":"测试登记"}
```

漏服用 `status: "missed"`，不传 `taken_at`。延迟用 `status: "delayed"` 和 `delayed_to: "09:30"`，不传 `taken_at`。延迟仅记录用户选择，不代表补服建议。同一时刻再次登记会更新该条状态，不产生重复服药记录。
修改用药使用 PUT `/patients/{id}/medications/{medication_id}`，需提交完整药物字段；停用记录使用 POST `.../deactivate`。

## 记录健康指标

POST `/patients/{patient_id}/observations`：

```json
{"metric_type":"blood_pressure","systolic":125,"diastolic":80,"unit":"mmHg","measured_at":"2026-09-25T07:30:00+08:00","notes":"虚拟值"}
```

其他指标使用 `value` 字段；单位从 GET `/catalog/observation-types` 查询，不自动转换单位。时间必须包含时区。

## 查看计划和安全检查

- GET `/patients/{patient_id}/care-plan?day=2026-09-25`
- GET `/patients/{patient_id}/nutrition-constraints`
- GET `/patients/{patient_id}/medication-plan?day=2026-09-25`
- GET `/patients/{patient_id}/medication-history`
- GET `/patients/{patient_id}/safety-check?foods=grapefruit&foods=high_sodium_food`

`foods` 是此次检查的饮食输入，不是已持久化的饮食日记。未传 foods 时，相关药食/病食规则会显示 `potential_not_recorded` 条件提醒，不能理解为已经食用。规则的 `matched_data` 给出实际匹配到的记录，`evidence_source` 给出来源，`demo` 标识演示性质。

高风险提示建议咨询医生或药师，接口不会自动修改任何药物记录。
