#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主页模块
负责主页内容和图表展示
"""

import os
import re
import time
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

import modbus

from pyecharts.charts import Bar, Line
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from pyecharts.commons.utils import JsCode

import app_storage
import db

class JsBridge(QObject):
    """JS和Python交互桥接"""
    def __init__(self, modbus_page):
        super().__init__()
        self.modbus_page = modbus_page
    
    @pyqtSlot()
    def prev_ring(self):
        """上一环操作"""
        if self.modbus_page:
            self.modbus_page.prev_ring()
    
    @pyqtSlot()
    def next_ring(self):
        """下一环操作"""
        if self.modbus_page:
            self.modbus_page.next_ring()

class HomePage:
    """主页类，负责生成主页内容和图表"""
    
    def __init__(self, modbus_page=None):
        self.page = QWebEngineView()
        self.modbus_page = modbus_page
        
        # 初始化JS桥接
        self.channel = QWebChannel()
        self.bridge = JsBridge(modbus_page)
        self.channel.registerObject("bridge", self.bridge)
        self.page.page().setWebChannel(self.channel)
        
        self.summary_data = {
            "实时流量": None,
            "实时载荷": None,
            "实时速度": None,
            "实时流量单位": "t/h",
            "实时速度单位": "m/s",
            "当前环号": None,
            "当前环重量": None,
            "当前环重量单位": "t",
        }
        self.ring_data = {
            "rings": [],
            "weights": [],
            "travels": [],
        }
        self.refresh_interval_ms = self._load_refresh_interval()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.refresh_interval_ms)
        self.update_data()
        self.generate_home_page()
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def _get_mac_prefix8(self):
        try:
            import uuid
            mac = uuid.getnode()
            hex_mac = f"{mac:012x}".upper()
            return hex_mac[:8]
        except Exception:
            return "00000000"
    
    def _build_metrics_table(self):
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        mac8 = self._get_mac_prefix8()
        flow = self.summary_data.get("实时流量")
        speed = self.summary_data.get("实时速度")
        flow_unit = str(self.summary_data.get("实时流量单位") or "")
        speed_unit = str(self.summary_data.get("实时速度单位") or "")
        total_weight = self.summary_data.get("当前环重量")
        total_unit = str(self.summary_data.get("当前环重量单位") or "")
        rows = []
        def row(name, dtype, formula_inputs, unit, value):
            return {
                "名称": name,
                "数据地址": mac8,
                "数据类型": dtype,
                "计算公式": "none",
                "公式输入值": formula_inputs,
                "单位": unit,
                "实时值": value,
                "数据时间": now_str
            }
        rows.append(row("实时流量", "float", 0, flow_unit, flow if flow is not None else "-"))
        rows.append(row("实时速度", "float", 0, speed_unit, speed if speed is not None else "-"))
        rows.append(row("当前环重量", "float", 0, total_unit, f"{float(total_weight):.3f}" if total_weight is not None else "-"))
        return rows

    def _load_refresh_interval(self):
        root = app_storage.load_json("setting.json", {})
        if not isinstance(root, dict):
            root = {}
        try:
            sec = int(root.get("refresh_interval", 5))
        except Exception:
            sec = 5
        return max(1000, int(sec) * 1000)

    def set_refresh_interval(self, ms):
        self.refresh_interval_ms = max(1000, int(ms))
        self.timer.stop()
        self.timer.start(self.refresh_interval_ms)
    
    def update_data(self):
        """更新数据并刷新图表"""
        new_interval = self._load_refresh_interval()
        if new_interval != self.refresh_interval_ms:
            self.set_refresh_interval(new_interval)
        state = app_storage.load_json("modbus_state.json", {})
        if not isinstance(state, dict):
            state = {}

        flow = state.get("flow")
        load = state.get("load")
        speed = state.get("speed")
        flow_unit = state.get("flow_unit")
        speed_unit = state.get("speed_unit")
        total_weight = state.get("total_weight")
        device_total_weight = state.get("device_total_weight")
        total_unit = str(state.get("total_weight_unit") or "t")
        pid = str(state.get("project_id") or "").strip() or self._active_project_id()

        # 实时流量单位转换：kg/h转t/h，除以1000
        self.summary_data["实时流量"] = float(flow) / 1000 if isinstance(flow, (int, float)) else None
        self.summary_data["实时载荷"] = float(load) if isinstance(load, (int, float)) else None
        self.summary_data["实时速度"] = float(speed) if isinstance(speed, (int, float)) else None
        self.summary_data["实时流量单位"] = str(flow_unit or "t/h")
        self.summary_data["实时速度单位"] = str(speed_unit or "m/s")
        
        # 实时计算当前环重量：仪表总重量 - 上一环总重量
        device_total_weight = state.get("device_total_weight")
        current_ring_weight = None
        if isinstance(device_total_weight, (int, float)):
            # 获取当前最大环号
            current_max_ring = db.max_ring_no(str(pid)) or 0
            if current_max_ring > 0:
                # 获取上一环的总重量
                prev_ring = db.get_ring_detail(str(pid), current_max_ring - 1)
                if prev_ring and isinstance(prev_ring, dict):
                    prev_total = prev_ring.get("total_weight")
                    if isinstance(prev_total, (int, float)):
                        current_ring_weight = float(device_total_weight) - float(prev_total)
                        if current_ring_weight < 0:
                            current_ring_weight = 0.0
        
        self.summary_data["当前环重量"] = current_ring_weight
        self.summary_data["当前环重量单位"] = total_unit

        try:
            last10 = db.recent_rings(pid, limit=10)
            self.ring_data["rings"] = [str(int(r.get("ring_no") or 0)) for r in last10]
            self.ring_data["weights"] = [float(r.get("weight") or 0.0) for r in last10]
            self.ring_data["travels"] = [float(r.get("travel") or 0.0) for r in last10]
        except Exception:
            self.ring_data["rings"] = []
            self.ring_data["weights"] = []
            self.ring_data["travels"] = []
        
        # 重新生成页面
        self.generate_home_page()

    def _active_project_id(self):
        projects = app_storage.load_json("project.json", [])
        if not isinstance(projects, list):
            return "default"
        active = None
        for p in projects:
            if isinstance(p, dict) and bool(p.get("is_active", False)):
                active = p
                break
        if active is None and projects and isinstance(projects[0], dict):
            active = projects[0]
        if isinstance(active, dict):
            pid = str(active.get("name_en") or active.get("name_cn") or "").strip()
            if pid:
                return pid
        return "default"
    
    def generate_home_page(self):
        """生成主页内容"""
        # 构建数据卡片HTML
        import json
        import time
        metrics_rows = self._build_metrics_table()
        metrics_json = json.dumps(metrics_rows, ensure_ascii=False)
        # 实时获取当前最大环号
        pid = self._active_project_id()
        current_ring_no = db.max_ring_no(str(pid)) or 0
        
        flow = self.summary_data.get("实时流量")
        speed = self.summary_data.get("实时速度")
        total_weight = self.summary_data.get("当前环重量")
        total_unit = str(self.summary_data.get("当前环重量单位") or "t")
        flow_unit = str(self.summary_data.get("实时流量单位") or "")
        speed_unit = str(self.summary_data.get("实时速度单位") or "")
        flow_txt = "--" if flow is None else f"{float(flow):.3f}"
        speed_txt = "--" if speed is None else f"{float(speed):.2f}"
        
        if total_weight is None:
            total_txt = "--"
        else:
            w = float(total_weight)
            total_txt = f"{max(0.0, w):.3f}"
            
        # 顶部工具栏，完全按照modbus页面样式
        button_bar = f"""
        <div style="background: white; border: none; border-radius: 10px; padding: 14px 14px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
            <div style="background: #f6ffed; color: #389e0d; border: none; border-radius: 8px; padding: 6px 10px; text-align: center; min-width: 110px; font-size: 14px;">
                当前环号: {current_ring_no}
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="prevRing()" style="background: #e6f4ff; color: #1677ff; border: none; border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 14px;" onmouseover="this.style.background='#bae7ff'" onmouseout="this.style.background='#e6f4ff'">
                    上一环
                </button>
                <button onclick="nextRing()" style="background: #f0f0f0; color: #333; border: none; border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 14px;" onmouseover="this.style.background='#e6f4ff'" onmouseout="this.style.background='#f0f0f0'">
                    下一环
                </button>
            </div>
        </div>
        """
        
        summary_cards = f"""
        <div class="data-grid">
            <div class="data-card" data-key="实时流量">
                <div class="data-label">实时流量</div>
                <div class="data-value">{flow_txt} <span class="data-unit">{flow_unit}</span></div>
            </div>
            <div class="data-card" data-key="实时速度">
                <div class="data-label">实时速度</div>
                <div class="data-value">{speed_txt} <span class="data-unit">{speed_unit}</span></div>
            </div>
            <div class="data-card" data-key="当前环重量">
                <div class="data-label">当前环重量</div>
                <div class="data-value">{total_txt} <span class="data-unit">{total_unit}</span></div>
            </div>
        </div>
        """
        
        ring_chart = self._clean_embed(self.create_ring_chart())
        
        # 构建HTML页面
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>主页</title>
            <script type="text/javascript" src="https://assets.pyecharts.org/assets/v5/echarts.min.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 12px;
                    background-color: #f9f9f9;
                }}
                .chart-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }}
                .chart-box {{
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 14px;
                    width: 100%;
                    box-sizing: border-box;
                }}
                .chart-title {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 12px;
                    color: #333;
                    text-align: center;
                }}
                .update-time {{
                    text-align: right;
                    color: #888;
                    font-size: 11px;
                    margin-top: 6px;
                }}
                .data-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                    margin-bottom: 12px;
                }}
                .data-card {{
                    background-color: #f0f2f5;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                }}
                .data-label {{
                    font-size: 13px;
                    color: #666;
                    margin-bottom: 6px;
                }}
                .data-value {{
                    font-size: 22px;
                    font-weight: bold;
                    color: #1890ff;
                }}
                .data-unit {{
                    font-size: 12px;
                    color: #999;
                    font-weight: normal;
                }}

                @media (max-width: 720px) {{
                    body {{ padding: 10px; }}
                    .chart-container {{ gap: 12px; }}
                    .chart-box {{ padding: 12px; }}
                    .chart-title {{ font-size: 15px; margin-bottom: 10px; }}
                    .data-grid {{ gap: 8px; margin-bottom: 10px; }}
                    .data-card {{ padding: 10px; }}
                    .data-value {{ font-size: 20px; }}
                    table.modal-table th, table.modal-table td {{ font-size: 12px; padding: 5px; }}
                }}

                @media (max-height: 560px) {{
                    body {{ padding: 8px; }}
                    .chart-container {{ gap: 10px; }}
                    .chart-box {{ padding: 10px; }}
                    .chart-title {{ font-size: 14px; margin-bottom: 8px; }}
                    .update-time {{ margin-top: 4px; }}
                }}
            </style>
        </head>
        <body>
            
            <div class="chart-container">
                {button_bar}
                <div class="chart-box">
                    <div class="chart-title">总数据汇总</div>
                    {summary_cards}
                </div>
                <div class="chart-box">
                    <div class="chart-title">环号实时出土数据</div>
                    {ring_chart}
                </div>
            </div>
            
            <script>
                // 初始化WebChannel
                var bridge = null;
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    bridge = channel.objects.bridge;
                }});
                
                function prevRing() {{
                    if (bridge) bridge.prev_ring();
                }}
                
                function nextRing() {{
                    if (bridge) bridge.next_ring();
                }}
            </script>
        </body>
        </html>
        """
        
        # 保存HTML到临时文件，添加时间戳避免缓存
        timestamp = int(time.time() * 1000)
        home_html_path = os.path.join(app_storage.ui_cache_dir(), f"home_page.html")
        with open(home_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView，添加时间戳查询参数强制刷新
        url = QUrl.fromLocalFile(home_html_path)
        url.setQuery(f"t={timestamp}")
        
        # 使用 QTimer.singleShot 确保在 GUI 事件循环中加载
        def load_page():
            self.page.load(url)
        
        QTimer.singleShot(0, load_page)
    

    def create_ring_chart(self):
        labels = list(self.ring_data.get("rings") or [])
        weights = list(self.ring_data.get("weights") or [])
        if not labels:
            labels = ["-"]
            weights = [0]
        
        axis2 = JsCode(
            "function (value) {"
            "  if (value === null || value === undefined || value === '') { return ''; }"
            "  var n = Number(value);"
            "  if (isNaN(n)) { return value; }"
            "  return String(Math.round(n));"
            "}"
        )
        tip3 = JsCode(
            "function (params) {"
            "  if (!params || !params.length) { return ''; }"
            "  var s = params[0].axisValueLabel + '<br/>';"
            "  params.forEach(function(p){"
            "    var v = p.data;"
            "    if (v === null || v === undefined || v === '') { v = '-'; }"
            "    else {"
            "      var n = Number(v);"
            "      v = isNaN(n) ? v : String(Math.round(n));"
            "    }"
            "    s += p.marker + p.seriesName + ': ' + v + '<br/>';"
            "  });"
            "  return s;"
            "}"
        )
        label3 = JsCode(
            "function (p) {"
            "  var v = p && p.value;"
            "  if (v === null || v === undefined || v === '') { return ''; }"
            "  var n = Number(v);"
            "  if (isNaN(n)) { return v; }"
            "  return String(Math.round(n));"
            "}"
        )

        bar = Bar(init_opts=opts.InitOpts(width="100%", height="260px", theme=ThemeType.LIGHT))
        bar.add_xaxis(labels)
        bar.add_yaxis(
            "重量(t)",
            weights,
            category_gap="40%",
            yaxis_index=0,
            itemstyle_opts=opts.ItemStyleOpts(color="#1890ff"),
            label_opts=opts.LabelOpts(is_show=True, formatter=label3),
        )

        grid = None
        grid_candidates = (
            dict(pos_left="6%", pos_right="4%", pos_top="14%", pos_bottom="14%", contain_label=True),
            dict(pos_left="6%", pos_right="4%", pos_top="14%", pos_bottom="14%", is_contain_label=True),
            dict(pos_left="6%", pos_right="4%", pos_top="14%", pos_bottom="14%"),
            dict(left="6%", right="4%", top="14%", bottom="14%", contain_label=True),
            dict(left="6%", right="4%", top="14%", bottom="14%", is_contain_label=True),
            dict(left="6%", right="4%", top="14%", bottom="14%"),
        )
        for kw in grid_candidates:
            try:
                grid = opts.GridOpts(**kw)
                break
            except TypeError:
                grid = None

        kwargs = dict(
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross", formatter=tip3),
            legend_opts=opts.LegendOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(
                name="环号",
                name_location="center",
                name_gap=22,
                axislabel_opts=opts.LabelOpts(font_size=11),
            ),
            yaxis_opts=opts.AxisOpts(
                name="重量(t)",
                name_location="end",
                name_gap=15,
                axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color="#1890ff")),
                axislabel_opts=opts.LabelOpts(formatter=axis2),
            ),
        )
        if grid is not None:
            try:
                bar.set_global_opts(grid_opts=grid, **kwargs)
                return bar.render_embed()
            except TypeError:
                pass
        bar.set_global_opts(**kwargs)
        return bar.render_embed()

    def _clean_embed(self, embed_html: str) -> str:
        try:
            m = re.search(r"<body[^>]*>([\s\S]*?)</body>", embed_html)
            if m:
                return m.group(1)
            return embed_html
        except Exception:
            return embed_html
