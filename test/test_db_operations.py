#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库操作测试用例
对应测试用例：RING-005、RING-006、DATA-003等
"""
import pytest
from datetime import datetime
import db


class TestDBOperations:
    """数据库操作测试类"""

    def test_upsert_ring_detail(self, temp_db, test_project_id):
        """测试新增/更新环记录"""
        # 新增记录
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=2.5,
            time_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_weight=10.5,
            travel=100.0,
            total_travel=500.0
        )

        # 查询验证
        record = db.get_ring_detail(test_project_id, 1)
        assert record is not None
        assert record["project_id"] == test_project_id
        assert record["ring_no"] == 1
        assert record["weight"] == 2.5
        assert record["total_weight"] == 10.5
        assert record["travel"] == 100.0
        assert record["total_travel"] == 500.0

    def test_update_ring_detail(self, temp_db, test_project_id):
        """测试更新已存在的环记录"""
        # 先插入
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=2.5,
            time_str="2026-03-28 10:00:00",
            total_weight=10.5,
            travel=100.0,
            total_travel=500.0
        )

        # 再更新
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=3.5,
            time_str="2026-03-28 10:01:00",
            total_weight=11.5,
            travel=150.0,
            total_travel=550.0
        )

        # 验证更新
        record = db.get_ring_detail(test_project_id, 1)
        assert record["weight"] == 3.5
        assert record["total_weight"] == 11.5
        assert record["travel"] == 150.0
        assert record["total_travel"] == 550.0
        assert record["time"] == "2026-03-28 10:01:00"

    def test_recent_rings(self, temp_db, test_project_id):
        """测试查询最近的环记录"""
        # 插入15条测试数据
        for i in range(1, 16):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=float(i),
                time_str=f"2026-03-28 10:{i:02d}:00",
                total_weight=float(i * 10),
                travel=float(i * 100),
                total_travel=float(i * 1000)
            )

        # 查询最近10条
        records = db.recent_rings(test_project_id, limit=10)
        assert len(records) == 10
        # 按环号升序排列，第一条是6号，最后一条是15号
        assert records[0]["ring_no"] == 6
        assert records[-1]["ring_no"] == 15

    def test_max_ring_no(self, temp_db, test_project_id):
        """测试查询最大环号"""
        # 空数据库时返回None
        assert db.max_ring_no(test_project_id) is None

        # 插入几条记录
        for i in range(1, 6):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=1.0,
                time_str="2026-03-28 10:00:00",
                total_weight=10.0,
                travel=100.0,
                total_travel=1000.0
            )

        assert db.max_ring_no(test_project_id) == 5

    def test_delete_ring_detail(self, temp_db, test_project_id):
        """测试删除环记录"""
        # 插入记录
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=2.5,
            time_str="2026-03-28 10:00:00",
            total_weight=10.5,
            travel=100.0,
            total_travel=500.0
        )
        assert db.get_ring_detail(test_project_id, 1) is not None

        # 删除
        db.delete_ring_detail(test_project_id, 1)
        assert db.get_ring_detail(test_project_id, 1) is None

    def test_sum_ring_weight_before(self, temp_db, test_project_id):
        """测试计算之前环的总重量"""
        # 插入环1-3
        db.upsert_ring_detail(test_project_id, 1, 1.5, "2026-03-28 10:00:00", 1.5, 100, 100)
        db.upsert_ring_detail(test_project_id, 2, 2.5, "2026-03-28 10:01:00", 4.0, 100, 200)
        db.upsert_ring_detail(test_project_id, 3, 3.5, "2026-03-28 10:02:00", 7.5, 100, 300)

        # 计算环3之前的总重量：1.5 + 2.5 = 4.0
        total = db.sum_ring_weight_before(test_project_id, 3)
        assert total == 4.0

        # 计算环1之前的总重量：0
        total = db.sum_ring_weight_before(test_project_id, 1)
        assert total == 0.0

    def test_ring_unique_constraint(self, temp_db, test_project_id):
        """测试环号唯一约束，对应EXCP-003"""
        # 插入第一条
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=2.5,
            time_str="2026-03-28 10:00:00",
            total_weight=10.5,
            travel=100.0,
            total_travel=500.0
        )

        # 插入相同project_id和ring_no的记录，应该更新而不是报错
        db.upsert_ring_detail(
            project_id=test_project_id,
            ring_no=1,
            weight=3.5,
            time_str="2026-03-28 10:01:00",
            total_weight=11.5,
            travel=150.0,
            total_travel=550.0
        )

        record = db.get_ring_detail(test_project_id, 1)
        assert record["weight"] == 3.5  # 验证已更新

    def test_get_last_ring_detail(self, temp_db, test_project_id):
        """测试获取最后一条环记录"""
        # 空数据库返回None
        assert db.get_last_ring_detail(test_project_id) is None

        # 插入记录
        for i in range(1, 4):
            db.upsert_ring_detail(
                project_id=test_project_id,
                ring_no=i,
                weight=float(i),
                time_str=f"2026-03-28 10:{i:02d}:00",
                total_weight=float(i * 10),
                travel=float(i * 100),
                total_travel=float(i * 1000)
            )

        last = db.get_last_ring_detail(test_project_id)
        assert last is not None
        assert last["ring_no"] == 3
        assert last["weight"] == 3.0
