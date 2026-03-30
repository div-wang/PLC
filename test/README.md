# 测试用例使用说明

## 环境准备
1. 安装测试依赖：
```bash
pip install pytest
```

2. 确保项目根目录在Python路径中。

## 运行测试
### 运行所有测试
```bash
pytest
```

### 运行指定模块测试
```bash
# 数据库操作测试
pytest test/test_db_operations.py -v

# 环号操作测试
pytest test/test_ring_operations.py -v

# Modbus连接测试
pytest test/test_modbus_connection.py -v

# 数据显示测试
pytest test/test_data_display.py -v
```

### 生成测试报告
```bash
pytest --html=test_report.html --self-contained-html
```

## 测试覆盖范围
| 测试文件 | 测试用例数 | 对应功能模块 |
|----------|------------|--------------|
| test_db_operations.py | 8 | 数据库CRUD操作、环记录增删改查 |
| test_ring_operations.py | 8 | 上一环、下一环功能、业务逻辑校验 |
| test_modbus_connection.py | 7 | Modbus连接、数据读取、状态显示 |
| test_data_display.py | 7 | 首页数据、图表、Modbus表格显示 |
| **合计** | **30** | |

## 测试特性
- 每个测试用例使用独立的临时数据库，不会影响真实数据
- 自动备份和恢复原有数据库
- 所有测试基于pytest框架，支持断言和mock测试
- 完全覆盖《系统功能测试用例》文档中的所有测试场景
