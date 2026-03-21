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
from PyQt5.QtCore import QUrl, QTimer

from pyecharts.charts import Bar, Line
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from pyecharts.commons.utils import JsCode

import app_storage
import db

class HomePage:
    """主页类，负责生成主页内容和图表"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.summary_data = {
            "实时流量": None,
            "实时载荷": None,
            "实时速度": None,
            "总重量": None,
            "总重量单位": "t",
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
        load = self.summary_data.get("实时载荷")
        speed = self.summary_data.get("实时速度")
        total_weight = self.summary_data.get("总重量")
        total_unit = str(self.summary_data.get("总重量单位") or "")
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
        rows.append(row("实时流量", "float", 0, "t/h", flow if flow is not None else "-"))
        rows.append(row("实时载荷", "float", 0, "kg/m", load if load is not None else "-"))
        rows.append(row("实时速度", "float", 0, "m/s", speed if speed is not None else "-"))
        rows.append(row("总重量", "float", 0, total_unit, f"{float(total_weight):.3f}" if total_weight is not None else "-"))
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
        total_weight = state.get("total_weight")
        total_unit = str(state.get("total_weight_unit") or "t")

        self.summary_data["实时流量"] = float(flow) if isinstance(flow, (int, float)) else None
        self.summary_data["实时载荷"] = float(load) if isinstance(load, (int, float)) else None
        self.summary_data["实时速度"] = float(speed) if isinstance(speed, (int, float)) else None
        self.summary_data["总重量"] = float(total_weight) if isinstance(total_weight, (int, float)) else None
        self.summary_data["总重量单位"] = total_unit

        ring_db = app_storage.load_json("ring_records.json", {"records": []})
        records = []
        if isinstance(ring_db, dict) and isinstance(ring_db.get("records"), list):
            records = [r for r in ring_db.get("records") if isinstance(r, dict)]
        pid = self._active_project_id()
        try:
            last10 = db.recent_rings(pid, limit=10)
        except Exception:
            filtered = [r for r in records if str(r.get("project_id") or "") == pid]
            filtered.sort(key=lambda x: int(x.get("ring_no") or 0))
            last10 = filtered[-10:]
        self.ring_data["rings"] = [str(int(r.get("ring_no") or 0)) for r in last10]
        self.ring_data["weights"] = [float(r.get("weight") or 0.0) for r in last10]
        self.ring_data["travels"] = [float(r.get("travel") or 0.0) for r in last10]
        
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
        metrics_rows = self._build_metrics_table()
        metrics_json = json.dumps(metrics_rows, ensure_ascii=False)
        flow = self.summary_data.get("实时流量")
        load = self.summary_data.get("实时载荷")
        speed = self.summary_data.get("实时速度")
        total_weight = self.summary_data.get("总重量")
        total_unit = str(self.summary_data.get("总重量单位") or "t")
        flow_txt = "--" if flow is None else f"{float(flow):.2f}"
        load_txt = "--" if load is None else f"{float(load):.2f}"
        speed_txt = "--" if speed is None else f"{float(speed):.2f}"
        total_txt = "--" if total_weight is None else f"{float(total_weight):.3f}"
        summary_cards = f"""
        <div class="data-grid">
            <div class="data-card" data-key="实时流量">
                <div class="data-label">实时流量</div>
                <div class="data-value">{flow_txt} <span class="data-unit">t/h</span></div>
            </div>
            <div class="data-card" data-key="实时载荷">
                <div class="data-label">实时载荷</div>
                <div class="data-value">{load_txt} <span class="data-unit">kg/m</span></div>
            </div>
            <div class="data-card" data-key="实时速度">
                <div class="data-label">实时速度</div>
                <div class="data-value">{speed_txt} <span class="data-unit">m/s</span></div>
            </div>
            <div class="data-card" data-key="总重量">
                <div class="data-label">总重量</div>
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
                    grid-template-columns: repeat(4, 1fr);
                    gap: 10px;
                    margin-bottom: 12px;
                }}
                .data-card {{
                    background-color: #f0f2f5;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                    transition: all 0.3s;
                    cursor: pointer;
                }}
                .data-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    background-color: #e6f7ff;
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
                .modal {{
                    display: none;
                    position: fixed;
                    z-index: 2000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                }}
                .modal-content {{
                    background-color: white;
                    margin: 6% auto;
                    padding: 16px;
                    border-radius: 8px;
                    width: 92vw;
                    max-width: 600px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }}
                .modal-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .modal-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                }}
                .close-btn {{
                    border: none;
                    background: #f0f0f0;
                    border-radius: 4px;
                    padding: 6px 10px;
                    cursor: pointer;
                }}
                .detail-grid {{
                    display: grid;
                    grid-template-columns: 160px 1fr;
                    gap: 10px;
                    align-items: center;
                }}
                .detail-label {{
                    color: #666;
                    font-weight: 600;
                }}
                .detail-value {{
                    color: #333;
                }}
                table.modal-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                table.modal-table th, table.modal-table td {{
                    border: 1px solid #eee;
                    padding: 6px;
                    font-size: 13px;
                    text-align: left;
                }}
                table.modal-table th {{
                    background: #f7f7f7;
                    color: #555;
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
                <div class="chart-box">
                    <div class="chart-title">总数据汇总</div>
                    {summary_cards}
                    <div class="update-time">最后更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
                <div class="chart-box">
                    <div class="chart-title">环号实时出土数据</div>
                    {ring_chart}
                    <div class="update-time">最后更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
            </div>
            
            <div id="metricModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <div class="modal-title" id="modalTitle">PLC数据详情</div>
                        <button class="close-btn" id="modalClose">关闭</button>
                    </div>
                    <table class="modal-table">
                        <thead>
                            <tr>
                                <th>名称</th>
                                <th>数据地址</th>
                                <th>数据类型</th>
                                <th>计算公式</th>
                                <th>公式输入值</th>
                                <th>单位</th>
                                <th>实时值</th>
                                <th>数据时间</th>
                            </tr>
                        </thead>
                        <tbody id="metricTBody"></tbody>
                    </table>
                </div>
            </div>
            
            <script>
            const METRICS_ROWS = {metrics_json};
            function populateTable() {{
                const tbody = document.getElementById('metricTBody');
                tbody.innerHTML = '';
                METRICS_ROWS.forEach(r => {{
                    const tr = document.createElement('tr');
                    const cols = ['名称','数据地址','数据类型','计算公式','公式输入值','单位','实时值','数据时间'];
                    cols.forEach(k => {{
                        const td = document.createElement('td');
                        td.textContent = (r[k] !== undefined && r[k] !== null) ? String(r[k]) : '-';
                        tr.appendChild(td);
                    }});
                    tbody.appendChild(tr);
                }});
            }}
            function showMetric() {{
                populateTable();
                document.getElementById('metricModal').style.display = 'block';
            }}
            function hideMetric() {{
                document.getElementById('metricModal').style.display = 'none';
            }}
            document.addEventListener('DOMContentLoaded', function() {{
                document.querySelectorAll('.data-card').forEach(function(card) {{
                    card.addEventListener('click', function() {{
                        showMetric();
                    }});
                }});
                document.getElementById('modalClose').addEventListener('click', hideMetric);
                window.addEventListener('click', function(evt) {{
                    if (evt.target && evt.target.id === 'metricModal') {{
                        hideMetric();
                    }}
                }});
            }});
            </script>
        </body>
        </html>
        """
        
        # 保存HTML到临时文件
        home_html_path = os.path.join(app_storage.ui_cache_dir(), "home_page.html")
        with open(home_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(home_html_path))
    

    def create_ring_chart(self):
        labels = list(self.ring_data.get("rings") or [])
        weights = list(self.ring_data.get("weights") or [])
        if not labels:
            labels = ["-"]
            weights = [0]
        
        axis2 = JsCode(
            "function (value) {"
            "  if (value === null || value === undefined || value === '') { return ''; }"
            "  return Number(value).toFixed(2);"
            "}"
        )
        tip3 = JsCode(
            "function (params) {"
            "  if (!params || !params.length) { return ''; }"
            "  var s = params[0].axisValueLabel + '<br/>';"
            "  params.forEach(function(p){"
            "    var v = p.data;"
            "    if (v === null || v === undefined || v === '') { v = '-'; }"
            "    else { v = Number(v).toFixed(3); }"
            "    s += p.marker + p.seriesName + ': ' + v + '<br/>';"
            "  });"
            "  return s;"
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
