import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
from PIL import ImageTk

class LabelGeneratorUI:
    def __init__(self, root, core):
        self.root = root
        self.core = core
        self.root.title("坐标标签生成器（精确布局）")
        self.root.geometry("1050x700")
        self.root.resizable(True, True)
        
        # 状态变量
        self.status_var = tk.StringVar(value="就绪")
        
        # 数据存储相关变量
        self.coord_file_var = tk.StringVar()
        self.device_file_var = tk.StringVar()
        self.config_file_var = tk.StringVar(value=self.core.config_file)
        
        # 预览相关变量
        self.preview_photo = None
        self.current_page = 0
        self.zoom_factor = 0.5  # 默认缩放比例
        self.zoom_var = tk.StringVar(value="50%")
        self.page_label_var = tk.StringVar(value="页: 0/0")
        
        # 裁切设置
        self.crop_margin_var = tk.IntVar(value=5)  # 裁切边距(mm)
        
        # 初始化变量
        self._init_variables()
        
        # 创建UI
        self._create_widgets()
        
        # 加载配置
        self._load_config()
    
    def _init_variables(self):
        # 分页和行列设置
        self.points_per_page_var = tk.IntVar(value=self.core.default_params["points_per_page"])
        self.rows_var = tk.IntVar(value=self.core.default_params["rows"])
        self.columns_var = tk.IntVar(value=self.core.default_params["columns"])
        
        # 点间距调整（百分比）
        self.x_spacing_var = tk.IntVar(value=self.core.default_params["x_spacing"])
        self.y_spacing_var = tk.IntVar(value=self.core.default_params["y_spacing"])
        
        # 文字设置
        self.font_size_var = tk.IntVar(value=self.core.default_params["font_size"])
        self.spacing_var = tk.IntVar(value=self.core.default_params["spacing"])
        self.number_spacing_var = tk.IntVar(value=self.core.default_params["number_spacing"])
        
        # 位置微调（像素）
        self.x_offset_var = tk.IntVar(value=self.core.default_params["x_offset"])
        self.y_offset_var = tk.IntVar(value=self.core.default_params["y_offset"])
        
        # 文字变形
        self.x_stretch_var = tk.IntVar(value=self.core.default_params["x_stretch"])
        self.y_stretch_var = tk.IntVar(value=self.core.default_params["y_stretch"])
        
        # 调试模式和打印设置
        self.debug_mode_var = tk.BooleanVar(value=self.core.default_params["debug_mode"])
        self.print_grid_var = tk.BooleanVar(value=self.core.default_params["print_grid"])
        self.print_dot_var = tk.BooleanVar(value=self.core.default_params["print_dot"])
        
        # 自定义高度设置（毫米）
        self.custom_height_mm_var = tk.IntVar(value=self.core.default_params["custom_height_mm"])
    
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
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
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
        ttk.Entry(content_frame, textvariable=self.coord_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(content_frame, text="浏览...", command=self._browse_coord_file).pack(fill=tk.X, pady=(0, 8))
        
        # 设备文件选择
        ttk.Label(content_frame, text="设备信息CSV文件:").pack(anchor=tk.W, pady=(5, 2))
        ttk.Entry(content_frame, textvariable=self.device_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(content_frame, text="浏览...", command=self._browse_device_file).pack(fill=tk.X, pady=(0, 8))
        
        # 配置文件选择
        ttk.Label(content_frame, text="配置文件:").pack(anchor=tk.W, pady=(5, 2))
        ttk.Entry(content_frame, textvariable=self.config_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(content_frame, text="浏览...", command=self._browse_config_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(content_frame, text="加载", command=self._load_config).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Frame(content_frame).pack(fill=tk.X, pady=(0, 8))  # 分隔
        
        # 纸张设置
        paper_frame = ttk.LabelFrame(content_frame, text="纸张设置", padding="5")
        paper_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(paper_frame, text="宽度: 210mm (A4)").grid(row=0, column=0, sticky=tk.W, pady=2, columnspan=2)
        ttk.Label(paper_frame, text="高度(mm):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(paper_frame, textvariable=self.custom_height_mm_var, width=10).grid(row=1, column=1, pady=2, sticky=tk.W)
        ttk.Button(paper_frame, text="应用", command=self._apply_paper_settings).grid(row=1, column=2, pady=2, padx=5)
        
        # 裁切设置
        crop_frame = ttk.LabelFrame(content_frame, text="导出裁切设置", padding="5")
        crop_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(crop_frame, text="裁切边距(mm):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(crop_frame, textvariable=self.crop_margin_var, width=10).grid(row=0, column=1, pady=2, sticky=tk.W)
        ttk.Label(crop_frame, text="(导出时会裁切掉边缘此尺寸)", font=('Arial', 8)).grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # 分页和行列设置
        layout_frame = ttk.LabelFrame(content_frame, text="布局设置", padding="5")
        layout_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(layout_frame, text="行数:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.rows_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(layout_frame, text="排数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.columns_var, width=10).grid(row=1, column=1, pady=2)
        
        ttk.Label(layout_frame, text="每页点数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(layout_frame, textvariable=self.points_per_page_var, width=10).grid(row=2, column=1, pady=2)
        
        # 其他设置保持不变...
        # 点间距调整
        spacing_frame = ttk.LabelFrame(content_frame, text="间距调整(%)", padding="5")
        spacing_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(spacing_frame, text="列间距:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(spacing_frame, textvariable=self.x_spacing_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(spacing_frame, text="行间距:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(spacing_frame, textvariable=self.y_spacing_var, width=10).grid(row=1, column=1, pady=2)
        
        # 文字设置
        text_settings_frame = ttk.LabelFrame(content_frame, text="文字设置(像素)", padding="5")
        text_settings_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(text_settings_frame, text="文字高度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(text_settings_frame, textvariable=self.font_size_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(text_settings_frame, text="上下间隔:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(text_settings_frame, textvariable=self.spacing_var, width=10).grid(row=1, column=1, pady=2)
        
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
        ttk.Checkbutton(print_frame, text="导出时包含坐标点", variable=self.print_dot_var).pack(anchor=tk.W, pady=2)
        
        # 网格信息显示
        ttk.Label(print_frame, text=f"网格尺寸: {self.core.grid_size_mm}mm", font=('Arial', 8)).pack(anchor=tk.W)
        ttk.Label(print_frame, text=f"等效像素: {self.core.grid_size_px}px", font=('Arial', 8)).pack(anchor=tk.W)
        
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
        ttk.Label(preview_toolbar, textvariable=self.page_label_var).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preview_toolbar, text="下一页", command=self._next_page).pack(side=tk.LEFT, padx=(0, 10))
        
        # 缩放控制
        ttk.Label(preview_toolbar, text="缩放:").pack(side=tk.LEFT, padx=(0, 5))
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
            self.core.load_coordinates(filename)
            self.status_var.set(f"已加载坐标文件，包含 {len(self.core.coordinates_df)} 个点")
    
    def _browse_device_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            self.device_file_var.set(filename)
            self.core.load_devices(filename)
            self.status_var.set(f"已加载设备文件，包含 {len(self.core.devices_df)} 个设备")
    
    def _browse_config_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.config_file_var.set(filename)
            self.core.config_file = filename
            self._load_config()
    
    def _load_config(self):
        config_loaded = self.core.load_config(self.config_file_var.get())
        if config_loaded:
            # 更新UI控件值
            self.points_per_page_var.set(self.core.config["points_per_page"])
            self.rows_var.set(self.core.config["rows"])
            self.columns_var.set(self.core.config["columns"])
            self.x_spacing_var.set(self.core.config["x_spacing"])
            self.y_spacing_var.set(self.core.config["y_spacing"])
            self.font_size_var.set(self.core.config["font_size"])
            self.spacing_var.set(self.core.config["spacing"])
            self.number_spacing_var.set(self.core.config["number_spacing"])
            self.x_offset_var.set(self.core.config["x_offset"])
            self.y_offset_var.set(self.core.config["y_offset"])
            self.x_stretch_var.set(self.core.config["x_stretch"])
            self.y_stretch_var.set(self.core.config["y_stretch"])
            self.debug_mode_var.set(self.core.config["debug_mode"])
            self.print_grid_var.set(self.core.config["print_grid"])
            self.print_dot_var.set(self.core.config["print_dot"])
            self.custom_height_mm_var.set(self.core.config["custom_height_mm"])
            if "crop_margin" in self.core.config:
                self.crop_margin_var.set(self.core.config["crop_margin"])
            
            # 应用纸张设置
            self.core.update_paper_size(self.custom_height_mm_var.get())
            self.status_var.set("已加载配置文件")
        else:
            self.status_var.set("使用默认配置")
    
    def _save_config(self):
        # 收集当前配置
        config = {
            "points_per_page": self.points_per_page_var.get(),
            "rows": self.rows_var.get(),
            "columns": self.columns_var.get(),
            "x_spacing": self.x_spacing_var.get(),
            "y_spacing": self.y_spacing_var.get(),
            "font_size": self.font_size_var.get(),
            "spacing": self.spacing_var.get(),
            "number_spacing": self.number_spacing_var.get(),
            "x_offset": self.x_offset_var.get(),
            "y_offset": self.y_offset_var.get(),
            "x_stretch": self.x_stretch_var.get(),
            "y_stretch": self.y_stretch_var.get(),
            "debug_mode": self.debug_mode_var.get(),
            "print_grid": self.print_grid_var.get(),
            "print_dot": self.print_dot_var.get(),
            "custom_height_mm": self.custom_height_mm_var.get(),
            "crop_margin": self.crop_margin_var.get()  # 保存裁切边距
        }
        
        if self.core.save_config(config, self.config_file_var.get()):
            messagebox.showinfo("成功", "参数已保存")
            self.status_var.set("参数已保存")
        else:
            messagebox.showerror("错误", "保存参数失败")
    
    def _load_default_config(self):
        self.core.load_default_config()
        self._init_variables()
        self.status_var.set("已加载默认参数")
    
    def _apply_paper_settings(self):
        try:
            height_mm = self.custom_height_mm_var.get()
            if height_mm <= 0:
                raise ValueError("高度必须为正数")
            self.core.update_paper_size(height_mm)
            messagebox.showinfo("成功", f"纸张高度已设置为 {height_mm}mm")
            self.status_var.set(f"纸张高度: {height_mm}mm")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
    
    def _generate_all_pages(self):
        if not self.core.coordinates_df or not self.core.devices_df:
            messagebox.showerror("错误", "请先加载坐标文件和设备文件")
            return
        
        self.status_var.set("正在生成所有页面...")
        self.root.update()
        
        # 收集参数
        params = {
            "rows": self.rows_var.get(),
            "columns": self.columns_var.get(),
            "points_per_page": self.points_per_page_var.get(),
            "x_spacing": self.x_spacing_var.get(),
            "y_spacing": self.y_spacing_var.get(),
            "font_size": self.font_size_var.get(),
            "spacing": self.spacing_var.get(),
            "number_spacing": self.number_spacing_var.get(),
            "x_offset": self.x_offset_var.get(),
            "y_offset": self.y_offset_var.get(),
            "x_stretch": self.x_stretch_var.get() / 100.0,
            "y_stretch": self.y_stretch_var.get() / 100.0,
            "debug_mode": self.debug_mode_var.get(),
            "print_grid": self.print_grid_var.get(),
            "print_dot": self.print_dot_var.get()
        }
        
        # 生成页面
        success, total_pages = self.core.generate_all_pages(params)
        if success:
            self.current_page = 0
            self._update_preview()
            self.status_var.set(f"已完成所有 {total_pages} 页的生成")
        else:
            self.status_var.set("生成失败")
    
    def _update_preview(self):
        if not self.core.generated_images:
            self.preview_canvas.delete("all")
            self.page_label_var.set("页: 0/0")
            return
        
        total_pages = len(self.core.generated_images)
        self.page_label_var.set(f"页: {self.current_page+1}/{total_pages}")
        
        # 获取当前页图像并缩放
        current_image = self.core.generated_images[self.current_page]
        scaled_width = int(current_image.width * self.zoom_factor)
        scaled_height = int(current_image.height * self.zoom_factor)
        preview_img = self.core.resize_image(current_image, scaled_width, scaled_height)
        
        # 转换为Tkinter可用的图像格式
        self.preview_photo = ImageTk.PhotoImage(preview_img)
        
        # 在画布上显示
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_photo)
        self._update_scroll_region()
    
    def _update_scroll_region(self):
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
    
    def _prev_page(self):
        if self.core.generated_images and self.current_page > 0:
            self.current_page -= 1
            self._update_preview()
    
    def _next_page(self):
        if self.core.generated_images and self.current_page < len(self.core.generated_images) - 1:
            self.current_page += 1
            self._update_preview()
    
    def _apply_zoom(self):
        try:
            # 从输入框获取百分比并转换为缩放因子
            zoom_percent = int(self.zoom_var.get().replace('%', ''))
            self.zoom_factor = max(0.1, min(2.0, zoom_percent / 100.0))
            self.zoom_var.set(f"{int(self.zoom_factor * 100)}%")
            self._update_preview()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的缩放百分比")
    
    def _reset_zoom(self):
        self.zoom_factor = 0.5
        self.zoom_var.set("50%")
        self._update_preview()
    
    def _export_all_pages(self):
        if not self.core.generated_images:
            messagebox.showerror("错误", "请先生成页面")
            return
        
        self.status_var.set("正在导出所有页面...")
        self.root.update()
        
        # 询问保存目录
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            self.status_var.set("导出取消")
            return
        
        # 获取裁切边距(mm)
        crop_margin_mm = self.crop_margin_var.get()
        
        # 导出页面（带裁切）
        success, total_pages = self.core.export_all_pages(output_dir, crop_margin_mm)
        if success:
            self.status_var.set(f"所有 {total_pages} 页已成功导出")
            messagebox.showinfo("成功", f"所有 {total_pages} 页已导出至:\n{output_dir}")
        else:
            self.status_var.set("导出失败")
