#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主页模块
负责主页内容和图表展示
"""

import os
import random
import time
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer

from pyecharts.charts import Bar
from pyecharts import options as opts
from pyecharts.globals import ThemeType

class HomePage:
    """主页类，负责生成主页内容和图表"""
    
    def __init__(self):
        self.page = QWebEngineView()
        # 初始化数据
        self.data = {
            "当前状态": 1,
            "推进行程": 75,
            "瞬时出土量": 42,
            "环出土量": 128
        }
        self.generate_home_page()
        
        # 设置定时器，每分钟刷新一次数据
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(60000)  # 60000毫秒 = 1分钟
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def update_data(self):
        """更新数据并刷新图表"""
        # 模拟数据变化，实际应用中应该从PLC获取真实数据
        # 随机决定是否更新某个数据项
        if random.choice([True, False]):
            self.data["当前状态"] = random.randint(0, 2)
        if random.choice([True, False]):
            self.data["推进行程"] = max(0, min(100, self.data["推进行程"] + random.randint(-10, 10)))
        if random.choice([True, False]):
            self.data["瞬时出土量"] = max(0, min(100, self.data["瞬时出土量"] + random.randint(-15, 15)))
        if random.choice([True, False]):
            self.data["环出土量"] = max(0, min(200, self.data["环出土量"] + random.randint(-20, 20)))
        
        # 重新生成页面
        self.generate_home_page()
    
    def generate_home_page(self):
        """生成主页内容"""
        # 创建图表
        bar_chart = self.create_bar_chart()
        
        # 构建HTML页面
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>主页</title>
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
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                }}
                .chart-box {{
                    width: 90%;
                    margin-bottom: 20px;
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
                    <div class="chart-title">PLC运行数据</div>
                    {bar_chart}
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
    
    def create_bar_chart(self):
        """创建柱状图"""
        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="400px", theme=ThemeType.LIGHT))
            .add_xaxis(list(self.data.keys()))
            .add_yaxis("数值", list(self.data.values()), category_gap="50%")
            .set_global_opts(
                title_opts=opts.TitleOpts(title=""),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(
                    axislabel_opts=opts.LabelOpts(rotate=0, font_size=14),
                    name="监测项目",
                    name_location="middle",
                    name_gap=35
                ),
                yaxis_opts=opts.AxisOpts(
                    name="数值",
                    name_location="middle",
                    name_gap=40
                ),
            )
            .set_series_opts(
                label_opts=opts.LabelOpts(is_show=True, position="top", font_size=14)
            )
        )
        return bar.render_embed()