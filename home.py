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

from pyecharts.charts import Bar
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
        self.ring_data = {
            "实际环出土量": 120,
            "标准环出土量": 100,
            "预估参照量": 110,
            "净推进行": 80
        }
        self.generate_home_page()
        
        self.refresh_interval_ms = self._load_refresh_interval()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.refresh_interval_ms)
    
    def get_page(self):
        """获取页面组件"""
        return self.page

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

        if random.choice([True, False]):
            self.ring_data["实际环出土量"] = max(0, self.ring_data["实际环出土量"] + random.randint(-10, 10))
        if random.choice([True, False]):
            self.ring_data["标准环出土量"] = max(0, self.ring_data["标准环出土量"] + random.randint(-5, 5))
        if random.choice([True, False]):
            self.ring_data["预估参照量"] = max(0, self.ring_data["预估参照量"] + random.randint(-8, 8))
        if random.choice([True, False]):
            self.ring_data["净推进行"] = max(0, self.ring_data["净推进行"] + random.randint(-10, 10))
        
        # 重新生成页面
        self.generate_home_page()
    
    def generate_home_page(self):
        """生成主页内容"""
        summary_chart = self._clean_embed(self.create_summary_chart())
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
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .header p {{
                    color: #666;
                }}
                .chart-container {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 20px;
                    align-items: start;
                }}
                .chart-box {{
                    margin-bottom: 0;
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 15px;
                }}
                .chart-title {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #333;
                    text-align: center;
                }}
                .update-time {{
                    text-align: right;
                    color: #888;
                    font-size: 12px;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PLC数据监控</h1>
                <p>实时监控PLC关键指标</p>
            </div>
            
            <div class="chart-container">
                <div class="chart-box">
                    <div class="chart-title">总数据汇总</div>
                    {summary_chart}
                    <div class="update-time">最后更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
                <div class="chart-box">
                    <div class="chart-title">环号实时出土数据</div>
                    {ring_chart}
                    <div class="update-time">最后更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 保存HTML到临时文件
        home_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "home_page.html")
        with open(home_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(home_html_path))
    
    def create_summary_chart(self):
        labels = ["推进行程(mm)", "瞬时出土量(t/h)", "环出土量(t)", "当前状态(%)"]
        values = [
            self.summary_data["推进行程"],
            self.summary_data["瞬时出土量"],
            self.summary_data["环出土量"],
            self.summary_data["当前状态"],
        ]
        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="360px", theme=ThemeType.LIGHT))
            .add_xaxis(labels)
            .add_yaxis("数值", values, category_gap="40%")
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="item"),
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=14)),
                yaxis_opts=opts.AxisOpts(name="数值")
            )
            .set_series_opts(label_opts=opts.LabelOpts(is_show=True, position="top", font_size=14))
        )
        return bar.render_embed()

    def create_ring_chart(self):
        labels = ["实际环出土量(t)", "标准环出土量(t)", "预估参照量(t)", "净推进行(mm)"]
        values = [
            self.ring_data["实际环出土量"],
            self.ring_data["标准环出土量"],
            self.ring_data["预估参照量"],
            self.ring_data["净推进行"],
        ]
        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="360px", theme=ThemeType.LIGHT))
            .add_xaxis(labels)
            .add_yaxis("数值", values, category_gap="40%")
            .set_global_opts(
                tooltip_opts=opts.TooltipOpts(trigger="item"),
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=14)),
                yaxis_opts=opts.AxisOpts(name="数值")
            )
            .set_series_opts(label_opts=opts.LabelOpts(is_show=True, position="top", font_size=14))
        )
        return bar.render_embed()

    def _clean_embed(self, embed_html: str) -> str:
        try:
            m = re.search(r"<body[^>]*>([\s\S]*?)</body>", embed_html)
            if m:
                return m.group(1)
            return embed_html
        except Exception:
            return embed_html
