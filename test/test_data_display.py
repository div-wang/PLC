#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据读取与显示功能测试用例
对应测试用例：DATA-001到DATA-006
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
import json
import db
from home import HomePage
from modbus import ModbusPage


class TestDataDisplay:
    """数据显示测试类"""

    @pytest.fixture
    def mock_modbus_state(self):
        """模拟modbus状态数据"""
        import json
        state = {
            "flow": 10.5,
            "load": 25.6,
            "speed": 1.2,
            "flow_unit": "t/h",
            "speed_unit": "m/s",
            "total_weight": 2.5,
            "total_weight_unit": "t",
            "device_total_weight": 100.0,
            "project_id": "test_project_001",
            "time": "2026-03-28 10:00:00"
        }
        with patch('db.meta_get', return_value=json.dumps(state)):
            yield state

    @pytest.fixture
    def test_ring_data(self, temp_db, test_project_id):
        """创建测试环数据"""
        for i in range(1, 11):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=float(i),
                time_str=f"2026-03-28 10:{i:02d}:00",
                total_weight=float(i * 10),
                travel=float(i * 100),
                total_travel=float(i * 1000)
            )
        return test_project_id

    def test_home_page_update_data(self, mock_modbus_state, test_ring_data, qtbot):
        """测试首页数据更新，对应DATA-001"""
        with patch('home.HomePage._active_project_id', return_value=test_ring_data):
            home_page = HomePage()
            
            # 验证摘要数据
            assert home_page.summary_data["实时流量"] == 10.5 / 1000  # kg转t
            assert home_page.summary_data["实时载荷"] == 25.6
            assert home_page.summary_data["实时速度"] == 1.2
            assert home_page.summary_data["当前环重量"] is not None

            # 验证环数据
            assert len(home_page.ring_data["rings"]) == 10
            assert len(home_page.ring_data["weights"]) == 10
            assert len(home_page.ring_data["travels"]) == 10
            assert home_page.ring_data["rings"] == [str(i) for i in range(1, 11)]
            assert home_page.ring_data["weights"] == [float(i) for i in range(1, 11)]

    def test_home_page_chart_generation(self, mock_modbus_state, test_ring_data, qtbot):
        """测试首页图表生成，对应DATA-002"""
        with patch('home.HomePage._active_project_id', return_value=test_ring_data):
            home_page = HomePage()
            chart_html = home_page.create_ring_chart()
            
            # 验证图表包含必要内容
            assert "环号实时出土数据" not in chart_html  # 图表标题在外部
            assert "重量(t)" in chart_html or r"\u91cd\u91cf(t)" in chart_html
            assert all(str(i) in chart_html for i in range(1, 11))  # 所有环号都在图表中

    def test_modbus_table_data(self, temp_db, test_project_id, qtbot):
        """测试Modbus表格数据显示，对应DATA-003"""
        # 插入测试数据
        for i in range(1, 6):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=float(i) * 1.5,
                time_str=f"2026-03-28 10:{i:02d}:00",
                total_weight=float(i * 10),
                travel=float(i * 100),
                total_travel=float(i * 1000)
            )

        with patch('modbus._active_project_id', return_value=test_project_id):
            modbus_page = ModbusPage()
            
            # 验证表格数据
            records = db.recent_rings(test_project_id, 1000)
            assert len(records) == 5
            
            # 验证表格控件
            assert modbus_page.tbl.rowCount() == 5
            assert modbus_page.tbl.item(0, 0).text() == "5"  # 降序排列
            assert modbus_page.tbl.item(0, 1).text() == "7.500"

    def test_data_accuracy(self, mock_modbus_state, qtbot):
        """测试数据准确性，对应DATA-004"""
        # 模拟设备返回值
        mock_modbus_state["device_total_weight"] = 123.456
        mock_modbus_state["speed"] = 0.85
        mock_modbus_state["flow"] = 10.5555
        
        import json
        with patch('db.meta_get', return_value=json.dumps(mock_modbus_state)):
            with patch('home.HomePage._active_project_id', return_value="test_project"):
                home_page = HomePage()
                
                # 验证单位转换：流量kg转t
                assert home_page.summary_data["实时流量"] == 10.5555 / 1000
                # 验证速度值正确
                assert home_page.summary_data["实时速度"] == 0.85

    def test_data_update_refresh(self, mock_modbus_state, test_ring_data, qtbot):
        """测试数据定时刷新，对应DATA-005"""
        with patch('db.meta_get') as mock_meta_get:
            import json
            # 第一次数据
            mock_meta_get.return_value = json.dumps({
                "flow": 10.0,
                "total_weight": 1.0,
                "device_total_weight": 100.0,
                "project_id": test_ring_data
            })
            
            with patch('home.HomePage._active_project_id', return_value=test_ring_data):
                home_page = HomePage()
                initial_weight = home_page.summary_data["当前环重量"]
                
                # 第二次数据更新
                mock_meta_get.return_value = json.dumps({
                    "flow": 20.0,
                    "total_weight": 2.0,
                    "device_total_weight": 110.0,
                    "project_id": test_ring_data
                })
                
                # 手动触发定时器更新
                home_page.update_data()
                
                assert home_page.summary_data["当前环重量"] != initial_weight
                assert home_page.summary_data["实时流量"] == 20.0 / 1000

    def test_abnormal_data_handling(self):
        """测试异常数据处理，对应DATA-006"""
        with patch('home.app_storage.load_json') as mock_load:
            # 异常数据
            mock_load.return_value = {
                "flow": "invalid",  # 字符串类型
                "load": None,
                "speed": float('nan'),
                "total_weight": float('inf'),
                "project_id": "test_project"
            }
            
            home_page = HomePage()
            
            # 验证异常数据被正确处理
            assert home_page.summary_data["实时流量"] is None
            assert home_page.summary_data["实时载荷"] is None
            assert home_page.summary_data["实时速度"] is None
            assert home_page.summary_data["当前环重量"] is None or home_page.summary_data["当前环重量"] == 0.0

    def test_modbus_table_pagination(self, temp_db, test_project_id, qtbot):
        """测试表格分页功能"""
        # 插入25条数据（3页）
        for i in range(1, 26):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=1.0,
                time_str=f"2026-03-28 10:{i%60:02d}:00",
                total_weight=10.0,
                travel=100.0,
                total_travel=1000.0
            )
            
        with patch('modbus._active_project_id', return_value=test_project_id):
            modbus_page = ModbusPage()
            
            # 第一页
            assert modbus_page.pg == 1
            assert modbus_page.tbl.rowCount() == 10
            assert modbus_page.tbl.item(0, 0).text() == "25"
            
            # 下一页
            modbus_page.chg_pg(1)
            assert modbus_page.pg == 2
            assert modbus_page.tbl.rowCount() == 10
            assert modbus_page.tbl.item(0, 0).text() == "15"
            
            # 下一页 (最后一页)
            modbus_page.chg_pg(1)
            assert modbus_page.pg == 3
            assert modbus_page.tbl.rowCount() == 5
            assert modbus_page.tbl.item(0, 0).text() == "5"
            
            # 超过总页数
            modbus_page.chg_pg(1)
            assert modbus_page.pg == 3
