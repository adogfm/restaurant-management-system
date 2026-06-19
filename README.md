# 餐厅管理系统（Restaurant Management System）

基于 Flask + MySQL 的餐厅后台管理系统，为中小型餐饮企业提供一站式后台管理解决方案，覆盖菜品、订单、顾客、员工、桌台五大核心业务场景。

## 技术栈

- **后端框架**：Python Flask 2.3
- **数据库**：MySQL 8.0
- **模板引擎**：Jinja2
- **前端样式**：Bootstrap
- **开发工具**：PyCharm、Navicat、draw.io

## 主要功能

### 菜品管理
- 菜品增删改查，支持图片上传
- 菜品状态控制（上架/下架）
- 菜品分类管理

### 订单管理
- 创建订单，自动生成订单号（ORD+年月+序号）
- 会员积分自动匹配折扣
- 订单状态跟踪（进行中→已完成）
- 桌台状态联动（下单→占用，完成→释放）
- 订单打印功能

### 顾客管理
- 顾客信息维护（手机号、姓名、性别、生日）
- 积分累计与会员等级自动升级
- 新顾客自动建档

### 员工管理
- 员工档案管理（工号、姓名、职位、薪资、部门）
- 在职状态跟踪

### 桌台管理
- 桌台状态实时更新（空闲/占用/清洁中/预订）
- 按区域可视化展示

## 会员折扣体系

| 会员等级 | 所需积分 | 折扣 |
|---------|---------|------|
| 普通会员 | 0 | 无折扣 |
| 白银会员 | 1000 | 9.5折 |
| 黄金会员 | 2000 | 9.0折 |
| 白金会员 | 5000 | 8.5折 |
| 钻石会员 | 10000 | 8.0折 |

## 数据库设计

- 包含 **6 张数据表**：菜品、订单、顾客、员工、桌台、订单明细
- 建立外键关联，保证数据完整性
- 有历史订单的菜品禁止删除（外键约束）

## 项目结构
restaurant-management-system/
├── app.py # Flask 主应用
├── database.py # 数据库操作封装
├── templates/ # HTML 模板文件
├── static/ # 静态资源（CSS、图片）
├── restaurantdb.sql # 数据库脚本
└── README.md # 项目说明


## 快速开始

### 环境要求
- Python 3.8+
- MySQL 8.0

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/adogfm/restaurant-management-system.git
cd restaurant-management-system

2.安装依赖
pip install flask mysql-connector-python

3.创建数据库（在 MySQL 中执行）
CREATE DATABASE restaurantdb CHARACTER SET utf8mb4;

4.修改 database.py 中的数据库密码（默认是 123456）

5.运行项目
python app.py

6.访问 http://localhost:5000，登录账号：boss / 123456
