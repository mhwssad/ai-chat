# 定时任务模块架构文档

## 概述

定时任务模块负责管理和执行定时任务，支持 Cron 表达式调度、间隔调度和一次性任务。

## 模块职责划分

### 1. types.py - 数据类型定义层

**职责：** 定义所有数据类型和枚举

**包含：**
- `TaskStatus` - 任务状态枚举（active/paused/completed/failed/disabled）
- `TaskType` - 任务类型枚举（tool_call/llm_prompt/system_event）
- `ExecutionStatus` - 执行状态枚举（running/success/failed/timeout/cancelled）
- `CronSpec` - Cron 规范（含验证逻辑）
- `TaskConfig` - 任务配置（含序列化）
- `ScheduledTaskInfo` - 对外暴露的任务信息
- `TaskExecutionResult` - 执行结果

**单一职责：** ✅ 只负责数据类型定义

---

### 2. store.py - 持久化存储层

**职责：** 纯数据访问，只负责 CRUD 操作

**包含：**
- `SchedulerStore` - 封装数据库操作
  - 任务的增删改查
  - 执行日志的增删改查
  - 统计查询

**单一职责：** ✅ 只负责数据持久化，不包含业务逻辑

**不负责：**
- ❌ 业务逻辑（由 SchedulerService 处理）
- ❌ 状态转换（由 SchedulerService 处理）
- ❌ 重试逻辑（由 SchedulerService 处理）

---

### 3. executor.py - 任务执行器

**职责：** 纯任务执行，只负责执行不同类型的任务

**包含：**
- `TaskExecutor` - 执行不同类型的任务
  - 工具调用执行
  - LLM 提示执行
  - 系统事件执行

**单一职责：** ✅ 只负责任务执行

**不负责：**
- ❌ 执行日志记录（由 SchedulerManager 处理）
- ❌ 任务统计更新（由 SchedulerService 处理）

---

### 4. manager.py - 调度管理器

**职责：** 纯调度引擎，只负责调度循环和任务执行触发

**包含：**
- `SchedulerManager` - 调度循环管理
  - 启动/停止调度器
  - 检查到期任务
  - 触发任务执行
  - 记录执行日志
  - 计算下次执行时间

**单一职责：** ✅ 只负责调度循环

**不负责：**
- ❌ 任务 CRUD 操作（由 SchedulerService 处理）
- ❌ 状态管理（由 SchedulerService 处理）
- ❌ 业务逻辑（由 SchedulerService 处理）

---

### 5. service.py - 业务服务层

**职责：** 完整的业务服务层，负责所有业务逻辑

**包含：**
- `SchedulerService` - 业务服务门面
  - 参数验证
  - 业务规则检查
  - 任务 CRUD 操作
  - 状态管理（enable/disable/pause/resume）
  - 执行统计更新（重试逻辑、状态转换）
  - 日志查询

**单一职责：** ✅ 只负责业务逻辑

**不负责：**
- ❌ 调度循环（由 SchedulerManager 处理）
- ❌ 任务执行（由 TaskExecutor 处理）
- ❌ 数据持久化（由 SchedulerStore 处理）

---

### 6. storage/scheduler_models.py - ORM 模型

**职责：** 定义数据库表结构

**包含：**
- `ScheduledTask` - 定时任务表
- `TaskExecutionLog` - 任务执行日志表

**单一职责：** ✅ 只负责 ORM 模型定义

---

### 7. storage/scheduler_repository.py - 数据仓库

**职责：** 提供类型安全的数据库操作

**包含：**
- `ScheduledTaskRepository` - 任务仓库
- `TaskExecutionLogRepository` - 执行日志仓库

**单一职责：** ✅ 只负责数据访问

---

### 8. tools/builtins/scheduler_tools.py - 工具层

**职责：** 提供 LLM 可调用的工具接口

**包含：**
- `CronCreate` - 创建定时任务
- `CronDelete` - 删除定时任务
- `CronList` - 列出定时任务

**单一职责：** ✅ 只负责工具接口

---

### 9. container.py - DI 容器

**职责：** 依赖注入容器，管理实例创建和依赖关系

**单一职责：** ✅ 只负责依赖注入

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    SchedulerService                         │
│  (业务逻辑层：参数验证、权限检查、业务规则)                      │
│  - 任务 CRUD 操作                                            │
│  - 状态管理                                                  │
│  - 执行统计更新                                              │
│  - 日志查询                                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    SchedulerManager                         │
│  (调度引擎：纯调度循环、生命周期管理)                           │
│  - 启动/停止调度器                                            │
│  - 检查到期任务                                               │
│  - 触发任务执行                                               │
│  - 记录执行日志                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────┐
│    TaskExecutor      │
│  (纯任务执行)         │
│  - 工具调用执行        │
│  - LLM 提示执行       │
│  - 系统事件执行        │
└──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      SchedulerStore                         │
│  (纯数据访问：CRUD 操作，无业务逻辑)                           │
│  - 任务增删改查                                               │
│  - 执行日志增删改查                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   SchedulerRepository                       │
│  (类型安全的数据访问)                                         │
└─────────────────────────────────────────────────────────────┘
```

## 数据流

### 1. 创建任务

```
用户调用 → SchedulerService.create_cron_task()
         → 验证参数
         → 检查名称唯一性
         → 计算首次执行时间
         → SchedulerStore.create_task()
         → SchedulerRepository.create()
         → 返回 ScheduledTaskInfo
```

### 2. 调度执行

```
SchedulerManager._scheduler_loop()
         → SchedulerStore.get_due_tasks()
         → 遍历到期任务
         → SchedulerManager._execute_task()
         → SchedulerStore.create_execution_log()
         → TaskExecutor.execute()
         → SchedulerStore.update_execution_log()
         → SchedulerService.update_task_after_execution()
         → 更新任务统计和状态
```

### 3. 状态管理

```
用户调用 → SchedulerService.enable_task()
         → 检查当前状态
         → 计算下次执行时间
         → SchedulerStore.update_task_fields()
         → 返回更新后的任务
```

## 职责边界

### SchedulerService vs SchedulerManager

| 功能 | SchedulerService | SchedulerManager |
|------|-----------------|------------------|
| 任务 CRUD | ✅ | ❌ |
| 状态管理 | ✅ | ❌ |
| 执行统计 | ✅ | ❌ |
| 日志查询 | ✅ | ❌ |
| 调度循环 | ❌ | ✅ |
| 任务执行 | ❌ | ✅ |
| 执行日志 | ❌ | ✅ |

### SchedulerStore vs SchedulerRepository

| 功能 | SchedulerStore | SchedulerRepository |
|------|---------------|---------------------|
| 业务逻辑 | ❌ | ❌ |
| 事务管理 | ✅ | ❌ |
| 类型安全 | ❌ | ✅ |
| 查询构建 | ✅ | ✅ |

## 扩展点

### 1. 新增任务类型

在 `TaskType` 枚举中添加新类型，在 `TaskExecutor` 中添加对应的执行方法。

### 2. 新增调度策略

在 `SchedulerManager` 中扩展调度逻辑，或引入新的调度策略类。

### 3. 新增验证规则

在 `SchedulerService` 中添加新的验证方法。

### 4. 新增存储后端

实现新的 `SchedulerStore` 或 `SchedulerRepository`。
