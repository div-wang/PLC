#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目管理模块
负责项目管理相关功能
"""

import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class ProjectPage:
    """项目管理页面类"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.generate_project_page()
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def generate_project_page(self):
        """生成项目管理页面内容"""
        # 构建HTML页面
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>项目管理</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                .header p {
                    color: #666;
                }
                .action-bar {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 15px;
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }
                .action-btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: bold;
                }
                .btn-new {
                    background-color: #52c41a;
                    color: white;
                }
                .btn-new:hover {
                    background-color: #73d13d;
                }
                .btn-delete {
                    background-color: #ff4d4f;
                    color: white;
                }
                .btn-delete:hover {
                    background-color: #ff7875;
                }
                .btn-edit {
                    background-color: #1890ff;
                    color: white;
                }
                .btn-edit:hover {
                    background-color: #40a9ff;
                }
                .btn-search {
                    background-color: #fa8c16;
                    color: white;
                }
                .btn-search:hover {
                    background-color: #ffa940;
                }
                .project-list {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 20px;
                    min-height: 300px;
                }
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    color: #999;
                }
                .empty-state h3 {
                    margin-bottom: 10px;
                    color: #666;
                }
                .project-item {
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .project-item:last-child {
                    border-bottom: none;
                }
                .project-info {
                    flex: 1;
                }
                .project-name {
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 5px;
                }
                .project-name-en {
                    color: #666;
                    font-size: 12px;
                    margin-bottom: 5px;
                }
                .project-desc {
                    color: #666;
                    font-size: 14px;
                    margin-top: 5px;
                }
                .project-status {
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-left: 10px;
                }
                .status-active {
                    background-color: #e6f7ff;
                    color: #1890ff;
                }
                .status-completed {
                    background-color: #f6ffed;
                    color: #52c41a;
                }
                .status-pending {
                    background-color: #fff7e6;
                    color: #fa8c16;
                }
                
                    .project-actions {
                    display: flex;
                    gap: 5px;
                    margin-left: 10px;
                }
                .item-action-btn {
                    padding: 4px 8px;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: bold;
                }
                .item-btn-edit {
                    background-color: #1890ff;
                    color: white;
                }
                .item-btn-edit:hover {
                    background-color: #40a9ff;
                }
                .item-btn-delete {
                    background-color: #ff4d4f;
                    color: white;
                }
                .item-btn-delete:hover {
                    background-color: #ff7875;
                }
                
                /* 模态框样式 */
                .modal {
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                }
                .modal-content {
                    background-color: white;
                    margin: 15% auto;
                    padding: 30px;
                    border-radius: 8px;
                    width: 400px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }
                .modal-header {
                    margin-bottom: 20px;
                }
                .modal-header h2 {
                    margin: 0;
                    color: #333;
                }
                .form-group {
                    margin-bottom: 15px;
                }
                .form-group label {
                    display: block;
                    margin-bottom: 5px;
                    color: #333;
                    font-weight: bold;
                }
                .form-group input {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                    box-sizing: border-box;
                }
                .form-group input:focus {
                    outline: none;
                    border-color: #1890ff;
                }
                .modal-footer {
                    margin-top: 20px;
                    text-align: right;
                }
                .modal-btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    margin-left: 10px;
                }
                .modal-btn-save {
                    background-color: #52c41a;
                    color: white;
                }
                .modal-btn-save:hover {
                    background-color: #73d13d;
                }
                .modal-btn-cancel {
                    background-color: #f0f0f0;
                    color: #333;
                }
                .modal-btn-cancel:hover {
                    background-color: #e0e0e0;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>项目管理</h1>
                <p>管理和监控您的PLC项目</p>
            </div>
            
            <div class="action-bar">
                <input type="text" id="searchInput" placeholder="搜索项目..." style="padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 200px;">
                <div style="flex: 1;"></div>
                <button class="action-btn btn-new" onclick="showAddModal()">新建</button>
            </div>
            
            <div class="project-list" id="projectList">
                <div class="empty-state">
                    <h3>暂无项目</h3>
                    <p>点击"新建"按钮创建您的第一个项目</p>
                </div>
            </div>
            
            <!-- 添加项目模态框 -->
            <div id="addModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>添加新项目</h2>
                    </div>
                    <form id="addProjectForm">
                        <div class="form-group">
                            <label for="projectNameCN">项目名称（中文）</label>
                            <input type="text" id="projectNameCN" name="projectNameCN" required>
                        </div>
                        <div class="form-group">
                            <label for="projectNameEN">项目名（英文+数字）</label>
                            <input type="text" id="projectNameEN" name="projectNameEN" pattern="[a-zA-Z0-9_]+" required>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="modal-btn modal-btn-cancel" onclick="hideAddModal()">取消</button>
                            <button type="submit" class="modal-btn modal-btn-save">保存</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                let projects = [];
                let selectedProjectId = null;
                
                function showAddModal() {
                    document.getElementById('addModal').style.display = 'block';
                    document.getElementById('projectNameCN').focus();
                }
                
                function hideAddModal() {
                    document.getElementById('addModal').style.display = 'none';
                    document.getElementById('addProjectForm').reset();
                }
                
                function renderProjects() {
                    const projectList = document.getElementById('projectList');
                    
                    if (projects.length === 0) {
                        projectList.innerHTML = `
                            <div class="empty-state">
                                <h3>暂无项目</h3>
                                <p>点击"新建"按钮创建您的第一个项目</p>
                            </div>
                        `;
                        return;
                    }
                    
                    projectList.innerHTML = projects.map((project, index) => `
                        <div class="project-item" style="cursor: pointer; ${selectedProjectId === index ? 'background-color: #f0f8ff;' : ''}" onclick="selectProject(${index})">
                            <div class="project-info">
                                <div class="project-name">${project.nameCN}</div>
                                <div class="project-name-en">${project.nameEN}</div>
                            </div>
                            <div style="display: flex; align-items: center;">
                                <span class="project-status status-pending">待开发</span>
                                <div class="project-actions">
                                    <button class="item-action-btn item-btn-edit" onclick="event.stopPropagation(); editProject(${index})">编辑</button>
                                    <button class="item-action-btn item-btn-delete" onclick="event.stopPropagation(); deleteProject(${index})">删除</button>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }
                
                function selectProject(index) {
                    selectedProjectId = index;
                    renderProjects();
                }
                
                function deleteProject(index) {
                    if (confirm('确定要删除该项目吗？')) {
                        projects.splice(index, 1);
                        if (selectedProjectId === index) {
                            selectedProjectId = null;
                        } else if (selectedProjectId > index) {
                            selectedProjectId--;
                        }
                        renderProjects();
                    }
                }
                
                function editProject(index) {
                    const project = projects[index];
                    alert(`编辑项目：${project.nameCN} (${project.nameEN})`);
                }
                
                function searchProjects() {
                    const searchInput = document.getElementById('searchInput');
                    const searchTerm = searchInput.value.trim();
                    
                    if (!searchTerm) {
                        renderProjects();
                        return;
                    }
                    
                    const filteredProjects = projects.filter(project => 
                        project.nameCN.includes(searchTerm) || 
                        project.nameEN.toLowerCase().includes(searchTerm.toLowerCase())
                    );
                    
                    const projectList = document.getElementById('projectList');
                    
                    if (filteredProjects.length === 0) {
                        projectList.innerHTML = `
                            <div class="empty-state">
                                <h3>未找到匹配的项目</h3>
                                <p>请尝试其他搜索关键词</p>
                            </div>
                        `;
                        return;
                    }
                    
                    projectList.innerHTML = filteredProjects.map((project, index) => {
                        const originalIndex = projects.indexOf(project);
                        return `
                            <div class="project-item" style="cursor: pointer; ${selectedProjectId === originalIndex ? 'background-color: #f0f8ff;' : ''}" onclick="selectProject(${originalIndex})">
                                <div class="project-info">
                                    <div class="project-name">${project.nameCN}</div>
                                    <div class="project-name-en">${project.nameEN}</div>
                                </div>
                                <div style="display: flex; align-items: center;">
                                    <span class="project-status status-pending">待开发</span>
                                    <div class="project-actions">
                                        <button class="item-action-btn item-btn-edit" onclick="event.stopPropagation(); editProject(${originalIndex})">编辑</button>
                                        <button class="item-action-btn item-btn-delete" onclick="event.stopPropagation(); deleteProject(${originalIndex})">删除</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                // 搜索框事件监听
                document.getElementById('searchInput').addEventListener('input', searchProjects);
                
                // 表单提交处理
                document.getElementById('addProjectForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const nameCN = document.getElementById('projectNameCN').value.trim();
                    const nameEN = document.getElementById('projectNameEN').value.trim();
                    
                    if (!nameCN || !nameEN) {
                        alert('请填写完整的项目信息');
                        return;
                    }
                    
                    // 检查英文名称是否已存在
                    if (projects.some(p => p.nameEN.toLowerCase() === nameEN.toLowerCase())) {
                        alert('项目英文名已存在，请使用其他名称');
                        return;
                    }
                    
                    // 添加新项目
                    projects.push({
                        id: Date.now(),
                        nameCN: nameCN,
                        nameEN: nameEN,
                        description: '',
                        status: 'pending',
                        createdAt: new Date().toISOString()
                    });
                    
                    hideAddModal();
                    renderProjects();
                });
                
                // 点击模态框外部关闭
                window.onclick = function(event) {
                    const modal = document.getElementById('addModal');
                    if (event.target === modal) {
                        hideAddModal();
                    }
                }
                
                // 初始化页面
                renderProjects();
            </script>
        </body>
        </html>
        """
        
        # 保存HTML到临时文件
        project_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "project_page.html")
        with open(project_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(project_html_path))
