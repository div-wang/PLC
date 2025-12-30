#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目管理模块
负责项目管理相关功能
"""

import os
import json
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWidgets import QFileDialog

class ProjectPage:
    """项目管理页面类"""
    
    def __init__(self):
        self.page = QWebEngineView()
        self.bridge = ProjectBridge()
        self.channel = QWebChannel(self.page.page())
        self.channel.registerObject('bridge', self.bridge)
        self.page.page().setWebChannel(self.channel)
        self.generate_project_page()
    
    def get_page(self):
        """获取页面组件"""
        return self.page
    
    def load_projects(self):
        """从JSON文件加载项目列表"""
        projects_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.json")
        default_projects = []
        
        if os.path.exists(projects_path):
            try:
                with open(projects_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert snake_case to camelCase for JS
                    js_projects = []
                    for p in data:
                        js_p = {
                            "nameCN": p.get("name_cn", ""),
                            "nameEN": p.get("name_en", ""),
                            "current": p.get("is_active", False),
                            "plcSettings": p.get("plc_settings", {})
                        }
                        js_projects.append(js_p)
                    return js_projects
            except Exception as e:
                print(f"Error loading projects: {e}")
                return default_projects
        return default_projects

    def generate_project_page(self):
        """生成项目管理页面内容"""
        js_projects = self.load_projects()
        
        # 构建HTML页面
        html_content = r"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>项目管理</title>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }

                .action-bar {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 15px;
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: flex-end;
                    gap: 20px;
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
                .btn-import {
                    background-color: #722ed1;
                    color: white;
                }
                .btn-import:hover {
                    background-color: #9254de;
                }
                .btn-export {
                    background-color: #13c2c2;
                    color: white;
                }
                .btn-export:hover {
                    background-color: #36cfc9;
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
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 20px;
                    padding: 20px;
                }
                .empty-state {
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 60px 20px;
                    color: #999;
                }
                .empty-state h3 {
                    margin-bottom: 10px;
                    color: #666;
                }
                .project-item {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    transition: all 0.3s;
                    border: 1px solid #eee;
                    position: relative;
                }
                .project-item:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.15);
                }
                .project-item.active-project {
                    border: 2px solid #1890ff;
                    background-color: #f0f9ff;
                }
                .project-info {
                    flex: 1;
                    margin-bottom: 15px;
                }
                .project-name {
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 8px;
                }
                .project-name-en {
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 5px;
                }
                .project-status-badge {
                    position: absolute;
                    top: 15px;
                    right: 15px;
                    padding: 4px 12px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .status-active {
                    background-color: #e6f7ff;
                    color: #1890ff;
                    border: 1px solid #91d5ff;
                }
                .project-actions {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                    padding-top: 15px;
                    border-top: 1px solid #f0f0f0;
                    margin-top: auto;
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
                .item-btn-switch {
                    background-color: #722ed1;
                    color: white;
                }
                .item-btn-switch:hover {
                    background-color: #9254de;
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
            
            <div class="action-bar">
                <input type="text" id="searchInput" placeholder="搜索项目..." style="padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 200px;">
                <div style="flex: 1;"></div>
                <button class="action-btn btn-import" onclick="importProjects()">导入项目</button>
                <button class="action-btn btn-export" onclick="exportProjects()">导出项目</button>
                <button class="action-btn btn-new" onclick="showAddModal()">新建项目</button>
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
            
            <!-- 编辑项目模态框 -->
            <div id="editModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>编辑项目</h2>
                    </div>
                    <form id="editProjectForm">
                        <div class="form-group">
                            <label for="editProjectNameCN">项目名称（中文）</label>
                            <input type="text" id="editProjectNameCN" name="editProjectNameCN" required>
                        </div>
                        <div class="form-group">
                            <label for="editProjectNameEN">项目名（英文+数字）</label>
                            <input type="text" id="editProjectNameEN" name="editProjectNameEN" disabled>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="modal-btn modal-btn-cancel" onclick="hideEditModal()">取消</button>
                            <button type="submit" class="modal-btn modal-btn-save">保存</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <!-- 导入项目模态框 -->
            <div id="importModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>导入项目</h2>
                    </div>
                    <div class="form-group">
                        <label for="importFile">选择JSON文件</label>
                        <input type="file" id="importFile" accept="application/json">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="modal-btn modal-btn-cancel" onclick="hideImportModal()">取消</button>
                        <button type="button" class="modal-btn modal-btn-save" onclick="confirmImportProject()">导入</button>
                    </div>
                </div>
            </div>
            
            <script>
                let projects = __PROJECTS__;
                let selectedProjectId = null;
                let fileInputEl = null;
                let editingIndex = null;
                let importFileEl = null;
                
                document.addEventListener('DOMContentLoaded', function(){
                    new QWebChannel(qt.webChannelTransport, function(channel){
                        window.bridge = channel.objects.bridge;
                    });
                });
                
                function showAddModal() {
                    document.getElementById('addModal').style.display = 'block';
                    document.getElementById('projectNameCN').focus();
                }
                
                function hideAddModal() {
                    document.getElementById('addModal').style.display = 'none';
                    document.getElementById('addProjectForm').reset();
                }
                
                function showImportModal() {
                    importFileEl = document.getElementById('importFile');
                    if (importFileEl) {
                        importFileEl.value = '';
                    }
                    document.getElementById('importModal').style.display = 'block';
                }
                
                function hideImportModal() {
                    document.getElementById('importModal').style.display = 'none';
                    importFileEl = null;
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
                        <div class="project-item ${project.current ? 'active-project' : ''}" onclick="selectProject(${index})">
                            ${project.current ? '<span class="project-status-badge status-active">当前运行</span>' : ''}
                            <div class="project-info">
                                <div class="project-name">${project.nameCN}</div>
                                <div class="project-name-en">${project.nameEN}</div>
                            </div>
                            <div class="project-actions">
                                <button class="item-action-btn item-btn-switch" onclick="event.stopPropagation(); switchCurrent(${index})">切换</button>
                                <button class="item-action-btn item-btn-edit" onclick="event.stopPropagation(); editProject(${index})">编辑</button>
                                <button class="item-action-btn item-btn-delete" onclick="event.stopPropagation(); deleteProject(${index})">删除</button>
                            </div>
                        </div>
                    `).join('');
                }
                
                function selectProject(index) {
                    selectedProjectId = index;
                    renderProjects();
                }

                function switchCurrent(index) {
                    projects = projects.map((p, i) => ({...p, current: i === index}));
                    selectedProjectId = index;
                    renderProjects();
                }
                
                function deleteProject(index) {
                    if (projects[index] && projects[index].current) {
                        alert('当前项目不可删除');
                        return;
                    }
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
                    editingIndex = index;
                    const project = projects[index];
                    document.getElementById('editProjectNameCN').value = project.nameCN || '';
                    document.getElementById('editProjectNameEN').value = project.nameEN || '';
                    document.getElementById('editModal').style.display = 'block';
                    document.getElementById('editProjectNameCN').focus();
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
                            <div class="project-item ${project.current ? 'active-project' : ''}" onclick="selectProject(${originalIndex})">
                                ${project.current ? '<span class="project-status-badge status-active">当前运行</span>' : ''}
                                <div class="project-info">
                                    <div class="project-name">${project.nameCN}</div>
                                    <div class="project-name-en">${project.nameEN}</div>
                                </div>
                                <div class="project-actions">
                                    <button class="item-action-btn item-btn-switch" onclick="event.stopPropagation(); switchCurrent(${originalIndex})">切换</button>
                                    <button class="item-action-btn item-btn-edit" onclick="event.stopPropagation(); editProject(${originalIndex})">编辑</button>
                                    <button class="item-action-btn item-btn-delete" onclick="event.stopPropagation(); deleteProject(${originalIndex})">删除</button>
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
                        createdAt: new Date().toISOString(),
                        current: projects.length === 0
                    });
                    
                    hideAddModal();
                    renderProjects();
                });
                
                // 编辑表单提交处理（只允许修改中文名）
                document.getElementById('editProjectForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    if (editingIndex === null || projects[editingIndex] === undefined) {
                        hideEditModal();
                        return;
                    }
                    const nameCN = document.getElementById('editProjectNameCN').value.trim();
                    if (!nameCN) {
                        alert('请填写项目中文名');
                        return;
                    }
                    projects[editingIndex].nameCN = nameCN;
                    hideEditModal();
                    renderProjects();
                });
                
                // 点击模态框外部关闭
                window.onclick = function(event) {
                    const modal = document.getElementById('addModal');
                    const editModal = document.getElementById('editModal');
                    const importModal = document.getElementById('importModal');
                    if (event.target === modal) {
                        hideAddModal();
                    } else if (event.target === editModal) {
                        hideEditModal();
                    } else if (event.target === importModal) {
                        hideImportModal();
                    }
                }
                
                // 初始化页面
                renderProjects();

                function validateImportedProject(p) {
                    if (!p || typeof p !== 'object') return false;
                    const neededKeys = ['name_cn','name_en','is_active','plc_settings'];
                    for (const k of neededKeys) {
                        if (!(k in p)) return false;
                    }
                    if (typeof p.name_cn !== 'string' || typeof p.name_en !== 'string') return false;
                    if (typeof p.is_active !== 'boolean') return false;
                    if (typeof p.plc_settings !== 'object' || p.plc_settings === null) return false;
                    const ps = p.plc_settings;
                    const plcNeeded = ['device_type','byte_order','heartbeat','timeout','refresh_interval_ms','address','port','username','password'];
                    for (const k of plcNeeded) {
                        if (!(k in ps)) return false;
                    }
                    if (typeof ps.device_type !== 'string' || typeof ps.byte_order !== 'string') return false;
                    if (typeof ps.address !== 'string' || typeof ps.username !== 'string' || typeof ps.password !== 'string') return false;
                    if (typeof ps.heartbeat !== 'number' || typeof ps.timeout !== 'number' || typeof ps.refresh_interval_ms !== 'number' || typeof ps.port !== 'number') return false;
                    return true;
                }

                function hideEditModal() {
                    document.getElementById('editModal').style.display = 'none';
                    document.getElementById('editProjectForm').reset();
                    editingIndex = null;
                }
                
                function importProjects() {
                    showImportModal();
                }

                function exportProjects() {
                    let currentProject = projects.find(p => p.current);
                    if (!currentProject && selectedProjectId !== null) {
                        currentProject = projects[selectedProjectId];
                    }
                    if (!currentProject) {
                        alert('请先选择或激活一个项目');
                        return;
                    }
                    const obj = {
                        name_cn: currentProject.nameCN || '',
                        name_en: currentProject.nameEN || '',
                        is_active: true,
                        plc_settings: currentProject.plcSettings || {}
                    };
                    if (window.bridge) {
                        bridge.exportProject(JSON.stringify(obj));
                        alert('已请求导出');
                    } else {
                        alert('导出失败：桥接未初始化');
                    }
                }
                
                function confirmImportProject() {
                    if (!importFileEl) {
                        alert('请选择JSON文件');
                        return;
                    }
                    const file = importFileEl.files && importFileEl.files[0];
                    if (!file) {
                        alert('请选择JSON文件');
                        return;
                    }
                    const extOk = /\.json$/i.test(file.name);
                    const typeOk = file.type === 'application/json';
                    if (!extOk || !typeOk) {
                        alert('仅允许上传JSON文件');
                        return;
                    }
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            const data = JSON.parse(e.target.result);
                            if (!validateImportedProject(data)) {
                                alert('导入失败：JSON结构不符合 project.json 规范');
                                return;
                            }
                            const nameEN = data.name_en.trim();
                            if (projects.some(p => p.nameEN.toLowerCase() === nameEN.toLowerCase())) {
                                alert('导入失败：项目英文名已存在');
                                return;
                            }
                            projects.push({
                                id: Date.now(),
                                nameCN: data.name_cn,
                                nameEN: data.name_en,
                                description: '',
                                status: 'pending',
                                createdAt: new Date().toISOString(),
                                current: data.is_active === true ? (projects.length === 0 ? true : false) : false,
                                plcSettings: data.plc_settings || {}
                            });
                            renderProjects();
                            saveProjects();
                            hideImportModal();
                            alert('导入成功');
                        } catch (err) {
                            alert('导入失败：' + err.message);
                        }
                    };
                    reader.readAsText(file, 'utf-8');
                }
            </script>
        </body>
        </html>
        """
        
        # 替换初始值
        html_content = html_content.replace("__PROJECTS__", json.dumps(js_projects, ensure_ascii=False))
        
        # 保存HTML到临时文件
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "project_page.html")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 加载HTML到WebView
        self.page.load(QUrl.fromLocalFile(html_path))

class ProjectBridge(QObject):
    @pyqtSlot(str)
    def saveProjects(self, projects_json):
        """保存项目列表到JSON文件"""
        try:
            js_projects = json.loads(projects_json)
            # Convert camelCase back to snake_case for storage
            db_projects = []
            for p in js_projects:
                db_p = {
                    "name_cn": p.get("nameCN", ""),
                    "name_en": p.get("nameEN", ""),
                    "is_active": p.get("current", False),
                    "plc_settings": p.get("plcSettings", {})
                }
                db_projects.append(db_p)
            
            projects_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.json")
            with open(projects_path, 'w', encoding='utf-8') as f:
                json.dump(db_projects, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving projects: {e}")
    
    @pyqtSlot(str)
    def exportProject(self, project_json):
        try:
            obj = json.loads(project_json)
            default_name = "project_" + (obj.get("name_en", "project")) + ".json"
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_path = os.path.join(base_dir, default_name)
            filename, _ = QFileDialog.getSaveFileName(None, "导出项目", default_path, "JSON Files (*.json)")
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(obj, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error exporting project: {e}")
