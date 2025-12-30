#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主页模块
负责主页内容和图表展示
"""

import os
import re
import random
import time
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, QSettings

from pyecharts.charts import Bar, Line
from pyecharts import options as opts
from pyecharts.globals import ThemeType

class HomePage:
    """主页类，负责生成主页内容和图表"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.summary_data = {
            "推进行程": 75,
            "瞬时出土量": 42,
            "环出土量": 128,
            "当前状态": 60
        }
        # 模拟最近20环的出土量数据
        self.ring_data = {
            "rings": [str(i) for i in range(1, 21)],
            "values": [random.randint(80, 150) for _ in range(20)],
            "stroke_values": [random.randint(100, 200) for _ in range(20)]
        }
        self.refresh_interval_ms = self._load_refresh_interval()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.refresh_interval_ms)
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
        try:
            current_ring_label = int(self.ring_data["rings"][-1])
        except Exception:
            current_ring_label = 1
        ring_base = 8000
        ring_no = ring_base + current_ring_label - 1
        stroke = int(self.summary_data.get("推进行程", 0))
        # 模拟各油缸行程：在总行程基础上加减微小偏差
        cyl_variants = [
            ("A组油缸行程", max(0, stroke + 1)),
            ("B组油缸行程", max(0, stroke - 1)),
            ("C组油缸行程", max(0, stroke + 2)),
            ("D组油缸行程", max(0, stroke - 2)),
        ]
        # 刀盘转速与推进速度简单计算（示意）
        rpm = round(self.summary_data.get("当前状态", 0) * 0.3, 2)
        refresh_ms = getattr(self, 'refresh_interval_ms', 60000)
        speed = round(stroke / max(1, refresh_ms / 1000.0), 2)
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
        rows.append(row("环号", "short", ring_base, "", ring_no))
        rows.append(row("刀盘转速", "float", 0, "", rpm))
        for nm, val in cyl_variants:
            rows.append(row(nm, "float", 0, "mm", val))
        rows.append(row("推进速度", "float", 0, "", speed))
        return rows

    def _load_refresh_interval(self):
        try:
            settings = QSettings("PLCApp", "PLC")
            val = int(settings.value("refresh_interval_ms", 60000))
            return max(1000, val)
        except Exception:
            env_val = os.environ.get("PLC_REFRESH_MS")
            try:
                if env_val:
                    return max(1000, int(env_val))
            except Exception:
                pass
        return 60000

    def set_refresh_interval(self, ms):
        self.refresh_interval_ms = max(1000, int(ms))
        self.timer.stop()
        self.timer.start(self.refresh_interval_ms)
    
    def update_data(self):
        """更新数据并刷新图表"""
        new_interval = self._load_refresh_interval()
        if new_interval != self.refresh_interval_ms:
            self.set_refresh_interval(new_interval)
        if random.choice([True, False]):
            self.summary_data["当前状态"] = max(0, min(100, self.summary_data["当前状态"] + random.randint(-5, 5)))
        if random.choice([True, False]):
            self.summary_data["推进行程"] = max(0, min(200, self.summary_data["推进行程"] + random.randint(-10, 10)))
        if random.choice([True, False]):
            self.summary_data["瞬时出土量"] = max(0, min(300, self.summary_data["瞬时出土量"] + random.randint(-15, 15)))
        if random.choice([True, False]):
            self.summary_data["环出土量"] = max(0, min(300, self.summary_data["环出土量"] + random.randint(-20, 20)))

        # 更新环号数据（模拟推进）
        if random.random() < 0.1:  # 10%概率推进一环
            last_ring = int(self.ring_data["rings"][-1])
            self.ring_data["rings"].pop(0)
            self.ring_data["rings"].append(str(last_ring + 1))
            self.ring_data["values"].pop(0)
            self.ring_data["values"].append(random.randint(80, 150))
        
        # 重新生成页面
        self.generate_home_page()
    
    def generate_home_page(self):
        """生成主页内容"""
        # 构建数据卡片HTML
        import json
        metrics_rows = self._build_metrics_table()
        metrics_json = json.dumps(metrics_rows, ensure_ascii=False)
        summary_cards = f"""
        <div class="data-grid">
            <div class="data-card" data-key="推进行程">
                <div class="data-label">推进行程</div>
                <div class="data-value">{self.summary_data["推进行程"]} <span class="data-unit">mm</span></div>
            </div>
            <div class="data-card" data-key="瞬时出土量">
                <div class="data-label">瞬时出土量</div>
                <div class="data-value">{self.summary_data["瞬时出土量"]} <span class="data-unit">t/h</span></div>
            </div>
            <div class="data-card" data-key="环出土量">
                <div class="data-label">环出土量</div>
                <div class="data-value">{self.summary_data["环出土量"]} <span class="data-unit">t</span></div>
            </div>
            <div class="data-card" data-key="当前状态">
                <div class="data-label">当前状态</div>
                <div class="data-value">{self.summary_data["当前状态"]} <span class="data-unit">%</span></div>
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
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .chart-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 30px;
                }}
                .chart-box {{
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 20px;
                    width: 100%;
                    box-sizing: border-box;
                }}
                .chart-title {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 20px;
                    color: #333;
                    text-align: center;
                }}
                .update-time {{
                    text-align: right;
                    color: #888;
                    font-size: 12px;
                    margin-top: 10px;
                }}
                .data-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .data-card {{
                    background-color: #f0f2f5;
                    border-radius: 8px;
                    padding: 20px;
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
                    font-size: 16px;
                    color: #666;
                    margin-bottom: 10px;
                }}
                .data-value {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #1890ff;
                }}
                .data-unit {{
                    font-size: 16px;
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
                    margin: 10% auto;
                    padding: 20px;
                    border-radius: 8px;
                    width: 600px;
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
                    padding: 8px;
                    font-size: 13px;
                    text-align: left;
                }}
                table.modal-table th {{
                    background: #f7f7f7;
                    color: #555;
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
        home_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "home_page.html")
        with open(home_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(home_html_path))
    

    def create_ring_chart(self):
        labels = self.ring_data["rings"]
        values_output = self.ring_data["values"]
        values_stroke = self.ring_data["stroke_values"]
        
        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="360px", theme=ThemeType.LIGHT))
            .add_xaxis(labels)
            .add_yaxis(
                "出土量(t)", 
                values_output, 
                category_gap="40%", 
                yaxis_index=0,
                itemstyle_opts=opts.ItemStyleOpts(color="#1890ff")
            )
            .extend_axis(
                yaxis=opts.AxisOpts(
                    name="推进行程(mm)",
                    type_="value",
                    min_=0,
                    max_=250,
                    position="right",
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#d14a61")
                    ),
                    axislabel_opts=opts.LabelOpts(formatter="{value} mm"),
                )
            )
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
                legend_opts=opts.LegendOpts(is_show=True),
                xaxis_opts=opts.AxisOpts(
                    name="环号",
                    name_location="center",
                    name_gap=30,
                    axislabel_opts=opts.LabelOpts(font_size=12)
                ),
                yaxis_opts=opts.AxisOpts(
                    name="出土量(t)",
                    name_location="end",
                    name_gap=15,
                    axisline_opts=opts.AxisLineOpts(
                        linestyle_opts=opts.LineStyleOpts(color="#1890ff")
                    )
                )
            )
        )
        
        line = (
            Line()
            .add_xaxis(labels)
            .add_yaxis(
                "推进行程(mm)", 
                values_stroke, 
                yaxis_index=1,
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color="#d14a61"),
                linestyle_opts=opts.LineStyleOpts(width=2)
            )
        )
        
        bar.overlap(line)
        return bar.render_embed()

    def _clean_embed(self, embed_html: str) -> str:
        try:
            m = re.search(r"<body[^>]*>([\s\S]*?)</body>", embed_html)
            if m:
                return m.group(1)
            return embed_html
        except Exception:
            return embed_html
