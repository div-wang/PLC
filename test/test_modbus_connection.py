#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modbus连接功能测试用例
对应测试用例：CONN-001到CONN-006
"""
import pytest
from unittest.mock import MagicMock, patch, call
from modbus import _RTUSettings, _RTUModbusClient, ModbusPage, load_modbus_settings


class TestModbusConnection:
    """Modbus连接测试类"""

    @pytest.fixture
    def mock_minimalmodbus(self):
        """模拟minimalmodbus库"""
        with patch('minimalmodbus.Instrument') as mock_instr:
            mock_inst = MagicMock()
            mock_instr.return_value = mock_inst
            mock_inst.serial = MagicMock()
            mock_inst.serial.is_open = True
            yield mock_instr

    def test_rtu_client_connect_success(self, mock_minimalmodbus):
        """测试正常连接，对应CONN-001"""
        settings = _RTUSettings(
            unit_id=1,
            timeout_s=1.0,
            serial_port="COM1",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
        )
        client = _RTUModbusClient(settings)

        ok, err = client.connect()
        assert ok is True
        assert err == ""
        assert client.is_connected() is True

        # 验证参数是否正确传递
        mock_minimalmodbus.assert_called_once_with("COM1", 1)
        assert mock_minimalmodbus.return_value.serial.baudrate == 9600
        assert mock_minimalmodbus.return_value.serial.parity == "N"
        assert mock_minimalmodbus.return_value.serial.stopbits == 1
        assert mock_minimalmodbus.return_value.serial.bytesize == 8

    def test_rtu_client_connect_failure(self):
        """测试连接失败，对应CONN-002/CONN-003/CONN-004"""
        settings = _RTUSettings(
            unit_id=1,
            timeout_s=1.0,
            serial_port="INVALID_COM",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
        )
        client = _RTUModbusClient(settings)

        # 模拟连接异常
        with patch('minimalmodbus.Instrument', side_effect=Exception("Port not found")):
            ok, err = client.connect()
            assert ok is False
            assert "Port not found" in err
            assert client.is_connected() is False

    def test_auto_connect(self, qtbot):
        """测试自动重连功能，对应CONN-006"""
        with patch('modbus._RTUModbusClient.connect') as mock_connect:
            with patch('PyQt5.QtCore.QTimer.singleShot'):
                # 前两次失败，第三次成功
                mock_connect.side_effect = [(False, "error"), (False, "error"), (True, "")]
                
                page = ModbusPage()
                page.start_auto_connect(max_attempts=3, interval_ms=100)
                
                assert page._auto_connecting is True
                assert page._auto_attempts == 0

    def test_connection_status_display(self, qtbot):
        """测试连接状态显示，对应CONN-005"""
        page = ModbusPage()
        
        # 连接中状态
        page._set_status_badge("connecting")
        assert page.status_label.text() == "连接中"
        assert "#f5f5f5" in page.status_label.styleSheet()  # 灰色背景

        # 已连接状态
        page._set_status_badge("connected")
        assert page.status_label.text() == "已连接"
        assert "#f6ffed" in page.status_label.styleSheet()  # 绿色背景

        # 未连接/失败状态
        page._set_status_badge("failed")
        assert page.status_label.text() == "未连接"
        assert "#fff2e8" in page.status_label.styleSheet()  # 橙色背景

    def test_read_float32_success(self, mock_minimalmodbus):
        """测试读取float32数据正常"""
        settings = _RTUSettings(
            unit_id=1,
            timeout_s=1.0,
            serial_port="COM1",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
        )
        client = _RTUModbusClient(settings)
        client.connect()

        # 模拟读取返回值
        mock_minimalmodbus.return_value.read_float.return_value = 123.456
        
        value, err = client.read_float32(address=50, byte_order="ABCD")
        assert value == 123.456
        assert err == ""
        mock_minimalmodbus.return_value.read_float.assert_called_once_with(
            50, functioncode=3, number_of_registers=2, byteorder=0
        )

    def test_read_float32_failure(self, mock_minimalmodbus):
        """测试读取数据失败"""
        settings = _RTUSettings(
            unit_id=1,
            timeout_s=1.0,
            serial_port="COM1",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
        )
        client = _RTUModbusClient(settings)
        client.connect()

        # 模拟读取异常
        mock_minimalmodbus.return_value.read_float.side_effect = Exception("Read error")
        
        value, err = client.read_float32(address=50, byte_order="ABCD")
        assert value is None
        assert "Read error" in err

    def test_disconnect(self, mock_minimalmodbus):
        """测试断开连接功能"""
        settings = _RTUSettings(
            unit_id=1,
            timeout_s=1.0,
            serial_port="COM1",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
        )
        client = _RTUModbusClient(settings)
        client.connect()
        
        assert client.is_connected() is True
        
        client.close()
        assert client.is_connected() is False
        mock_minimalmodbus.return_value.serial.close.assert_called_once()

    def test_load_modbus_settings_default(self):
        """测试加载默认配置"""
        with patch('modbus._load_setting_root', return_value={}):
            settings = load_modbus_settings()
            assert settings["instrument_port"] == "COM1"
            assert settings["instrument_address"] == 1
            assert settings["baudrate"] == 9600
            assert settings["parity"] == "N"
            assert settings["stopbits"] == 1
            assert settings["bytesize"] == 8
            assert settings["timeout_s"] == 1.0
