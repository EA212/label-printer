import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import json
import math

class CoordinateLabelGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("坐标标签生成器（精确布局）")
        self.root.geometry("1050x700")
        self.root.resizable(True, True)
        
        # 先初始化status_var，确保在加载配置前可用
        self.status_var = tk.StringVar(value="就绪")
        
        # 配置文件路径
        self.config_file = "label_generator_config.json"
        
        # A4纸张尺寸（毫米）和对应像素（300dpi）
        self.a4_width_mm = 210
        self.a4_height_mm = 297
        self.a4_width_px = 2480  # 300dpi下A4宽度像素
        self.a4_height_px = 3508  # 300dpi下A4高度像素
        self.mm_to_px = self.a4_width_px / self.a4_width_mm  # 毫米到像素的转换因子（约11.811像素/毫米）
        
        # 网格设置 - 统一为3毫米
        self.grid_size_mm = 3  # 网格尺寸（毫米）
        self.grid_size_px = int(round(self.grid_size_mm * self.mm_to_px))  # 转换为像素
        
        # 边距设置（毫米）
        self.margin_left_mm = 10
        self.margin_right_mm = 10
        self.margin_top_mm = 10
        self.margin_bottom_mm = 10
        
        # 转换为像素
        self.margin_left_px = int(round(self.margin_left_mm * self.mm_to_px))
        self.margin_right_px = int(round(self.margin_right_mm * self.mm_to_px))
        self.margin_top_px = int(round(self.margin_top_mm * self.mm_to_px))
        self.margin_bottom_px = int(round(self.margin_bottom_mm * self.mm_to_px))
        
        # 有效打印区域
        self.print_width_px = self.a4_width_px - self.margin_left_px - self.margin_right_px
        self.print_height_px = self.a4_height_px - self.margin_top_px - self.margin_bottom_px
        
        # 设置中文字体支持
        self.system_fonts = ["simhei.ttf", "microsoftyahei.ttf", "simsun.ttc", "simkai.ttf", 
                             "msyh.ttc", "msyhbd.ttc", "simfang.ttf"]
        self.selected_font = None
        
        # 数据存储
        self.coordinates_df = None
        self.devices_df = None
        self.generated_images = []  # 存储所有生成的图像
        self.current_page = 0
        self.zoom_factor = 0.5  # 默认缩放比例
        
        # 点标记设置（始终打印）
        self.print_dot = True  # 强制打印点标记
        self.dot_radius_px = 2  # 点标记半径（像素）
        
        # 参数变量初始化 - 使用用户提供的默认参数
        self._init_variables()
        
        # 加载保存的配置，如果没有则使用默认参数
        self._load_config()
        
        # 创建UI
        self._create_widgets()
        
    def _init_variables(self):
        # 用户提供的默认参数（6排14行）
        default_params = {
            "points_per_page": 84,  # 6×14=84
            "x_spacing": 90,       # 列间距百分比
            "y_spacing": 57,       # 行间距百分比
            "font_size": 30,
            "spacing": 4,
            "number_spacing": 2,   # 数字间隔（新增参数）
            "x_offset": 20,
            "y_offset": 36,
            "x_stretch": 100,
            "y_stretch": 100,
            "debug_mode": True,
            "rows": 14,    # 行数设置
            "columns": 6   # 排数设置
        }
        
        # 分页和行列设置
        self.points_per_page_var = tk.IntVar(value=default_params["points_per_page"])
        self.rows_var = tk.IntVar(value=default_params["rows"])
        self.columns_var = tk.IntVar(value=default_params["columns"])
        
        # 点间距调整（百分比）
        self.x_spacing_var = tk.IntVar(value=default_params["x_spacing"])
        self.y_spacing_var = tk.IntVar(value=default_params["y_spacing"])
        
        # 文字设置
        self.font_size_var = tk.IntVar(value=default_params["font_size"])
        self.spacing_var = tk.IntVar(value=default_params["spacing"])
        # 新增：数字间隔参数（仅影响设备码和密码）
        self.number_spacing_var = tk.IntVar(value=default_params["number_spacing"])
        
        # 位置微调（像素）
        self.x_offset_var = tk.IntVar(value=default_params["x_offset"])
        self.y_offset_var = tk.IntVar(value=default_params["y_offset"])
        
        # 文字变形
        self.x_stretch_var = tk.IntVar(value=default_params["x_stretch"])
        self.y_stretch_var = tk.IntVar(value=default_params["y_stretch"])
        
        # 调试模式
        self.debug_mode_var = tk.BooleanVar(value=default_params["debug_mode"])
        
        # 网格打印选项
        self.print_grid_var = tk.BooleanVar(value=False)
    
    def _create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧带滚动的控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制选项", padding="5")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 添加滚动条
        canvas = tk.Canvas(control_frame, width=300, height=600)
        scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 内容框架 - 使用紧凑布局
        content_frame = ttk.Frame(scrollable_frame, padding="5")
        content_frame.pack(fill=tk.X)
        
        # 坐标文件选择
        ttk.Label(content_frame, text="坐标CSV文件:").pack(anchor=tk.W, pady=(5, 2))
        self.coord_file_var = tk.StringVar()
        ttk.Entry(content_frame, textvariable=self.coord_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(content_frame, text="浏览...", command=self._browse_coord_file).pack(fill=tk.X, pady=(0, 8))
        
        # 设备文件选择
        ttk.Label(content_frame, text="设备信息CSV文件:").pack(anchor=tk.W, pady=(5, 2))
        self.device_file_var = tk.StringVar()
        ttk.Entry(content_frame, textvariable=self.device_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(content_frame, text="浏览...", command=self._browse_device_file).pack(fill=tk.X, pady=(0, 8))
        
        # 分页和行列设置
        layout_frame = ttk.LabelFrame(content_frame, text="布局设置", padding="5")
        layout_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(layout_frame, text="行数:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.rows_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(layout_frame, text="排数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.columns_var, width=10).grid(row=1, column=1, pady=2)
        
        ttk.Label(layout_frame, text="每页点数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.points_per_page_var, width=10).grid(row=2, column=1, pady=2)
        
        # 点间距调整
        spacing_frame = ttk.LabelFrame(content_frame, text="间距调整(%)", padding="5")
        spacing_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(spacing_frame, text="列间距:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(spacing_frame, textvariable=self.x_spacing_var, width=10).grid(row=0, column=1, pady=2)
        ttk.Label(spacing_frame, text="(第1列到第6列平均分布)").grid(row=0, column=2, sticky=tk.W, pady=2)
        
        ttk.Label(spacing_frame, text="行间距:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(spacing_frame, textvariable=self.y_spacing_var, width=10).grid(row=1, column=1, pady=2)
        ttk.Label(spacing_frame, text="(第1行到第14行平均分布)").grid(row=1, column=2, sticky=tk.W, pady=2)
        
        # 文字设置
        text_settings_frame = ttk.LabelFrame(content_frame, text="文字设置(像素)", padding="5")
        text_settings_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(text_settings_frame, text="文字高度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(text_settings_frame, textvariable=self.font_size_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(text_settings_frame, text="上下间隔:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(text_settings_frame, textvariable=self.spacing_var, width=10).grid(row=1, column=1, pady=2)
        
        # 新增：数字间隔设置
        ttk.Label(text_settings_frame, text="数字间隔:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(text_settings_frame, textvariable=self.number_spacing_var, width=10).grid(row=2, column=1, pady=2)
        ttk.Label(text_settings_frame, text="(仅设备码和密码)", font=('Arial', 8)).grid(row=2, column=2, sticky=tk.W, pady=2)
        
        # 位置微调
        position_frame = ttk.LabelFrame(content_frame, text="文字位置微调(像素)", padding="5")
        position_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(position_frame, text="X偏移:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(position_frame, textvariable=self.x_offset_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(position_frame, text="Y偏移:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(position_frame, textvariable=self.y_offset_var, width=10).grid(row=1, column=1, pady=2)
        
        # 文字变形
        transform_frame = ttk.LabelFrame(content_frame, text="文字变形(%)", padding="5")
        transform_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(transform_frame, text="X拉伸:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(transform_frame, textvariable=self.x_stretch_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(transform_frame, text="Y拉伸:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(transform_frame, textvariable=self.y_stretch_var, width=10).grid(row=1, column=1, pady=2)
        
        # 调试和打印设置
        print_frame = ttk.LabelFrame(content_frame, text="打印设置", padding="5")
        print_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Checkbutton(print_frame, text="调试模式(显示3mm网格和标度)", variable=self.debug_mode_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(print_frame, text="导出时包含网格", variable=self.print_grid_var).pack(anchor=tk.W, pady=2)
        
        # 网格信息显示
        ttk.Label(print_frame, text=f"网格尺寸: {self.grid_size_mm}mm", font=('Arial', 8)).pack(anchor=tk.W)
        ttk.Label(print_frame, text=f"等效像素: {self.grid_size_px}px", font=('Arial', 8)).pack(anchor=tk.W)
        
        # 参数保存
        param_frame = ttk.Frame(content_frame)
        param_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Button(param_frame, text="保存参数", command=self._save_config).pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(param_frame, text="默认参数", command=self._load_default_config).pack(side=tk.RIGHT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 操作按钮
        action_frame = ttk.Frame(content_frame)
        action_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Button(action_frame, text="生成多页", command=self._generate_all_pages).pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(action_frame, text="导出所有页", command=self._export_all_pages).pack(side=tk.RIGHT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 右侧预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览（与打印效果一致）", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 预览工具栏
        preview_toolbar = ttk.Frame(preview_frame)
        preview_toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 分页控制
        ttk.Button(preview_toolbar, text="上一页", command=self._prev_page).pack(side=tk.LEFT, padx=(0, 5))
        self.page_label_var = tk.StringVar(value="页: 0/0")
        ttk.Label(preview_toolbar, textvariable=self.page_label_var).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preview_toolbar, text="下一页", command=self._next_page).pack(side=tk.LEFT, padx=(0, 10))
        
        # 缩放控制
        ttk.Label(preview_toolbar, text="缩放:").pack(side=tk.LEFT, padx=(0, 5))
        self.zoom_var = tk.StringVar(value="20%")
        ttk.Entry(preview_toolbar, textvariable=self.zoom_var, width=5).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preview_toolbar, text="应用", command=self._apply_zoom).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preview_toolbar, text="重置", command=self._reset_zoom).pack(side=tk.LEFT)
        
        # 预览画布容器
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # 预览画布
        self.preview_canvas = tk.Canvas(canvas_container, bg="white")
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.preview_canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.preview_canvas.bind('<Configure>', lambda e: self._update_scroll_region())
        
        # 状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _browse_coord_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            self.coord_file_var.set(filename)
            try:
                self.coordinates_df = pd.read_csv(filename)
                self.status_var.set(f"已加载坐标文件，包含 {len(self.coordinates_df)} 个点")
            except Exception as e:
                messagebox.showerror("错误", f"无法读取坐标文件: {str(e)}")
                self.coordinates_df = None
    
    def _browse_device_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            self.device_file_var.set(filename)
            try:
                self.devices_df = pd.read_csv(filename)
                self.status_var.set(f"已加载设备文件，包含 {len(self.devices_df)} 个设备")
            except Exception as e:
                messagebox.showerror("错误", f"无法读取设备文件: {str(e)}")
                self.devices_df = None
    
    def _get_font(self, size):
        if self.selected_font:
            try:
                return ImageFont.truetype(self.selected_font, size)
            except:
                pass
                
        # 尝试系统字体
        for font_name in self.system_fonts:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                continue
                
        # 如果都失败，使用默认字体
        return ImageFont.load_default()
    
    def _calculate_positions(self, rows, columns):
        """计算行列的平均间距位置"""
        positions = []
        
        # 计算列间距（平均分布）
        if columns > 1:
            col_spacing = self.print_width_px / (columns - 1) * (self.x_spacing_var.get() / 100.0)
        else:
            col_spacing = 0
            
        # 计算行间距（平均分布）
        if rows > 1:
            row_spacing = self.print_height_px / (rows - 1) * (self.y_spacing_var.get() / 100.0)
        else:
            row_spacing = 0
        
        # 计算每个点的位置
        for row in range(rows):
            for col in range(columns):
                x = self.margin_left_px + col * col_spacing
                y = self.margin_top_px + row * row_spacing
                positions.append((x, y))
                
        return positions
    
    def _draw_text_with_spacing(self, draw, text, x, y, font, spacing=0):
        """在指定位置绘制带有字符间距的文本"""
        current_x = x
        for char in text:
            # 绘制单个字符
            draw.text((current_x, y), char, font=font, fill='black')
            # 计算当前字符宽度并加上间距
            char_width = draw.textlength(char, font=font)
            current_x += char_width + spacing
        return current_x - x  # 返回总宽度
    
    def _draw_debug_elements(self, draw, width, height, include_in_export=False):
        """绘制调试元素：3毫米网格和毫米标度尺"""
        # 只有在调试模式或设置了导出包含网格时才绘制
        if not (self.debug_mode_var.get() or include_in_export):
            return
            
        # 绘制3毫米网格（基于精确的毫米到像素转换）
        grid_color = (200, 200, 200, 100) if self.debug_mode_var.get() else (200, 200, 200)
        
        # 横向网格线（Y方向）
        for y in range(0, height, self.grid_size_px):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
        # 纵向网格线（X方向）
        for x in range(0, width, self.grid_size_px):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        
        # 绘制毫米标度尺（边缘刻度）- 仅在调试模式显示
        if self.debug_mode_var.get():
            ruler_color = (100, 100, 100)
            font = self._get_font(10)
            mm_major_interval = 10  # 主刻度间隔（毫米）
            mm_minor_interval = self.grid_size_mm  # 次刻度间隔（等于网格尺寸）
            
            # 转换为像素间隔
            px_major_interval = int(round(mm_major_interval * self.mm_to_px))
            px_minor_interval = self.grid_size_px  # 次刻度等于网格尺寸
            
            # 顶部标度尺
            draw.line([(0, 0), (width, 0)], fill=ruler_color, width=2)
            for x in range(0, width + 1, px_minor_interval):
                # 计算对应的毫米值
                mm_value = int(round(x / self.mm_to_px))
                
                # 主刻度（每10毫米）
                if mm_value % mm_major_interval == 0:
                    draw.line([(x, 0), (x, 15)], fill=ruler_color, width=2)
                    draw.text((x - 10, 15), f"{mm_value}mm", font=font, fill=ruler_color)
                else:
                    # 次刻度（每3毫米，与网格对齐）
                    draw.line([(x, 0), (x, 8)], fill=ruler_color, width=1)
            
            # 左侧标度尺
            draw.line([(0, 0), (0, height)], fill=ruler_color, width=2)
            for y in range(0, height + 1, px_minor_interval):
                # 计算对应的毫米值
                mm_value = int(round(y / self.mm_to_px))
                
                # 主刻度（每10毫米）
                if mm_value % mm_major_interval == 0:
                    draw.line([(0, y), (15, y)], fill=ruler_color, width=2)
                    draw.text((15, y - 5), f"{mm_value}mm", font=font, fill=ruler_color)
                else:
                    # 次刻度（每3毫米，与网格对齐）
                    draw.line([(0, y), (8, y)], fill=ruler_color, width=1)
    
    def _generate_all_pages(self):
        if self.coordinates_df is None or self.devices_df is None:
            messagebox.showerror("错误", "请先加载坐标文件和设备文件")
            return
        
        self.status_var.set("正在生成所有页面...")
        self.root.update()
        
        try:
            # 获取布局设置
            rows = self.rows_var.get()
            columns = self.columns_var.get()
            points_per_page = min(self.points_per_page_var.get(), rows * columns)
            total_devices = len(self.devices_df)
            total_pages = max(1, (total_devices + points_per_page - 1) // points_per_page)
            
            # 计算行列平均分布的位置
            base_positions = self._calculate_positions(rows, columns)
            
            # 获取参数
            font_size = self.font_size_var.get()
            spacing = self.spacing_var.get()
            number_spacing = self.number_spacing_var.get()  # 获取数字间隔参数
            x_offset = self.x_offset_var.get()
            y_offset = self.y_offset_var.get()
            x_stretch = self.x_stretch_var.get() / 100.0
            y_stretch = self.y_stretch_var.get() / 100.0
            debug_mode = self.debug_mode_var.get()
            
            self.generated_images = []
            
            # 为每一页生成图像
            for page in range(total_pages):
                start_idx = page * points_per_page
                end_idx = min((page + 1) * points_per_page, total_devices)
                
                # 创建A4尺寸图像（300dpi: 2480 × 3508像素）
                width, height = self.a4_width_px, self.a4_height_px
                image = Image.new('RGB', (width, height), color='white')
                draw = ImageDraw.Draw(image)
                
                # 创建调试图层
                debug_layer = None
                debug_draw = None
                if debug_mode:
                    debug_layer = Image.new('RGBA', (width, height), (255, 255, 255, 0))
                    debug_draw = ImageDraw.Draw(debug_layer)
                    self._draw_debug_elements(debug_draw, width, height)
                
                # 绘制实际网格（如果需要导出）
                if self.print_grid_var.get():
                    self._draw_debug_elements(draw, width, height, include_in_export=True)
                
                # 获取字体
                font = self._get_font(font_size)
                
                # 处理当前页的每个设备
                for i in range(start_idx, end_idx):
                    pos_idx = i % len(base_positions)  # 循环使用计算出的位置
                    
                    try:
                        # 获取计算好的坐标并应用偏移
                        base_x, base_y = base_positions[pos_idx]
                        x = base_x + x_offset
                        y = base_y + y_offset
                        
                        # 获取设备信息
                        device_code = self.devices_df.iloc[i]['device_code']
                        password = self.devices_df.iloc[i]['password']
                        
                        # 准备要显示的文本
                        label1 = "设备码："
                        value1 = str(device_code)
                        label2 = "密钥："
                        value2 = str(password)
                        
                        # 计算标签文字宽度（不包含数字间隔）
                        label1_width = draw.textlength(label1, font=font)
                        label2_width = draw.textlength(label2, font=font)
                        
                        # 计算数字/值的宽度（包含数字间隔）
                        if value1:
                            char1_width = sum(draw.textlength(c, font=font) for c in value1)
                            value1_width = char1_width + (len(value1) - 1) * number_spacing
                        else:
                            value1_width = 0
                            
                        if value2:
                            char2_width = sum(draw.textlength(c, font=font) for c in value2)
                            value2_width = char2_width + (len(value2) - 1) * number_spacing
                        else:
                            value2_width = 0
                        
                        # 总宽度（标签+值）
                        total1_width = (label1_width + value1_width) * x_stretch
                        total2_width = (label2_width + value2_width) * x_stretch
                        
                        # 计算文字位置（以坐标点为中心）
                        text1_x = x - total1_width / 2
                        text1_y = y - (font_size * y_stretch) - spacing
                        
                        text2_x = x - total2_width / 2
                        text2_y = y + spacing
                        
                        # 绘制文字（支持拉伸变形）
                        if x_stretch != 1.0 or y_stretch != 1.0:
                            # 处理第一行文字：标签 + 带间隔的设备码
                            temp_width = int(total1_width * 1.2)
                            temp_height = int(font_size * 1.2)
                            temp_img = Image.new('RGBA', (temp_width, temp_height), (255, 255, 255, 0))
                            temp_draw = ImageDraw.Draw(temp_img)
                            
                            # 绘制标签（无间隔）
                            temp_draw.text((0, 0), label1, font=font, fill='black')
                            # 绘制设备码（有间隔）
                            self._draw_text_with_spacing(temp_draw, value1, label1_width, 0, font, number_spacing)
                            
                            # 应用拉伸变形
                            new_width = int(temp_width * x_stretch)
                            new_height = int(temp_height * y_stretch)
                            transformed_img = temp_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            image.paste(transformed_img, (int(text1_x), int(text1_y)), transformed_img)
                            
                            # 处理第二行文字：标签 + 带间隔的密码
                            temp_width2 = int(total2_width * 1.2)
                            temp_height2 = int(font_size * 1.2)
                            temp_img2 = Image.new('RGBA', (temp_width2, temp_height2), (255, 255, 255, 0))
                            temp_draw2 = ImageDraw.Draw(temp_img2)
                            
                            # 绘制标签（无间隔）
                            temp_draw2.text((0, 0), label2, font=font, fill='black')
                            # 绘制密码（有间隔）
                            self._draw_text_with_spacing(temp_draw2, value2, label2_width, 0, font, number_spacing)
                            
                            # 应用拉伸变形
                            new_width2 = int(temp_width2 * x_stretch)
                            new_height2 = int(temp_height2 * y_stretch)
                            transformed_img2 = temp_img2.resize((new_width2, new_height2), Image.Resampling.LANCZOS)
                            image.paste(transformed_img2, (int(text2_x), int(text2_y)), transformed_img2)
                            
                        else:
                            # 正常绘制，不拉伸
                            # 绘制标签（无间隔）
                            draw.text((text1_x, text1_y), label1, font=font, fill='black')
                            # 绘制设备码（有间隔）
                            self._draw_text_with_spacing(draw, value1, text1_x + label1_width, text1_y, font, number_spacing)
                            
                            # 绘制标签（无间隔）
                            draw.text((text2_x, text2_y), label2, font=font, fill='black')
                            # 绘制密码（有间隔）
                            self._draw_text_with_spacing(draw, value2, text2_x + label2_width, text2_y, font, number_spacing)
                            
                        # 绘制点标记（始终打印）
                        draw.ellipse([
                            (x - self.dot_radius_px, y - self.dot_radius_px),
                            (x + self.dot_radius_px, y + self.dot_radius_px)
                        ], fill='black')
                            
                        # 在调试模式下显示坐标信息
                        if debug_mode and debug_draw:
                            # 显示像素和毫米双坐标
                            mm_x = round(x / self.mm_to_px, 1)
                            mm_y = round(y / self.mm_to_px, 1)
                            debug_draw.text((x + 10, y), f"({int(x)}px/{mm_x}mm, {int(y)}px/{mm_y}mm)", 
                                          font=font, fill='red')
                            
                    except Exception as e:
                        messagebox.showerror("错误", f"处理第 {i+1} 个设备时出错: {str(e)}")
                        continue
                
                # 将调试图层合并到主图像
                if debug_mode and debug_layer:
                    image = Image.alpha_composite(image.convert('RGBA'), debug_layer).convert('RGB')
                
                self.generated_images.append(image)
                self.status_var.set(f"已生成第 {page+1}/{total_pages} 页")
                self.root.update()
            
            self.current_page = 0
            self._update_preview()
            self.status_var.set(f"已完成所有 {total_pages} 页的生成")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成页面时出错: {str(e)}")
            self.status_var.set("生成失败")
    
    def _update_preview(self):
        if not self.generated_images:
            self.preview_canvas.delete("all")
            self.page_label_var.set("页: 0/0")
            return
        
        total_pages = len(self.generated_images)
        self.page_label_var.set(f"页: {self.current_page+1}/{total_pages}")
        
        # 获取当前页图像并缩放 - 保持精确比例
        current_image = self.generated_images[self.current_page]
        scaled_width = int(current_image.width * self.zoom_factor)
        scaled_height = int(current_image.height * self.zoom_factor)
        preview_img = current_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        
        # 转换为Tkinter可用的图像格式
        self.preview_photo = ImageTk.PhotoImage(preview_img)
        
        # 在画布上显示
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_photo)
        self._update_scroll_region()
    
    def _update_scroll_region(self):
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
    
    def _prev_page(self):
        if self.generated_images and self.current_page > 0:
            self.current_page -= 1
            self._update_preview()
    
    def _next_page(self):
        if self.generated_images and self.current_page < len(self.generated_images) - 1:
            self.current_page += 1
            self._update_preview()
    
    def _apply_zoom(self):
        try:
            # 从输入框获取百分比并转换为缩放因子
            zoom_percent = int(self.zoom_var.get().replace('%', ''))
            self.zoom_factor = max(0.1, min(1.0, zoom_percent / 100.0))
            self.zoom_var.set(f"{int(self.zoom_factor * 100)}%")
            self._update_preview()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的缩放百分比")
    
    def _reset_zoom(self):
        self.zoom_factor = 0.2
        self.zoom_var.set("20%")
        self._update_preview()
    
    def _save_config(self):
        """保存当前参数到配置文件"""
        config = {
            "points_per_page": self.points_per_page_var.get(),
            "rows": self.rows_var.get(),
            "columns": self.columns_var.get(),
            "x_spacing": self.x_spacing_var.get(),
            "y_spacing": self.y_spacing_var.get(),
            "font_size": self.font_size_var.get(),
            "spacing": self.spacing_var.get(),
            "number_spacing": self.number_spacing_var.get(),  # 保存数字间隔参数
            "x_offset": self.x_offset_var.get(),
            "y_offset": self.y_offset_var.get(),
            "x_stretch": self.x_stretch_var.get(),
            "y_stretch": self.y_stretch_var.get(),
            "debug_mode": self.debug_mode_var.get(),
            "print_grid": self.print_grid_var.get()
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "参数已保存")
            self.status_var.set("参数已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存参数失败: {str(e)}")
    
    def _load_config(self):
        """从配置文件加载参数"""
        if not os.path.exists(self.config_file):
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载参数
            self.points_per_page_var.set(config.get("points_per_page", 84))
            self.rows_var.set(config.get("rows", 14))
            self.columns_var.set(config.get("columns", 6))
            self.x_spacing_var.set(config.get("x_spacing", 100))
            self.y_spacing_var.set(config.get("y_spacing", 100))
            self.font_size_var.set(config.get("font_size", 30))
            self.spacing_var.set(config.get("spacing", 4))
            self.number_spacing_var.set(config.get("number_spacing", 2))  # 加载数字间隔参数
            self.x_offset_var.set(config.get("x_offset", -23))
            self.y_offset_var.set(config.get("y_offset", 36))
            self.x_stretch_var.set(config.get("x_stretch", 130))
            self.y_stretch_var.set(config.get("y_stretch", 100))
            self.debug_mode_var.set(config.get("debug_mode", True))
            self.print_grid_var.set(config.get("print_grid", False))
            
            self.status_var.set("已加载保存的参数")
        except Exception as e:
            self.status_var.set(f"加载参数失败: {str(e)}")
    
    def _load_default_config(self):
        """加载用户提供的默认参数（6排14行）"""
        default_params = {
            "points_per_page": 84,
            "rows": 14,
            "columns": 6,
            "x_spacing": 100,
            "y_spacing": 100,
            "font_size": 30,
            "spacing": 4,
            "number_spacing": 2,  # 默认数字间隔
            "x_offset": -23,
            "y_offset": 36,
            "x_stretch": 130,
            "y_stretch": 100,
            "debug_mode": True,
            "print_grid": False
        }
        
        self.points_per_page_var.set(default_params["points_per_page"])
        self.rows_var.set(default_params["rows"])
        self.columns_var.set(default_params["columns"])
        self.x_spacing_var.set(default_params["x_spacing"])
        self.y_spacing_var.set(default_params["y_spacing"])
        self.font_size_var.set(default_params["font_size"])
        self.spacing_var.set(default_params["spacing"])
        self.number_spacing_var.set(default_params["number_spacing"])  # 设置默认数字间隔
        self.x_offset_var.set(default_params["x_offset"])
        self.y_offset_var.set(default_params["y_offset"])
        self.x_stretch_var.set(default_params["x_stretch"])
        self.y_stretch_var.set(default_params["y_stretch"])
        self.debug_mode_var.set(default_params["debug_mode"])
        self.print_grid_var.set(default_params["print_grid"])
        
        self.status_var.set("已加载默认参数")
    
    def _export_all_pages(self):
        """导出与预览完全一致的图像"""
        if not self.generated_images:
            messagebox.showerror("错误", "请先生成页面")
            return
        
        self.status_var.set("正在导出所有页面...")
        self.root.update()
        
        try:
            # 询问保存目录
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                self.status_var.set("导出取消")
                return
            
            total_pages = len(self.generated_images)
            
            # 导出已生成的图像（与预览完全一致）
            for page in range(total_pages):
                # 直接保存已生成的图像，确保与预览一致
                filename = os.path.join(output_dir, f"label_page_{page+1}.png")
                self.generated_images[page].save(filename, dpi=(300, 300))
                self.status_var.set(f"已导出第 {page+1}/{total_pages} 页")
                self.root.update()
            
            self.status_var.set(f"所有 {total_pages} 页已成功导出")
            messagebox.showinfo("成功", f"所有 {total_pages} 页已导出至:\n{output_dir}")
            messagebox.showinfo("注意", "导出的图像与预览完全一致，包含所有标记点")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出页面时出错: {str(e)}")
            self.status_var.set("导出失败")

if __name__ == "__main__":
    root = tk.Tk()
    app = CoordinateLabelGenerator(root)
    root.mainloop()
