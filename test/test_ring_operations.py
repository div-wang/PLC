#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
上一环/下一环功能测试用例
对应测试用例：RING-001到RING-009、EXCP-004等
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import db
from modbus import ModbusPage


class TestRingOperations:
    """环号操作测试类"""

    @pytest.fixture
    def mock_modbus_page(self, temp_db, test_project_id, qtbot):
        """创建模拟的ModbusPage对象"""
        with patch('modbus._active_project_id', return_value=test_project_id):  
            with patch('PyQt5.QtWidgets.QMessageBox.warning', return_value=True):
                page = ModbusPage(user_role="admin")
                # 模拟已连接状态
                page.cli = MagicMock()
                page.cli.is_connected.return_value = True
                page.last_tot_wt = 100.0
                page.travel_tot = 1000.0
                page.ring_no = 1
                page.ring_wt = 2.5  # >1吨，满足下一环条件
                yield page

    def test_next_ring_normal(self, mock_modbus_page, test_project_id):
        """测试正常下一环操作，对应RING-001"""
        # 先插入初始环
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=2.5,
            time_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_weight=100.0,
            travel=100.0,
            total_travel=1000.0
        )

        # 执行下一环
        initial_ring_no = mock_modbus_page.ring_no
        mock_modbus_page.next_ring()
        print("ALL RINGS:", db.recent_rings(test_project_id, 100))

        # 验证
        assert mock_modbus_page.ring_no == initial_ring_no + 1
        # 新环已创建
        new_ring = db.get_ring_detail(test_project_id, initial_ring_no + 1)
        assert new_ring is not None
        assert new_ring["weight"] == 0.0
        assert new_ring["travel"] == 0.0
        # 原来的环数据已保存
        old_ring = db.get_ring_detail(test_project_id, initial_ring_no)
        assert old_ring is not None
        assert old_ring["weight"] == 2.5

    def test_next_ring_not_connected(self, mock_modbus_page):
        """测试未连接时点击下一环，对应RING-003"""
        mock_modbus_page.cli = None  # 模拟未连接

        with patch.object(mock_modbus_page, 'warn') as mock_warning:
            mock_modbus_page.next_ring()
            mock_warning.assert_called_once_with("Modbus未连接")

    def test_next_ring_weight_too_low(self, mock_modbus_page):
        """测试重量不足时点击下一环，对应RING-004"""
        mock_modbus_page.ring_wt = 0.5  # 小于1吨

        with patch.object(mock_modbus_page, 'warn') as mock_warning:
            mock_modbus_page.next_ring()
            mock_warning.assert_called_once_with("当前环重量≤1t，不可切换")

    def test_prev_ring_normal(self, mock_modbus_page, test_project_id):
        """测试正常上一环操作，对应RING-002"""
        # 插入两条环记录
        db.upsert_ring_detail(test_project_id, 1, 2.0, "2026-03-28 10:00:00", 97.5, 800, 800)
        db.upsert_ring_detail(test_project_id, 2, 2.5, "2026-03-28 10:01:00", 100.0, 200, 1000)
        mock_modbus_page.ring_no = 2
        mock_modbus_page.ring_wt = 2.5

        # 模拟确认操作
        with patch.object(mock_modbus_page, 'confirm', return_value=True):
            mock_modbus_page.prev_ring()

        # 验证：环号变为1，数据合并
        assert mock_modbus_page.ring_no == 1
        merged_ring = db.get_ring_detail(test_project_id, 1)
        assert merged_ring is not None
        assert merged_ring["weight"] == 2.0 + 2.5 == 4.5  # 重量合并
        assert merged_ring["total_weight"] == 100.0  # 总重量使用原来环2的
        assert merged_ring["travel"] == 800 + 200 == 1000  # 行程合并
        # 环2已被删除
        assert db.get_ring_detail(test_project_id, 2) is None

    def test_prev_ring_not_enough_records(self, mock_modbus_page, test_project_id):
        """测试记录不足时上一环，对应RING-007"""
        # 只有1条记录
        db.upsert_ring_detail(test_project_id, 1, 2.5, "2026-03-28 10:00:00", 100.0, 200, 1000)
        mock_modbus_page.ring_no = 1

        with patch.object(mock_modbus_page, 'confirm', return_value=True):
            with patch.object(mock_modbus_page, 'warn') as mock_warning:
                mock_modbus_page.prev_ring()
                mock_warning.assert_called_once_with("没有上一环")

    def test_prev_ring_user_cancel(self, mock_modbus_page, test_project_id):
        """测试用户取消上一环操作"""
        # 插入两条记录
        db.upsert_ring_detail(test_project_id, 1, 2.0, "2026-03-28 10:00:00", 97.5, 800, 800)
        db.upsert_ring_detail(test_project_id, 2, 2.5, "2026-03-28 10:01:00", 100.0, 200, 1000)
        mock_modbus_page.ring_no = 2

        # 模拟用户取消
        with patch.object(mock_modbus_page, 'confirm', return_value=False):
            mock_modbus_page.prev_ring()

        # 验证无变化
        assert mock_modbus_page.ring_no == 2
        assert db.get_ring_detail(test_project_id, 1) is not None
        assert db.get_ring_detail(test_project_id, 2) is not None

    def test_ring_operation_empty_database(self, mock_modbus_page, test_project_id):
        """测试空数据库时的环操作，对应EXCP-004"""
        # 数据库为空
        assert db.max_ring_no(test_project_id) is None

        # 下一环应该失败（重量不足）
        mock_modbus_page.ring_wt = 0.0
        with patch.object(mock_modbus_page, 'warn') as mock_warning:
            mock_modbus_page.next_ring()
            mock_warning.assert_called_once_with("当前环重量≤1t，不可切换")

        with patch.object(mock_modbus_page, 'confirm', return_value=True):
            with patch.object(mock_modbus_page, 'warn') as mock_warning:
                mock_modbus_page.prev_ring()
                mock_warning.assert_called_once_with("没有上一环")

    def test_next_ring_data_persistence(self, mock_modbus_page, test_project_id):
        """测试下一环数据持久化，对应RING-005"""
        initial_total = mock_modbus_page.last_tot_wt
        initial_travel = mock_modbus_page.travel_tot

        # 执行下一环
        mock_modbus_page.ring_wt = 2.5
        mock_modbus_page.next_ring()

        # 验证数据库中的数据
        new_ring = db.get_ring_detail(test_project_id, 2)
        assert new_ring is not None
        assert new_ring["total_weight"] == initial_total
        assert new_ring["total_travel"] == initial_travel
        assert new_ring["weight"] == 0.0
        assert new_ring["travel"] == 0.0
        assert len(new_ring["time"]) == 19  # 时间格式正确：YYYY-MM-DD HH:MM:SS
