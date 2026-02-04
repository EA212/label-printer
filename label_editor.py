import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, scrolledtext
import os
import math
from PIL import Image, ImageTk, ImageDraw, ImageFont

class TextLabelEditor:
    def __init__(self, root, main_app):
        self.root = root
        self.main_app = main_app  # 引用主程序实例
        self.root.title("文字标签编辑器")
        self.root.geometry("800x800")
        self.root.transient(main_app.root)  # 设置为主窗口的子窗口
        self.root.grab_set()  # 模态窗口
        
        # 拖动相关变量
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 创建界面
        self.create_widgets()
        
        # 加载当前设置
        self.load_current_settings()
        
        # 更新预览
        self.update_preview()
    
    def create_widgets(self):
        """创建编辑器界面"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板
        control_frame = ttk.Frame(main_frame, width=400)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 右侧预览区
        preview_frame = ttk.LabelFrame(main_frame, text="实时预览", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 预览画布
        self.preview_canvas_frame = ttk.Frame(preview_frame)
        self.preview_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(
            self.preview_canvas_frame, 
            width=300, 
            height=300,
            bg='white',
            highlightthickness=1,
            highlightbackground='gray'
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定预览区拖动事件
        self.preview_canvas.bind("<Button-1>", self.start_drag)
        self.preview_canvas.bind("<B1-Motion>", self.on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.end_drag)
        
        # 文字内容设置
        text_frame = ttk.LabelFrame(control_frame, text="文字内容", padding="10")
        text_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(text_frame, text="文字内容:").pack(anchor=tk.W, pady=5)
        self.text_editor = scrolledtext.ScrolledText(text_frame, width=40, height=4)
        self.text_editor.pack(fill=tk.X, pady=5)
        
        # 可用占位符提示
        ttk.Label(text_frame, text="可用占位符:").pack(anchor=tk.W, pady=5)
        self.placeholders_label = ttk.Label(text_frame, text="", wraplength=300, justify=tk.LEFT)
        self.placeholders_label.pack(anchor=tk.W, pady=5)
        
        # 字体设置
        font_frame = ttk.LabelFrame(control_frame, text="字体设置", padding="10")
        font_frame.pack(fill=tk.X, pady=10)
        
        # 字体选择
        font_row = ttk.Frame(font_frame)
        font_row.pack(fill=tk.X, pady=5)
        ttk.Label(font_row, text="字体:").pack(side=tk.LEFT, padx=5)
        self.font_var = tk.StringVar()
        self.font_families = self.get_available_fonts()
        font_combo = ttk.Combobox(font_row, textvariable=self.font_var, values=self.font_families, width=20)
        font_combo.pack(side=tk.LEFT, padx=5)
        
        # 字体大小
        ttk.Label(font_row, text="大小:").pack(side=tk.LEFT, padx=5)
        self.font_size_var = tk.IntVar()
        ttk.Spinbox(font_row, from_=6, to=72, textvariable=self.font_size_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 字体颜色
        color_row = ttk.Frame(font_frame)
        color_row.pack(fill=tk.X, pady=5)
        ttk.Label(color_row, text="颜色:").pack(side=tk.LEFT, padx=5)
        self.color_var = tk.StringVar()
        self.color_label = ttk.Label(color_row, text="    ", background="#000000")
        self.color_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_row, text="选择", command=self.choose_color).pack(side=tk.LEFT, padx=5)
        
        # 位置设置
        position_frame = ttk.LabelFrame(control_frame, text="位置设置 (相对条码中心，单位：mm)", padding="10")
        position_frame.pack(fill=tk.X, pady=10)
        
        x_offset_row = ttk.Frame(position_frame)
        x_offset_row.pack(fill=tk.X, pady=5)
        ttk.Label(x_offset_row, text="X偏移:").pack(side=tk.LEFT, padx=5)
        self.x_offset_var = tk.DoubleVar()
        x_offset_spin = ttk.Spinbox(x_offset_row, from_=-50, to=50, textvariable=self.x_offset_var, increment=0.5, width=8)
        x_offset_spin.pack(side=tk.LEFT, padx=5)
        x_offset_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        y_offset_row = ttk.Frame(position_frame)
        y_offset_row.pack(fill=tk.X, pady=5)
        ttk.Label(y_offset_row, text="Y偏移:").pack(side=tk.LEFT, padx=5)
        self.y_offset_var = tk.DoubleVar()
        y_offset_spin = ttk.Spinbox(y_offset_row, from_=-50, to=50, textvariable=self.y_offset_var, increment=0.5, width=8)
        y_offset_spin.pack(side=tk.LEFT, padx=5)
        y_offset_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        # 变换设置
        transform_frame = ttk.LabelFrame(control_frame, text="文字变换", padding="10")
        transform_frame.pack(fill=tk.X, pady=10)
        
        rotation_row = ttk.Frame(transform_frame)
        rotation_row.pack(fill=tk.X, pady=5)
        ttk.Label(rotation_row, text="旋转角度:").pack(side=tk.LEFT, padx=5)
        self.rotation_var = tk.IntVar()
        rotation_spin = ttk.Spinbox(rotation_row, from_=0, to=359, textvariable=self.rotation_var, width=8)
        rotation_spin.pack(side=tk.LEFT, padx=5)
        rotation_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        scale_row = ttk.Frame(transform_frame)
        scale_row.pack(fill=tk.X, pady=5)
        ttk.Label(scale_row, text="X缩放:").pack(side=tk.LEFT, padx=5)
        self.scale_x_var = tk.DoubleVar()
        scale_x_spin = ttk.Spinbox(scale_row, from_=0.1, to=5.0, textvariable=self.scale_x_var, increment=0.1, width=8)
        scale_x_spin.pack(side=tk.LEFT, padx=5)
        scale_x_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        ttk.Label(scale_row, text="Y缩放:").pack(side=tk.LEFT, padx=5)
        self.scale_y_var = tk.DoubleVar()
        scale_y_spin = ttk.Spinbox(scale_row, from_=0.1, to=5.0, textvariable=self.scale_y_var, increment=0.1, width=8)
        scale_y_spin.pack(side=tk.LEFT, padx=5)
        scale_y_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        skew_row = ttk.Frame(transform_frame)
        skew_row.pack(fill=tk.X, pady=5)
        ttk.Label(skew_row, text="X倾斜:").pack(side=tk.LEFT, padx=5)
        self.skew_x_var = tk.IntVar()
        skew_x_spin = ttk.Spinbox(skew_row, from_=-45, to=45, textvariable=self.skew_x_var, width=8)
        skew_x_spin.pack(side=tk.LEFT, padx=5)
        skew_x_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        ttk.Label(skew_row, text="Y倾斜:").pack(side=tk.LEFT, padx=5)
        self.skew_y_var = tk.IntVar()
        skew_y_spin = ttk.Spinbox(skew_row, from_=-45, to=45, textvariable=self.skew_y_var, width=8)
        skew_y_spin.pack(side=tk.LEFT, padx=5)
        skew_y_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        # 图片设置
        image_frame = ttk.LabelFrame(control_frame, text="图片设置", padding="10")
        image_frame.pack(fill=tk.X, pady=10)
        
        image_path_row = ttk.Frame(image_frame)
        image_path_row.pack(fill=tk.X, pady=5)
        self.image_path_var = tk.StringVar()
        ttk.Entry(image_path_row, textvariable=self.image_path_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(image_path_row, text="浏览", command=self.browse_image).pack(side=tk.LEFT, padx=5)
        
        image_pos_row = ttk.Frame(image_frame)
        image_pos_row.pack(fill=tk.X, pady=5)
        ttk.Label(image_pos_row, text="图片X偏移:").pack(side=tk.LEFT, padx=5)
        self.image_x_var = tk.DoubleVar()
        image_x_spin = ttk.Spinbox(image_pos_row, from_=-50, to=50, textvariable=self.image_x_var, increment=0.5, width=8)
        image_x_spin.pack(side=tk.LEFT, padx=5)
        image_x_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        ttk.Label(image_pos_row, text="图片Y偏移:").pack(side=tk.LEFT, padx=5)
        self.image_y_var = tk.DoubleVar()
        image_y_spin = ttk.Spinbox(image_pos_row, from_=-50, to=50, textvariable=self.image_y_var, increment=0.5, width=8)
        image_y_spin.pack(side=tk.LEFT, padx=5)
        image_y_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        image_scale_row = ttk.Frame(image_frame)
        image_scale_row.pack(fill=tk.X, pady=5)
        ttk.Label(image_scale_row, text="图片缩放:").pack(side=tk.LEFT, padx=5)
        self.image_scale_var = tk.DoubleVar()
        image_scale_spin = ttk.Spinbox(image_scale_row, from_=0.1, to=2.0, textvariable=self.image_scale_var, increment=0.1, width=8)
        image_scale_spin.pack(side=tk.LEFT, padx=5)
        image_scale_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        ttk.Label(image_scale_row, text="图片旋转:").pack(side=tk.LEFT, padx=5)
        self.image_rotation_var = tk.IntVar()
        image_rotation_spin = ttk.Spinbox(image_scale_row, from_=0, to=359, textvariable=self.image_rotation_var, width=8)
        image_rotation_spin.pack(side=tk.LEFT, padx=5)
        image_rotation_spin.bind("<FocusOut>", lambda e: self.update_preview())
        
        # 按钮区域
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="更新预览", command=self.update_preview).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="应用", command=self.apply_settings).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.root.destroy).pack(side=tk.RIGHT, padx=10)
        
        # 绑定文本变化事件
        self.text_editor.bind("<KeyRelease>", lambda e: self.update_preview())
        self.font_var.trace_add("write", lambda *args: self.update_preview())
        self.font_size_var.trace_add("write", lambda *args: self.update_preview())
    
    def get_available_fonts(self):
        """获取系统可用字体，优先包含中文字体"""
        try:
            import platform
            system = platform.system()
            
            # 常见中文字体列表
            chinese_fonts = ["SimHei", "Microsoft YaHei", "SimSun", "KaiTi", "Heiti TC", "Arial Unicode MS"]
            available_fonts = []
            
            # 检查字体是否可用
            for font in chinese_fonts:
                try:
                    # 尝试加载字体
                    test_font = ImageFont.truetype(f"{font}.ttf", 12)
                    available_fonts.append(font)
                except:
                    try:
                        test_font = ImageFont.truetype(font, 12)
                        available_fonts.append(font)
                    except:
                        continue
            
            # 添加一些常用英文字体
            english_fonts = ["Arial", "Times New Roman", "Courier New", "Verdana"]
            for font in english_fonts:
                if font not in available_fonts:
                    try:
                        test_font = ImageFont.truetype(f"{font}.ttf", 12)
                        available_fonts.append(font)
                    except:
                        continue
            
            if not available_fonts:
                available_fonts = ["Arial"]
                
            return available_fonts
        except:
            return ["SimHei", "Microsoft YaHei", "Arial"]
    
    def load_current_settings(self):
        """加载当前设置"""
        # 显示可用占位符
        if self.main_app.csv_columns:
            placeholders_text = ", ".join([f"{{{col}}}" for col in self.main_app.csv_columns])
            self.placeholders_label.config(text=placeholders_text)
        
        # 加载文字设置
        settings = self.main_app.global_text_settings
        self.text_editor.insert(tk.END, settings['text'])
        self.font_var.set(settings['font'])
        self.font_size_var.set(settings['font_size'])
        
        # 转换颜色格式
        rgb = settings['color']
        hex_color = "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
        self.color_var.set(hex_color)
        self.color_label.configure(background=hex_color)
        
        self.x_offset_var.set(settings['x_offset'])
        self.y_offset_var.set(settings['y_offset'])
        self.rotation_var.set(settings['rotation'])
        self.scale_x_var.set(settings['scale_x'])
        self.scale_y_var.set(settings['scale_y'])
        self.skew_x_var.set(settings['skew_x'])
        self.skew_y_var.set(settings['skew_y'])
        
        # 加载图片设置
        img_settings = self.main_app.global_image_settings
        self.image_path_var.set(img_settings['path'])
        self.image_x_var.set(img_settings['x_offset'])
        self.image_y_var.set(img_settings['y_offset'])
        self.image_scale_var.set(img_settings['scale'])
        self.image_rotation_var.set(img_settings['rotation'])
    
    def choose_color(self):
        """选择字体颜色"""
        color = colorchooser.askcolor(title="选择字体颜色")[0]
        if color:
            rgb = (int(color[0]), int(color[1]), int(color[2]))
            hex_color = "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
            self.color_var.set(hex_color)
            self.color_label.configure(background=hex_color)
            self.update_preview()
    
    def browse_image(self):
        """浏览选择图片"""
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("所有文件", "*.*")],
            title="选择图片"
        )
        if file_path:
            self.image_path_var.set(file_path)
            self.update_preview()
    
    def start_drag(self, event):
        """开始拖动文字"""
        # 检查是否点击了文字区域
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        center_x, center_y = canvas_width // 2, canvas_height // 2
        
        # 简单判断：如果点击位置在中心附近区域，则允许拖动
        if abs(event.x - center_x) < 100 and abs(event.y - center_y) < 100:
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
    
    def on_drag(self, event):
        """拖动文字时更新位置"""
        if self.dragging:
            # 计算拖动距离（转换为毫米）
            dx = (event.x - self.drag_start_x) / self.main_app.scale
            dy = (event.y - self.drag_start_y) / self.main_app.scale
            
            # 更新偏移值
            new_x = self.x_offset_var.get() + dx
            new_y = self.y_offset_var.get() + dy
            
            # 限制范围
            if -50 <= new_x <= 50:
                self.x_offset_var.set(round(new_x, 1))
                self.drag_start_x = event.x
            if -50 <= new_y <= 50:
                self.y_offset_var.set(round(new_y, 1))
                self.drag_start_y = event.y
            
            # 更新预览
            self.update_preview()
    
    def end_drag(self, event):
        """结束拖动"""
        self.dragging = False
    
    def update_preview(self):
        """更新预览窗口"""
        # 清除预览画布
        self.preview_canvas.delete("all")
        
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # 绘制条码区域（预览用）
        barcode_width = self.main_app.barcode_width * self.main_app.scale
        barcode_height = self.main_app.barcode_height * self.main_app.scale
        center_x, center_y = canvas_width // 2, canvas_height // 2
        
        # 绘制条码边框
        self.preview_canvas.create_rectangle(
            center_x - barcode_width/2,
            center_y - barcode_height/2,
            center_x + barcode_width/2,
            center_y + barcode_height/2,
            outline='gray',
            dash=(2, 2)
        )
        
        # 绘制中心点
        self.preview_canvas.create_oval(
            center_x - 3, center_y - 3,
            center_x + 3, center_y + 3,
            fill='red'
        )
        
        # 创建预览文字
        try:
            # 获取文字内容并替换示例占位符
            text_content = self.text_editor.get("1.0", tk.END).strip()
            
            # 生成示例数据用于预览
            sample_data = {}
            if self.main_app.csv_columns:
                for col in self.main_app.csv_columns:
                    sample_data[col] = f"{{{col}}}"
                    if col.lower() == 'id':
                        sample_data[col] = "123"
                    elif col.lower() == 'password':
                        sample_data[col] = "******"
            
            # 替换占位符
            display_text = text_content
            for key, value in sample_data.items():
                display_text = display_text.replace(f"{{{key}}}", value)
            
            # 计算文字位置
            text_x = center_x + self.x_offset_var.get() * self.main_app.scale
            text_y = center_y + self.y_offset_var.get() * self.main_app.scale
            
            # 创建临时图像绘制文字
            temp_img = Image.new('RGBA', (300, 100), (255, 255, 255, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # 加载字体
            try:
                font = ImageFont.truetype(f"{self.font_var.get()}.ttf", self.font_size_var.get())
            except:
                try:
                    font = ImageFont.truetype(self.font_var.get(), self.font_size_var.get())
                except:
                    font = ImageFont.load_default()
            
            # 绘制文字
            temp_draw.text((0, 0), display_text, font=font, fill=self.color_var.get())
            
            # 应用变换
            if self.scale_x_var.get() != 1.0 or self.scale_y_var.get() != 1.0:
                temp_img = temp_img.resize(
                    (int(temp_img.width * self.scale_x_var.get()),
                     int(temp_img.height * self.scale_y_var.get())),
                    Image.Resampling.LANCZOS
                )
            
            if self.skew_x_var.get() != 0 or self.skew_y_var.get() != 0:
                temp_img = self._skew_image(temp_img, self.skew_x_var.get(), self.skew_y_var.get())
            
            if self.rotation_var.get() != 0:
                temp_img = temp_img.rotate(self.rotation_var.get(), expand=True)
            
            # 转换为Tkinter可用的图像
            tk_img = ImageTk.PhotoImage(temp_img)
            
            # 在画布上显示
            self.preview_canvas.create_image(
                text_x, text_y, 
                image=tk_img,
                anchor=tk.CENTER
            )
            
            # 保存引用防止被垃圾回收
            self.preview_canvas.temp_img = tk_img
            
        except Exception as e:
            self.preview_canvas.create_text(
                canvas_width//2, canvas_height//2,
                text=f"预览错误: {str(e)}",
                fill="red"
            )
        
        # 绘制图片（如果有）
        self._draw_preview_image(center_x, center_y)
    
    def _draw_preview_image(self, center_x, center_y):
        """在预览窗口绘制图片"""
        image_path = self.image_path_var.get()
        if not image_path or not os.path.exists(image_path):
            return
            
        try:
            # 打开图片
            img = Image.open(image_path).convert("RGBA")
            
            # 应用缩放
            if self.image_scale_var.get() != 1.0:
                new_width = int(img.width * self.image_scale_var.get())
                new_height = int(img.height * self.image_scale_var.get())
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 应用旋转
            if self.image_rotation_var.get() != 0:
                img = img.rotate(self.image_rotation_var.get(), expand=True)
            
            # 计算图片位置
            img_x = center_x + self.image_x_var.get() * self.main_app.scale
            img_y = center_y + self.image_y_var.get() * self.main_app.scale
            
            # 转换为Tkinter可用的图像
            tk_img = ImageTk.PhotoImage(img)
            
            # 在画布上显示
            self.preview_canvas.create_image(
                img_x, img_y, 
                image=tk_img,
                anchor=tk.CENTER
            )
            
            # 保存引用防止被垃圾回收
            self.preview_canvas.image = tk_img
            
        except Exception as e:
            self.preview_canvas.create_text(
                center_x, center_y + 50,
                text=f"图片错误: {str(e)}",
                fill="red"
            )
    
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
    
    def apply_settings(self):
        """应用设置到主程序"""
        try:
            # 保存文字设置
            hex_color = self.color_var.get().lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            self.main_app.global_text_settings = {
                'text': self.text_editor.get("1.0", tk.END).strip(),
                'font': self.font_var.get(),
                'font_size': self.font_size_var.get(),
                'color': rgb,
                'x_offset': self.x_offset_var.get(),
                'y_offset': self.y_offset_var.get(),
                'rotation': self.rotation
                'rotation': self.rotation_var.get(),
                'scale_x': self.scale_x_var.get(),
                'scale_y': self.scale_y_var.get(),
                'skew_x': self.skew_x_var.get(),
                'skew_y': self.skew_y_var.get()
            }
            
            # 保存图片设置
            self.main_app.global_image_settings = {
                'path': self.image_path_var.get(),
                'x_offset': self.image_x_var.get(),
                'y_offset': self.image_y_var.get(),
                'scale': self.image_scale_var.get(),
                'rotation': self.image_rotation_var.get()
            }
            
            # 刷新主窗口
            self.main_app.redraw_all_labels()
            messagebox.showinfo("成功", "设置已应用")
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"应用设置失败: {str(e)}")
    