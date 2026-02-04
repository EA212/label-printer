import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import csv
import os
import math
import json
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageOps

class BarcodeDesigner:
    def __init__(self, root):
        self.root = root
        self.root.title("条码标签设计器")
        self.root.geometry("1400x900")
        
        # 单位转换相关
        self.dpi = 300
        self.mm_per_inch = 25.4
        self.pixels_per_mm = self.dpi / self.mm_per_inch  # 300dpi下的像素/毫米
        
        # A4纸尺寸 (mm)
        self.a4_width_mm = 210
        self.a4_height_mm = 297
        self.a4_width_px = int(self.a4_width_mm * self.pixels_per_mm)
        self.a4_height_px = int(self.a4_height_mm * self.pixels_per_mm)
        
        # 显示相关
        self.scale = 3  # 屏幕上3像素代表1毫米
        self.zoom_factor = 1.0
        
        # 条码属性
        self.barcode_width = 40  # mm
        self.barcode_height = 20  # mm
        self.labels = []  # 存储条码信息
        self.csv_columns = []  # 存储CSV文件中的所有列名
        self.selected_label = None
        
        # 全局文字标签属性
        self.global_text_settings = {
            'text': '标签 {id}',  # 默认文本
            'font': 'SimHei',  # 使用支持中文的字体
            'font_size': 12,
            'color': (0, 0, 0),
            'x_offset': 0,  # 相对条码中心的X偏移 (mm)
            'y_offset': 0,  # 相对条码中心的Y偏移 (mm)
            'rotation': 0,
            'scale_x': 1.0,  # X方向缩放
            'scale_y': 1.0,  # Y方向缩放
            'skew_x': 0,     # X方向倾斜角度
            'skew_y': 0      # Y方向倾斜角度
        }
        
        # 图片设置
        self.global_image_settings = {
            'path': '',
            'x_offset': 0,
            'y_offset': 0,
            'scale': 1.0,
            'rotation': 0
        }
        
        # 创建界面
        self.create_widgets()
        
        # 初始化画布
        self.canvas_image = Image.new('RGB', 
                                     (int(self.a4_width_mm * self.scale), 
                                      int(self.a4_height_mm * self.scale)), 
                                     'white')
        self.draw = ImageDraw.Draw(self.canvas_image)
        self.update_canvas()
    
    def px_to_mm(self, px):
        """像素转毫米"""
        return px / self.pixels_per_mm
    
    def mm_to_px(self, mm):
        """毫米转像素"""
        return mm * self.pixels_per_mm
    
    def create_widgets(self):
        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入CSV数据", command=self.import_csv)
        file_menu.add_command(label="保存设计", command=self.save_design)
        file_menu.add_command(label="导出为图片", command=self.export_as_image)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="设置条码尺寸", command=self.set_barcode_size)
        settings_menu.add_command(label="编辑文字标签", command=self.open_text_editor)
        menubar.add_cascade(label="设置", menu=settings_menu)
        
        self.root.config(menu=menubar)
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工具栏
        toolbar = ttk.Frame(main_frame, padding="5")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(toolbar, text="导入CSV", command=self.import_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="设置条码尺寸", command=self.set_barcode_size).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="编辑文字标签", command=self.open_text_editor).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="清除所有", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        ttk.Button(toolbar, text="放大", command=lambda: self.zoom(0.1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="缩小", command=lambda: self.zoom(-0.1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="重置视图", command=self.reset_zoom).pack(side=tk.LEFT, padx=5)
        
        # A4纸张显示区域
        self.paper_frame = ttk.LabelFrame(main_frame, text=f"A4纸张 ({self.a4_width_mm}×{self.a4_height_mm}mm)", padding="10")
        self.paper_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 带滚动条的画布
        canvas_frame = ttk.Frame(self.paper_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.hscroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.vscroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = tk.Canvas(
            canvas_frame, 
            width=int(self.a4_width_mm * self.scale), 
            height=int(self.a4_height_mm * self.scale),
            bg='white',
            xscrollcommand=self.hscroll.set,
            yscrollcommand=self.vscroll.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.hscroll.config(command=self.canvas.xview)
        self.vscroll.config(command=self.canvas.yview)
        
        # 画布事件
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        # 属性面板
        self.properties_frame = ttk.LabelFrame(main_frame, text="标签属性", padding="10")
        self.properties_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        self.properties_frame.configure(width=300)
        
        ttk.Label(self.properties_frame, text="当前选中:").pack(anchor=tk.W, pady=5)
        self.selected_label_info = ttk.Label(self.properties_frame, text="无")
        self.selected_label_info.pack(anchor=tk.W, pady=5)
        
        ttk.Separator(self.properties_frame).pack(fill=tk.X, pady=10)
        
        ttk.Label(self.properties_frame, text="条码尺寸:").pack(anchor=tk.W, pady=5)
        
        size_frame = ttk.Frame(self.properties_frame)
        size_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(size_frame, text="宽度 (mm):").pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value=str(self.barcode_width))
        ttk.Entry(size_frame, textvariable=self.width_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(size_frame, text="高度 (mm):").pack(side=tk.LEFT, padx=5)
        self.height_var = tk.StringVar(value=str(self.barcode_height))
        ttk.Entry(size_frame, textvariable=self.height_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.properties_frame, text="应用尺寸", command=self.apply_size_change).pack(fill=tk.X, pady=10)
        
        # 占位符信息
        ttk.Label(self.properties_frame, text="可用占位符:").pack(anchor=tk.W, pady=5)
        self.placeholders_label = ttk.Label(self.properties_frame, text="请先导入CSV文件", wraplength=250)
        self.placeholders_label.pack(anchor=tk.W, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪 - 请导入CSV数据文件")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def import_csv(self):
        """导入CSV数据文件，自动识别所有列作为可能的占位符"""
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            title="选择CSV数据文件"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:  # 支持带BOM的UTF-8文件
                reader = csv.DictReader(f)
                self.csv_columns = reader.fieldnames  # 获取所有列名
                
                if not self.csv_columns:
                    messagebox.showerror("错误", "CSV文件格式不正确，未找到列名")
                    return
                    
                # 检查是否有必要的坐标列
                required_columns = ['x', 'y']
                if not all(col in [c.lower() for c in self.csv_columns] for col in required_columns):
                    messagebox.showerror("错误", "CSV文件必须包含x和y坐标列")
                    return
                
                temp_labels = []
                for row_num, row in enumerate(reader, 1):
                    try:
                        # 查找x和y列（不区分大小写）
                        x_col = next(col for col in self.csv_columns if col.lower() == 'x')
                        y_col = next(col for col in self.csv_columns if col.lower() == 'y')
                        
                        x_px = float(row[x_col])
                        y_px = float(row[y_col])
                        
                        x_mm = self.px_to_mm(x_px)
                        y_mm = self.px_to_mm(y_px)
                        
                        # 存储当前行的所有数据
                        label_data = {
                            'x': x_mm,
                            'y': y_mm,
                            'width': self.barcode_width,
                            'height': self.barcode_height,
                            'x_px': x_px,
                            'y_px': y_px,
                            'data': row  # 存储当前行的所有数据
                        }
                        
                        temp_labels.append(label_data)
                    except Exception as e:
                        messagebox.showwarning("数据格式错误", f"行 {row_num} 包含无效数据: {str(e)}")
            
            self.labels = temp_labels
            
            # 更新占位符显示
            if self.csv_columns:
                placeholders_text = ", ".join([f"{{{col}}}" for col in self.csv_columns])
                self.placeholders_label.config(text=placeholders_text)
            
            self.selected_label = None
            self.update_scroll_region()
            self.redraw_all_labels()
            self.status_var.set(f"已导入 {len(self.labels)} 条数据，可用占位符: {len(self.csv_columns)}个")
            messagebox.showinfo("成功", f"已成功导入 {len(self.labels)} 条数据\n可用占位符: {', '.join(self.csv_columns)}")
            
        except Exception as e:
            messagebox.showerror("导入失败", f"无法导入文件: {str(e)}")
            self.status_var.set("导入文件失败")
    
    def update_scroll_region(self):
        """更新滚动区域"""
        if not self.labels:
            return
            
        min_x = min(l['x'] for l in self.labels)
        max_x = max(l['x'] for l in self.labels)
        min_y = min(l['y'] for l in self.labels)
        max_y = max(l['y'] for l in self.labels)
        
        padding = 50  # mm
        scroll_width = max(self.a4_width_mm, max_x + padding)
        scroll_height = max(self.a4_height_mm, max_y + padding)
        
        scale = self.scale * self.zoom_factor
        self.canvas.config(scrollregion=(
            0, 0, 
            scroll_width * scale, 
            scroll_height * scale
        ))
    
    def set_barcode_size(self):
        """设置条码尺寸"""
        new_width = simpledialog.askfloat("条码宽度", "请输入条码宽度 (mm):", 
                                         minvalue=5, maxvalue=100, 
                                         initialvalue=self.barcode_width)
        if new_width is None:
            return
            
        new_height = simpledialog.askfloat("条码高度", "请输入条码高度 (mm):", 
                                          minvalue=5, maxvalue=100, 
                                          initialvalue=self.barcode_height)
        if new_height is None:
            return
            
        self.barcode_width = new_width
        self.barcode_height = new_height
        
        for label in self.labels:
            label['width'] = new_width
            label['height'] = new_height
        
        self.width_var.set(str(new_width))
        self.height_var.set(str(new_height))
        
        self.redraw_all_labels()
        self.status_var.set(f"已设置条码尺寸为 {new_width}×{new_height}mm")
    
    def apply_size_change(self):
        """应用尺寸变化"""
        try:
            new_width = float(self.width_var.get())
            new_height = float(self.height_var.get())
            
            if new_width <= 0 or new_height <= 0:
                messagebox.showwarning("无效值", "宽度和高度必须为正数")
                return
                
            if new_width > 100 or new_height > 100:
                messagebox.showwarning("值过大", "宽度和高度不应超过100mm")
                return
                
            if self.selected_label is not None:
                self.labels[self.selected_label]['width'] = new_width
                self.labels[self.selected_label]['height'] = new_height
                self.status_var.set(f"已更新选中标签尺寸为 {new_width}×{new_height}mm")
            else:
                self.barcode_width = new_width
                self.barcode_height = new_height
                for label in self.labels:
                    label['width'] = new_width
                    label['height'] = new_height
                self.status_var.set(f"已更新所有标签尺寸为 {new_width}×{new_height}mm")
                
            self.redraw_all_labels()
            
        except ValueError:
            messagebox.showwarning("无效输入", "请输入有效的数字")
    
    def clear_all(self):
        """清除所有标签"""
        if messagebox.askyesno("确认", "确定要清除所有标签吗?"):
            self.labels = []
            self.csv_columns = []
            self.selected_label = None
            self.selected_label_info.config(text="无")
            self.placeholders_label.config(text="请先导入CSV文件")
            self.redraw_all_labels()
            self.status_var.set("已清除所有标签")
    
    def on_canvas_click(self, event):
        """处理画布点击"""
        if not self.labels:
            return
            
        x = event.x / (self.scale * self.zoom_factor)
        y = event.y / (self.scale * self.zoom_factor)
        
        for i, label in enumerate(self.labels):
            half_w = label['width'] / 2
            half_h = label['height'] / 2
            x1 = label['x'] - half_w
            y1 = label['y'] - half_h
            x2 = label['x'] + half_w
            y2 = label['y'] + half_h
            
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected_label = i
                self.update_selected_label_info()
                self.redraw_all_labels()
                return
        
        self.selected_label = None
        self.selected_label_info.config(text="无")
        self.redraw_all_labels()
    
    def update_selected_label_info(self):
        """更新选中标签信息"""
        if self.selected_label is not None:
            label = self.labels[self.selected_label]
            info_text = "标签数据:\n"
            for key, value in label['data'].items():
                info_text += f"{key}: {value}\n"
            info_text += f"\n坐标: X:{label['x']:.1f}mm, Y:{label['y']:.1f}mm"
            self.selected_label_info.config(text=info_text)
    
    def redraw_all_labels(self):
        """重绘所有标签"""
        self.canvas_image = Image.new('RGB', 
                                     (int(self.a4_width_mm * self.scale * self.zoom_factor), 
                                      int(self.a4_height_mm * self.scale * self.zoom_factor)), 
                                     'white')
        self.draw = ImageDraw.Draw(self.canvas_image)
        
        self._draw_grid()
        
        for i, label in enumerate(self.labels):
            half_w = label['width'] / 2
            half_h = label['height'] / 2
            x1 = label['x'] - half_w
            y1 = label['y'] - half_h
            x2 = label['x'] + half_w
            y2 = label['y'] + half_h
            
            scale = self.scale * self.zoom_factor
            px1 = x1 * scale
            py1 = y1 * scale
            px2 = x2 * scale
            py2 = y2 * scale
            
            # 绘制条码区域（仅预览用）
            color = (255, 0, 0) if i == self.selected_label else (0, 0, 0)
            self.draw.rectangle([px1, py1, px2, py2], outline=color, width=2)
            
            # 绘制中心点（仅预览用）
            center_x = label['x'] * scale
            center_y = label['y'] * scale
            self.draw.ellipse([
                center_x - 3, 
                center_y - 3,
                center_x + 3, 
                center_y + 3
            ], fill=(0, 255, 0))
            
            # 绘制文字标签
            self._draw_label_text(label, scale)
            
            # 绘制图片
            self._draw_label_image(label, scale)
        
        self.update_canvas()
    
    def _replace_placeholders(self, text, label_data):
        """替换文本中的所有占位符"""
        result = text
        # 替换所有CSV列对应的占位符
        for key, value in label_data['data'].items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def _draw_label_text(self, label, scale):
        """绘制标签文字"""
        if not self.global_text_settings['text']:
            return
            
        try:
            # 替换所有占位符
            display_text = self._replace_placeholders(self.global_text_settings['text'], label)
            
            # 计算文字位置（mm转换为屏幕像素）
            text_x = (label['x'] + self.global_text_settings['x_offset']) * scale
            text_y = (label['y'] + self.global_text_settings['y_offset']) * scale
            
            # 准备字体
            font_size = int(self.global_text_settings['font_size'] * self.zoom_factor)
            # 尝试加载指定字体，失败则使用默认字体
            try:
                font = ImageFont.truetype(f"{self.global_text_settings['font']}.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype(self.global_text_settings['font'], font_size)
                except:
                    font = ImageFont.load_default()
            
            # 创建临时图像用于绘制变换文字
            text_bbox = self.draw.textbbox((0, 0), display_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            temp_img = Image.new('RGBA', (text_width + 10, text_height + 10), (255, 255, 255, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((5, 5), display_text, font=font, fill=self.global_text_settings['color'] + (255,))
            
            # 应用缩放
            if self.global_text_settings['scale_x'] != 1.0 or self.global_text_settings['scale_y'] != 1.0:
                temp_img = temp_img.resize(
                    (int(temp_img.width * self.global_text_settings['scale_x']),
                     int(temp_img.height * self.global_text_settings['scale_y'])),
                    Image.Resampling.LANCZOS
                )
            
            # 应用倾斜
            if self.global_text_settings['skew_x'] != 0 or self.global_text_settings['skew_y'] != 0:
                temp_img = self._skew_image(temp_img, self.global_text_settings['skew_x'], self.global_text_settings['skew_y'])
            
            # 应用旋转
            if self.global_text_settings['rotation'] != 0:
                temp_img = temp_img.rotate(self.global_text_settings['rotation'], expand=True)
            
            # 粘贴到主画布
            self.canvas_image.paste(
                temp_img, 
                (int(text_x - temp_img.width / 2), int(text_y - temp_img.height / 2)),
                temp_img
            )
            
        except Exception as e:
            print(f"绘制文字失败: {e}")
            # 失败时使用简单方式绘制
            try:
                font = ImageFont.load_default()
                self.draw.text(
                    (text_x, text_y), 
                    display_text, 
                    font=font,
                    fill=self.global_text_settings['color']
                )
            except:
                pass
    
    def _draw_label_image(self, label, scale):
        """绘制标签图片"""
        if not self.global_image_settings['path'] or not os.path.exists(self.global_image_settings['path']):
            return
            
        try:
            # 打开图片
            img = Image.open(self.global_image_settings['path']).convert("RGBA")
            
            # 应用缩放
            if self.global_image_settings['scale'] != 1.0:
                new_width = int(img.width * self.global_image_settings['scale'])
                new_height = int(img.height * self.global_image_settings['scale'])
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 应用旋转
            if self.global_image_settings['rotation'] != 0:
                img = img.rotate(self.global_image_settings['rotation'], expand=True)
            
            # 计算图片位置
            img_x = (label['x'] + self.global_image_settings['x_offset']) * scale
            img_y = (label['y'] + self.global_image_settings['y_offset']) * scale
            
            # 粘贴到主画布
            self.canvas_image.paste(
                img, 
                (int(img_x - img.width / 2), int(img_y - img.height / 2)),
                img
            )
            
        except Exception as e:
            print(f"绘制图片失败: {e}")
    
    def _skew_image(self, image, skew_x, skew_y):
        """倾斜图像"""
        width, height = image.size
        skew_x_rad = math.radians(skew_x)
        skew_y_rad = math.radians(skew_y)
        
        # 计算倾斜后的新尺寸
        new_width = int(width + abs(height * math.tan(skew_x_rad)))
        new_height = int(height + abs(width * math.tan(skew_y_rad)))
        
        # 创建新图像
        result = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 0))
        
        # 逐个像素应用倾斜变换
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                if pixel[3] > 0:  # 只处理非透明像素
                    new_x = x + int(y * math.tan(skew_x_rad))
                    new_y = y + int(x * math.tan(skew_y_rad))
                    if 0 <= new_x < new_width and 0 <= new_y < new_height:
                        result.putpixel((new_x, new_y), pixel)
        
        return result
    
    def _draw_grid(self):
        """绘制毫米网格"""
        scale = self.scale * self.zoom_factor
        for x in range(0, int(self.a4_width_mm) + 1, 10):
            self.draw.line(
                [x * scale, 0, x * scale, self.a4_height_mm * scale],
                fill=(230, 230, 230), 
                width=1
            )
            if x % 50 == 0:
                self.draw.text(
                    (x * scale + 2, 2), 
                    f"{x}mm", 
                    fill=(150, 150, 150),
                    font=ImageFont.load_default()
                )
        
        for y in range(0, int(self.a4_height_mm) + 1, 10):
            self.draw.line(
                [0, y * scale, self.a4_width_mm * scale, y * scale],
                fill=(230, 230, 230), 
                width=1
            )
            if y % 50 == 0:
                self.draw.text(
                    (2, y * scale + 2), 
                    f"{y}mm", 
                    fill=(150, 150, 150),
                    font=ImageFont.load_default()
                )
    
    def update_canvas(self):
        """更新画布显示"""
        self.tk_image = ImageTk.PhotoImage(image=self.canvas_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
    
    def zoom(self, amount):
        """缩放画布"""
        new_zoom = self.zoom_factor + amount
        if 0.3 <= new_zoom <= 3.0:
            self.zoom_factor = new_zoom
            self.update_scroll_region()
            self.redraw_all_labels()
            self.status_var.set(f"缩放: {int(self.zoom_factor * 100)}% | 标签数量: {len(self.labels)}")
    
    def reset_zoom(self):
        """重置缩放"""
        self.zoom_factor = 1.0
        self.update_scroll_region()
        self.redraw_all_labels()
        self.status_var.set(f"缩放已重置 | 标签数量: {len(self.labels)}")
    
    def on_mouse_wheel(self, event):
        """处理鼠标滚轮"""
        if event.state & 0x4:  # Ctrl键按下
            if hasattr(event, 'delta'):
                if event.delta > 0:
                    self.zoom(0.1)
                else:
                    self.zoom(-0.1)
            else:
                if event.num == 4:
                    self.zoom(0.1)
                elif event.num == 5:
                    self.zoom(-0.1)
    
    def save_design(self):
        """保存设计方案"""
        if not self.labels:
            messagebox.showwarning("无内容", "没有可保存的标签")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("设计文件", "*.json"), ("所有文件", "*.*")],
            title="保存设计"
        )
        
        if not file_path:
            return
            
        try:
            design_data = {
                'labels': self.labels,
                'csv_columns': self.csv_columns,
                'barcode_width': self.barcode_width,
                'barcode_height': self.barcode_height,
                'text_settings': self.global_text_settings,
                'image_settings': self.global_image_settings
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(design_data, f, ensure_ascii=False, indent=2)
            
            self.status_var.set(f"设计已保存到 {os.path.basename(file_path)}")
            messagebox.showinfo("成功", f"设计已成功保存到:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存文件: {str(e)}")
            self.status_var.set("保存设计失败")
    
    def export_as_image(self):
        """导出为图片（仅包含文字和图片，不包含预览框和点）"""
        if not self.labels:
            messagebox.showwarning("无内容", "没有可导出的标签")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg"), ("所有文件", "*.*")],
            title="导出为图片"
        )
        
        if not file_path:
            return
            
        try:
            # 创建高分辨率空白图像
            high_res_image = Image.new('RGB', (self.a4_width_px, self.a4_height_px), 'white')
            
            for label in self.labels:
                x_px = label['x_px']
                y_px = label['y_px']
                
                # 绘制文字（不绘制预览框和点）
                self._draw_high_res_text(high_res_image, label, x_px, y_px)
                
                # 绘制图片
                self._draw_high_res_image(high_res_image, label, x_px, y_px)
            
            # 保存图片并设置DPI信息
            high_res_image.save(file_path, dpi=(self.dpi, self.dpi))
            self.status_var.set(f"图片已导出到 {os.path.basename(file_path)}")
            messagebox.showinfo("成功", f"图片已成功导出到:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"无法导出图片: {str(e)}")
            self.status_var.set("导出图片失败")
    
    def _draw_high_res_text(self, image, label, x_px, y_px):
        """在高分辨率图像上绘制文字"""
        if not self.global_text_settings['text']:
            return
            
        try:
            # 替换所有占位符
            display_text = self._replace_placeholders(self.global_text_settings['text'], label)
            
            # 计算文字位置（毫米转像素）
            text_x = x_px + self.mm_to_px(self.global_text_settings['x_offset'])
            text_y = y_px + self.mm_to_px(self.global_text_settings['y_offset'])
            
            # 准备字体
            font_size = self.global_text_settings['font_size']
            # 尝试加载指定字体，失败则使用默认字体
            try:
                font = ImageFont.truetype(f"{self.global_text_settings['font']}.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype(self.global_text_settings['font'], font_size)
                except:
                    font = ImageFont.load_default()
            
            # 创建临时图像
            temp_img = Image.new('RGBA', (1000, 1000), (255, 255, 255, 0))  # 使用足够大的临时图像
            temp_draw = ImageDraw.Draw(temp_img)
            text_bbox = temp_draw.textbbox((0, 0), display_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 重新创建合适大小的临时图像
            temp_img = Image.new('RGBA', (text_width + 10, text_height + 10), (255, 255, 255, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((5, 5), display_text, font=font, fill=self.global_text_settings['color'] + (255,))
            
            # 应用变换
            if self.global_text_settings['scale_x'] != 1.0 or self.global_text_settings['scale_y'] != 1.0:
                temp_img = temp_img.resize(
                    (int(temp_img.width * self.global_text_settings['scale_x']),
                     int(temp_img.height * self.global_text_settings['scale_y'])),
                    Image.Resampling.LANCZOS
                )
            
            if self.global_text_settings['skew_x'] != 0 or self.global_text_settings['skew_y'] != 0:
                temp_img = self._skew_image(temp_img, self.global_text_settings['skew_x'], self.global_text_settings['skew_y'])
            
            if self.global_text_settings['rotation'] != 0:
                temp_img = temp_img.rotate(self.global_text_settings['rotation'], expand=True)
            
            # 粘贴到主图像
            image.paste(
                temp_img, 
                (int(text_x - temp_img.width / 2), int(text_y - temp_img.height / 2)),
                temp_img
            )
            
        except Exception as e:
            print(f"绘制高分辨率文字失败: {e}")
    
    def _draw_high_res_image(self, image, label, x_px, y_px):
        """在高分辨率图像上绘制图片"""
        if not self.global_image_settings['path'] or not os.path.exists(self.global_image_settings['path']):
            return
            
        try:
            img = Image.open(self.global_image_settings['path']).convert("RGBA")
            
            if self.global_image_settings['scale'] != 1.0:
                new_width = int(img.width * self.global_image_settings['scale'])
                new_height = int(img.height * self.global_image_settings['scale'])
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            if self.global_image_settings['rotation'] != 0:
                img = img.rotate(self.global_image_settings['rotation'], expand=True)
            
            img_x = x_px + self.mm_to_px(self.global_image_settings['x_offset'])
            img_y = y_px + self.mm_to_px(self.global_image_settings['y_offset'])
            
            image.paste(
                img, 
                (int(img_x - img.width / 2), int(img_y - img.height / 2)),
                img
            )
            
        except Exception as e:
            print(f"绘制高分辨率图片失败: {e}")
    
    def open_text_editor(self):
        """打开文字标签编辑器"""
        if not self.csv_columns:
            messagebox.showinfo("提示", "请先导入CSV文件以获取可用占位符")
            return
            
        from label_editor import TextLabelEditor
        editor_window = tk.Toplevel(self.root)
        editor = TextLabelEditor(editor_window, self)

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeDesigner(root)
    root.mainloop()
    