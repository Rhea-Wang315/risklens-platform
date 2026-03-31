# RiskLens Platform - 2周冲刺计划
**目标**: 把risklens-platform做成一个能demo的完整系统，结合whale-sentry展示end-to-end风控能力

**核心思路**: Detection (whale-sentry) → Decision (risklens-platform) → Impact Analysis (case study)

---

## 为什么要这么做?

### 当前问题
- whale-sentry: 101个测试，检测出$46.8M攻击 ✅
- risklens-platform: 只有3个commit，跑不起来 ❌
- **Gap**: 没有展示"检测到攻击后，应该做什么决策"

### Hiring Manager想看什么?
1. **Complete story**: 不只是"我能检测攻击"，而是"我能检测+决策+量化impact"
2. **Business impact**: "如果用了我的系统，能减少多少损失?"
3. **Production-ready**: 能跑、能demo、有测试、有文档

### 这个计划如何帮你?
- **Week 1**: 把risklens-platform做到能work (FastAPI + 规则引擎 + 数据库)
- **Week 2**: 用whale-sentry的真实数据，做一个完整的case study
- **结果**: 一个live demo + 一篇incident report + 一个demo video

---

## Week 1: 让risklens-platform跑起来

### 目标
把risklens-platform做成一个**能接收whale-sentry alerts并做出决策**的系统。

**不做的事情**:
- ❌ Kafka streaming
- ❌ Kubernetes deployment  
- ❌ React dashboard
- ❌ 复杂的ML模型

**只做核心**:
- ✅ FastAPI service (接收alerts)
- ✅ Rule engine (3个基础规则)
- ✅ PostgreSQL (存储decisions)
- ✅ Streamlit dashboard (简单可视化)

---

### Day 1-2: Database + Rule Engine

#### 任务
1. 完成database models (已有框架，需要测试)
2. 实现3个基础规则:
   - **Rule 1**: High score + low counterparty diversity → FREEZE
   - **Rule 2**: Medium score + high volume → WARN
   - **Rule 3**: Low score → OBSERVE
3. 写unit tests (coverage > 80%)

#### 验收标准
```bash
# 能跑通这些测试
pytest tests/test_models.py -v
pytest tests/test_rules.py -v
pytest tests/test_scoring.py -v

# Database能正常创建
docker-compose up -d
python -c "from risklens.db.models import Base; from risklens.db.session import engine; Base.metadata.create_all(engine)"
```

#### Commit策略
- Commit 1: "feat: Complete database models with audit trail"
- Commit 2: "feat: Implement rule engine with 3 baseline rules"
- Commit 3: "test: Add unit tests for rules and scoring (80%+ coverage)"

---

### Day 3-4: FastAPI Service

#### 任务
1. 实现FastAPI endpoints:
   - `POST /api/v1/evaluate` - 接收whale-sentry alert，返回decision
   - `GET /api/v1/decisions/{decision_id}` - 查询decision
   - `GET /api/v1/decisions?address=0x...` - 查询某地址的所有decisions
2. 集成whale-sentry (作为library)
3. 写integration tests

#### 验收标准
```bash
# 能启动服务
uvicorn risklens.api.main:app --reload

# 能接收alert并返回decision
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d @examples/example_alert.json

# 返回类似:
# {
#   "decision_id": "dec_abc123",
#   "action": "FREEZE",
#   "risk_level": "HIGH",
#   "confidence": 0.95,
#   "rationale": "High-confidence wash trading detected..."
# }
```

#### Commit策略
- Commit 4: "feat: Implement FastAPI service with core endpoints"
- Commit 5: "feat: Integrate whale-sentry detection engine"
- Commit 6: "test: Add integration tests for API endpoints"

---

### Day 5-7: Streamlit Dashboard + End-to-End Test

#### 任务
1. 创建简单的Streamlit dashboard:
   - 输入: 上传whale-sentry的detection results (CSV)
   - 处理: 批量调用risklens API
   - 输出: 展示decisions (表格 + 图表)
2. 用whale-sentry的**真实数据**测试end-to-end flow
3. 部署到Render/Streamlit Cloud (免费tier)

#### 验收标准
```bash
# 能启动dashboard
streamlit run dashboard/app.py

# 能上传whale-sentry的results.csv
# 能看到每个alert对应的decision
# 能看到统计: 多少FREEZE, 多少WARN, 多少OBSERVE
```

#### Commit策略
- Commit 7: "feat: Add Streamlit dashboard for decision visualization"
- Commit 8: "test: Validate end-to-end flow with whale-sentry data"
- Commit 9: "docs: Update README with demo instructions"

---

## Week 2: Case Study + Demo

### 目标
用whale-sentry检测到的**真实攻击数据**，展示risklens-platform的business impact。

---

### Day 8-10: 数据分析 + Impact Quantification

#### 任务
1. 从whale-sentry拿到检测结果:
   - 19,416 transactions analyzed
   - 3,216 attacks detected
   - $46.8M total profit extracted
2. 用risklens-platform对这些attacks做决策
3. 计算business impact:
   - 如果FREEZE了这些地址，能减少多少损失?
   - 如果WARN了这些地址，能提前多久发现?
   - False positive rate是多少?

#### 分析框架
```python
# 伪代码
for alert in whale_sentry_results:
    decision = risklens.evaluate(alert)
    
    if decision.action == "FREEZE":
        # 假设freeze后，后续交易被阻止
        prevented_loss += alert.subsequent_transactions_volume
    
    if decision.action == "WARN":
        # 假设warn后，人工review需要1小时
        detection_time_saved += 1 hour

# 输出
print(f"Total prevented loss: ${prevented_loss:,.2f}")
print(f"Average detection time: {avg_detection_time} seconds")
print(f"False positive rate: {fp_rate:.2%}")
```

#### 输出
一个Jupyter notebook: `analysis/impact_analysis.ipynb`

---

### Day 11-12: Incident Report

#### 任务
写一篇**professional incident report**，模拟"如果当时有这个系统"的场景。

#### 结构
```markdown
# Incident Report: Uniswap V3 Sandwich Attack Analysis
**Date**: [选一个whale-sentry检测到的高价值攻击]
**Attack Type**: Sandwich Attack
**Total Loss**: $X.X million

## Executive Summary
- What happened
- How our system would have detected it
- Potential loss prevention

## Detection Timeline
- T-0: Attack transaction submitted
- T+2s: whale-sentry detected anomaly (score: 0.95)
- T+3s: risklens-platform evaluated → FREEZE decision
- T+5s: Alert sent to operator

## Decision Rationale
- Rule matched: High score + low counterparty diversity
- Risk score: 0.95 (CRITICAL)
- Confidence: 0.98
- Recommended action: FREEZE account immediately

## Business Impact
- **Without system**: $X.X million lost
- **With system**: $X.X million prevented (assuming 5s freeze time)
- **ROI**: X,XXX% (system cost vs. prevented loss)

## Lessons Learned
- Detection latency: 2 seconds (acceptable)
- Decision latency: 1 second (acceptable)
- False positive rate: X% (needs improvement)

## Recommendations
- [具体的改进建议]
```

#### 输出
`docs/INCIDENT_REPORT_UNISWAP_SANDWICH.md`

---

### Day 13-14: Demo Video + Portfolio Update

#### 任务
1. 录制一个**5分钟demo video**:
   - 0:00-0:30: Problem statement
   - 0:30-2:00: System architecture (whale-sentry → risklens)
   - 2:00-4:00: Live demo (上传数据 → 看到decisions)
   - 4:00-5:00: Business impact (prevented loss, detection time)
2. 更新portfolio:
   - README.md (加入demo video链接)
   - LinkedIn (更新project section)
   - Resume (加入quantified impact)

#### Demo Script
```
"Hi, I'm Rhea. I built a complete risk control system for Web3.

[Screen: Architecture diagram]
The system has two parts:
- whale-sentry detects suspicious patterns (like sandwich attacks)
- risklens-platform makes decisions (freeze, warn, or observe)

[Screen: Streamlit dashboard]
Let me show you how it works. I'm uploading real data from Uniswap V3...
[Upload CSV]
...and you can see, out of 3,216 detected attacks, the system recommended:
- 1,200 FREEZE (high confidence)
- 800 WARN (medium confidence)  
- 1,216 OBSERVE (low risk)

[Screen: Impact analysis]
If this system was deployed, it could have prevented $X million in losses.
The average detection time is 2 seconds - fast enough to stop attacks in real-time.

[Screen: Incident report]
I also did a deep-dive on one specific attack...
[Show report]

This is the kind of system I want to build for Web3 companies.
Thanks for watching!"
```

#### 输出
- Video: 上传到YouTube (unlisted)
- Link: 加到README.md

---

## Commit策略总结

### Week 1 (9 commits)
1. feat: Complete database models with audit trail
2. feat: Implement rule engine with 3 baseline rules
3. test: Add unit tests for rules and scoring (80%+ coverage)
4. feat: Implement FastAPI service with core endpoints
5. feat: Integrate whale-sentry detection engine
6. test: Add integration tests for API endpoints
7. feat: Add Streamlit dashboard for decision visualization
8. test: Validate end-to-end flow with whale-sentry data
9. docs: Update README with demo instructions

### Week 2 (5 commits)
10. analysis: Add impact quantification notebook
11. docs: Add incident report for Uniswap sandwich attack
12. docs: Add demo video and update portfolio
13. feat: Deploy dashboard to Streamlit Cloud
14. docs: Final polish - README, LinkedIn, Resume

**Total: 14 commits in 2 weeks** (不是每天commit，而是每个milestone commit)

---

## 验收标准 (2周后)

### Technical
- [ ] risklens-platform能跑 (FastAPI + PostgreSQL + Streamlit)
- [ ] 能接收whale-sentry alerts并返回decisions
- [ ] 测试覆盖率 > 80%
- [ ] Live dashboard deployed (public URL)

### Business
- [ ] 有一个完整的incident report (quantified impact)
- [ ] 有一个5分钟demo video
- [ ] Portfolio updated (README + LinkedIn + Resume)

### Job Search
- [ ] 能在面试中demo这个系统 (5分钟)
- [ ] 能回答"你的系统如何创造business value?" (用数据说话)
- [ ] 能展示end-to-end thinking (detection → decision → impact)

---

## 常见问题

### Q1: 这个计划会不会太赶?
**A**: 不会。因为:
- whale-sentry已经完成 (101 tests passing)
- risklens-platform已经有框架 (database models, rule engine skeleton)
- 你只需要**把它们连起来**，不是从零开始

### Q2: 我需要每天commit吗?
**A**: **不需要**。Commit的原则是:
- 每个**功能完成**时commit (不是每天)
- 每个commit要有**清晰的message** (feat/test/docs)
- 不要为了"绿点"而commit (这是junior mindset)

### Q3: 如果Week 1没做完怎么办?
**A**: **没关系**。重要的是:
- Week 1结束时，系统能**基本跑起来** (哪怕有bug)
- Week 2可以边修bug边做case study
- **Deadline是flexible的**，但不要拖超过3周

### Q4: 我需要做Kafka/K8s吗?
**A**: **Week 1-2不需要**。因为:
- 这些是"nice to have"，不是"must have"
- Hiring manager更care你能不能**快速deliver value**
- 如果Week 3有时间，再加这些feature

### Q5: 这个计划和我的ROADMAP冲突吗?
**A**: **不冲突**。这个计划是:
- ROADMAP的Phase 1 (Decision Engine) ✅
- 加上一个**real-world validation** (case study) ✅
- Phase 2-5可以**之后再做** (如果有时间)

---

## 最后的话

**这个计划的核心思想**:
1. **Stop building, start shipping** - 不要追求完美，先做出能用的
2. **Show business impact** - 不要只展示技术，要展示价值
3. **Tell a complete story** - Detection → Decision → Impact (end-to-end)

**记住**:
- Hiring manager不care你的代码有多优雅
- 他们care你能不能**解决他们的问题**
- 你的目标是证明:**我能帮你减少损失/提高效率**

**Go ship it!** 🚀

---

*Last updated: Feb 28, 2026*
