import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import os
import threading
from queue import Queue
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
import platform

# 常量定义 - 单位：mm
A4_WIDTH = 210  # A4宽度
A4_HEIGHT = 297  # A4高度

# 图片参数（300dpi保证打印清晰度）
DPI = 300
MM_TO_PIXEL = DPI / 25.4  # 毫米到像素的转换因子（1mm ≈ 11.811像素）

# A4尺寸（像素）
A4_WIDTH_PX = int(A4_WIDTH * MM_TO_PIXEL)
A4_HEIGHT_PX = int(A4_HEIGHT * MM_TO_PIXEL)

class ImageBasedStickerGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("基于图像识别的标签生成器")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 数据存储
        self.raw_data = []  # 原始有效数据
        self.paged_data = []  # 按页划分的数据
        self.current_page = 0
        self.total_pages = 0
        
        # 图像相关
        self.sticker_image_path = None
        self.sticker_image = None
        self.detected_contours = []  # 检测到的标签轮廓
        self.processed_image = None  # 处理后的图像
        
        # 检测参数
        self.color_tolerance = tk.IntVar(value=30)
        self.min_area = tk.IntVar(value=500)
        self.max_area = tk.IntVar(value=50000)
        
        # UI样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        
        # 状态变量
        self.file_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")
        self.generating = False
        
        # 字体相关
        self.fonts = {}
        self.load_fonts()
        
        # 创建UI
        self.create_widgets()
        
        # 线程队列
        self.queue = Queue()
        self.max_threads = 2
    
    def load_fonts(self):
        """加载中文字体，确保绘图时可用"""
        system = platform.system()
        try:
            if system == "Windows":
                self.fonts["simhei"] = "C:/Windows/Fonts/simhei.ttf"
                self.fonts["msyh"] = "C:/Windows/Fonts/msyh.ttc"
            elif system == "Darwin":  # macOS
                self.fonts["simhei"] = "/Library/Fonts/SimHei.ttf"
                self.fonts["msyh"] = "/Library/Fonts/Microsoft YaHei.ttc"
            else:  # Linux
                self.fonts["simhei"] = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            
            # 测试字体是否可用
            test_font = ImageFont.truetype(self.fonts["simhei"], 12)
            self.default_font = self.fonts["simhei"]
        except Exception as e:
            self.default_font = None
            self.status_var.set(f"警告：未找到中文字体，可能导致中文显示异常 ({str(e)})")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(top_frame, text="数据文件 (CSV/Excel)", padding="5")
        file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="浏览", command=self.browse_data_file).pack(side=tk.LEFT, padx=5)
        
        # 图像选择区域
        image_frame = ttk.LabelFrame(top_frame, text="标签贴纸图像", padding="5")
        image_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.image_path_var = tk.StringVar()
        ttk.Entry(image_frame, textvariable=self.image_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(image_frame, text="选择图像", command=self.browse_image_file).pack(side=tk.LEFT, padx=5)
        
        # 操作按钮
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(btn_frame, text="检测标签", command=self.detect_stickers).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="生成图片", command=self.start_generation).pack(side=tk.LEFT, padx=5)
        
        # 参数调节区域
        param_frame = ttk.LabelFrame(main_frame, text="检测参数", padding="10")
        param_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(param_frame, text="颜色容差:").pack(side=tk.LEFT, padx=5)
        ttk.Scale(param_frame, from_=10, to=100, variable=self.color_tolerance, command=lambda v: self.update_param_label("color_label", v)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.color_label = ttk.Label(param_frame, text=str(self.color_tolerance.get()))
        self.color_label.pack(side=tk.LEFT, padx=5, width=30)
        
        ttk.Label(param_frame, text="最小面积:").pack(side=tk.LEFT, padx=5)
        ttk.Scale(param_frame, from_=100, to=10000, variable=self.min_area, command=lambda v: self.update_param_label("min_area_label", v)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.min_area_label = ttk.Label(param_frame, text=str(self.min_area.get()))
        self.min_area_label.pack(side=tk.LEFT, padx=5, width=30)
        
        ttk.Label(param_frame, text="最大面积:").pack(side=tk.LEFT, padx=5)
        ttk.Scale(param_frame, from_=10000, to=100000, variable=self.max_area, command=lambda v: self.update_param_label("max_area_label", v)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.max_area_label = ttk.Label(param_frame, text=str(self.max_area.get()))
        self.max_area_label.pack(side=tk.LEFT, padx=5, width=30)
        
        # 分页控制
        page_frame = ttk.Frame(main_frame)
        page_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(page_frame, text="上一页", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        self.page_label = ttk.Label(page_frame, text="第 0/0 页")
        self.page_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(page_frame, text="下一页", command=self.next_page).pack(side=tk.LEFT, padx=5)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="标签预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建左右分栏的预览区域
        preview_paned = ttk.PanedWindow(preview_frame, orient=tk.HORIZONTAL)
        preview_paned.pack(fill=tk.BOTH, expand=True)
        
        # 原始图像预览
        self.raw_preview_frame = ttk.LabelFrame(preview_paned, text="原始图像", padding="5")
        preview_paned.add(self.raw_preview_frame, weight=1)
        
        self.raw_canvas = tk.Canvas(self.raw_preview_frame, bg="#f5f5f5", borderwidth=1, relief=tk.SUNKEN)
        self.raw_canvas.pack(fill=tk.BOTH, expand=True)
        self.raw_canvas.bind("<Configure>", self.on_raw_canvas_resize)
        
        # 处理后图像预览
        self.processed_preview_frame = ttk.LabelFrame(preview_paned, text="检测结果", padding="5")
        preview_paned.add(self.processed_preview_frame, weight=1)
        
        self.processed_canvas = tk.Canvas(self.processed_preview_frame, bg="#f5f5f5", borderwidth=1, relief=tk.SUNKEN)
        self.processed_canvas.pack(fill=tk.BOTH, expand=True)
        self.processed_canvas.bind("<Configure>", self.on_processed_canvas_resize)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W)
    
    def update_param_label(self, label_name, value):
        """更新参数显示标签"""
        if label_name == "color_label":
            self.color_tolerance.set(int(float(value)))
            self.color_label.config(text=str(self.color_tolerance.get()))
        elif label_name == "min_area_label":
            self.min_area.set(int(float(value)))
            self.min_area_label.config(text=str(self.min_area.get()))
        elif label_name == "max_area_label":
            self.max_area.set(int(float(value)))
            self.max_area_label.config(text=str(self.max_area.get()))
    
    def browse_data_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("数据文件", "*.xlsx;*.xls;*.csv")],
            title="选择包含device_code和password的文件"
        )
        if file_path:
            self.file_path.set(file_path)
            self.load_data(file_path)
    
    def browse_image_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图像文件", "*.png;*.jpg;*.jpeg;*.bmp")],
            title="选择标签贴纸图片"
        )
        if file_path:
            self.image_path_var.set(file_path)
            self.sticker_image_path = file_path
            self.load_and_display_image()
    
    def load_and_display_image(self):
        """加载并显示图像"""
        try:
            # 使用OpenCV加载图像
            self.sticker_image = cv2.imread(self.sticker_image_path)
            if self.sticker_image is None:
                raise Exception("无法加载图像文件")
            
            # 转换为RGB格式以便在Tkinter中显示
            rgb_image = cv2.cvtColor(self.sticker_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # 在原始图像画布上显示
            self.raw_image = pil_image.copy()
            self.update_raw_preview()
            
            self.status_var.set(f"已加载图像: {os.path.basename(self.sticker_image_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载图像失败: {str(e)}")
            self.status_var.set("加载图像失败")
    
    def update_raw_preview(self):
        """更新原始图像预览"""
        if not hasattr(self, 'raw_image'):
            return
            
        canvas_w = self.raw_canvas.winfo_width()
        canvas_h = self.raw_canvas.winfo_height()
        
        if canvas_w < 50 or canvas_h < 50:
            return
        
        # 计算缩放比例
        img_w, img_h = self.raw_image.size
        scale = min(canvas_w / img_w, canvas_h / img_h) * 0.95
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # 缩放图像
        resized_img = self.raw_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.raw_tk_image = ImageTk.PhotoImage(resized_img)
        
        # 清除并显示新图像
        self.raw_canvas.delete("all")
        x = (canvas_w - new_w) // 2
        y = (canvas_h - new_h) // 2
        self.raw_canvas.create_image(x, y, image=self.raw_tk_image, anchor=tk.NW)
    
    def update_processed_preview(self):
        """更新处理后的图像预览"""
        if self.processed_image is None:
            return
            
        canvas_w = self.processed_canvas.winfo_width()
        canvas_h = self.processed_canvas.winfo_height()
        
        if canvas_w < 50 or canvas_h < 50:
            return
        
        # 计算缩放比例
        img_w, img_h = self.processed_image.size
        scale = min(canvas_w / img_w, canvas_h / img_h) * 0.95
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # 缩放图像
        resized_img = self.processed_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.processed_tk_image = ImageTk.PhotoImage(resized_img)
        
        # 清除并显示新图像
        self.processed_canvas.delete("all")
        x = (canvas_w - new_w) // 2
        y = (canvas_h - new_h) // 2
        self.processed_canvas.create_image(x, y, image=self.processed_tk_image, anchor=tk.NW)
        
        # 显示检测到的标签数量
        if self.detected_contours:
            self.processed_canvas.create_text(
                canvas_w // 2, 15,
                text=f"检测到 {len(self.detected_contours)} 个标签",
                font=("SimHei", 10), fill="red"
            )
    
    def on_raw_canvas_resize(self, event):
        self.update_raw_preview()
    
    def on_processed_canvas_resize(self, event):
        self.update_processed_preview()
    
    def detect_stickers(self):
        """检测图像中的标签轮廓"""
        if self.sticker_image is None:
            messagebox.showwarning("警告", "请先选择标签贴纸图像")
            return
            
        try:
            self.status_var.set("正在检测标签...")
            
            # 创建原始图像的副本用于绘制结果
            processed_img = self.sticker_image.copy()
            
            # 转换为HSV颜色空间，便于颜色检测
            hsv = cv2.cvtColor(processed_img, cv2.COLOR_BGR2HSV)
            
            # 定义白色的HSV范围（标签颜色）
            lower_white = np.array([0, 0, 255 - self.color_tolerance.get()])
            upper_white = np.array([180, self.color_tolerance.get(), 255])
            
            # 创建掩码
            mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # 形态学操作，去除噪声
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 筛选轮廓（基于面积）
            self.detected_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if self.min_area.get() < area < self.max_area.get():
                    # 获取最小外接矩形
                    x, y, w, h = cv2.boundingRect(contour)
                    self.detected_contours.append((x, y, w, h))
                    
                    # 在图像上绘制边界框
                    cv2.rectangle(processed_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # 标记序号
                    cv2.putText(processed_img, f"{len(self.detected_contours)}", 
                               (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # 转换为RGB格式以便在Tkinter中显示
            rgb_processed = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            self.processed_image = Image.fromarray(rgb_processed)
            
            # 更新预览
            self.update_processed_preview()
            
            # 处理数据分页
            if self.raw_data:
                self.total_pages = max(1, math.ceil(len(self.raw_data) / len(self.detected_contours)))
                self.paged_data = [self.raw_data[i*len(self.detected_contours):(i+1)*len(self.detected_contours)] 
                                  for i in range(self.total_pages)]
                self.current_page = 0
                self.update_page_label()
            
            self.status_var.set(f"标签检测完成，共检测到 {len(self.detected_contours)} 个标签")
            
        except Exception as e:
            messagebox.showerror("错误", f"标签检测失败: {str(e)}")
            self.status_var.set("标签检测失败")
    
    def load_data(self, file_path):
        """加载并过滤数据"""
        try:
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:  # CSV
                encodings = ['utf-8', 'gbk', 'gb2312']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("无法解析CSV编码，请尝试UTF-8格式")
            
            # 验证必要列
            required = ['device_code', 'password']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"文件缺少必要列：{', '.join(missing)}")
            
            # 过滤空行
            self.raw_data = []
            for _, row in df.iterrows():
                dev = str(row['device_code']).strip() if pd.notna(row['device_code']) else ""
                pwd = str(row['password']).strip() if pd.notna(row['password']) else ""
                if dev or pwd:
                    self.raw_data.append((dev, pwd))
            
            # 分页处理（如果已有检测到的标签）
            if self.detected_contours:
                items_per_page = len(self.detected_contours)
                self.total_pages = max(1, math.ceil(len(self.raw_data) / items_per_page))
                self.paged_data = [self.raw_data[i*items_per_page:(i+1)*items_per_page] 
                                  for i in range(self.total_pages)]
            else:
                self.total_pages = 0
                self.paged_data = []
            
            self.current_page = 0
            self.update_page_label()
            self.status_var.set(f"加载完成：{len(self.raw_data)}条数据")
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("加载失败")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_label()
    
    def update_page_label(self):
        self.page_label.config(text=f"第 {self.current_page + 1}/{self.total_pages} 页")
    
    def start_generation(self):
        if not self.paged_data or not self.detected_contours:
            messagebox.showwarning("警告", "请先加载数据并检测标签")
            return
            
        output_dir = filedialog.askdirectory(title="选择保存目录")
        if not output_dir:
            return
            
        self.generating = True
        self.progress_var.set(0)
        self.status_var.set(f"开始生成 {self.total_pages} 张图片...")
        
        threading.Thread(target=self.generate_all_pages, args=(output_dir,), daemon=True).start()
    
    def generate_all_pages(self, output_dir):
        """生成所有页图片"""
        for page_num in range(self.total_pages):
            if not self.generating:
                break
            self.queue.put((page_num + 1, self.paged_data[page_num], output_dir))
        
        # 启动工作线程
        threads = [threading.Thread(target=self.image_worker) 
                  for _ in range(min(self.max_threads, self.total_pages))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.generating = False
        self.progress_var.set(100)
        self.status_var.set(f"生成完成：{self.total_pages}张图片保存至 {output_dir}")
        messagebox.showinfo("完成", f"已生成 {self.total_pages} 张图片")
    
    def get_font(self, size):
        """获取指定大小的字体"""
        try:
            if self.default_font:
                return ImageFont.truetype(self.default_font, size)
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def fit_text_to_box(self, draw, text, box_width, box_height, font_path, min_size=5, max_size=30):
        """调整文字大小以适应方框"""
        # 尝试调整字体大小
        for size in range(max_size, min_size - 1, -1):
            font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if text_width <= box_width and text_height <= box_height:
                return (font, None)  # 无需变形
        
        # 如果最大字体仍超出宽度，创建文字图像并轻微变形
        font = ImageFont.truetype(font_path, max_size) if font_path else ImageFont.load_default()
        text_img = Image.new('L', (int(box_width * 1.2), int(box_height * 1.2)), 0)
        text_draw = ImageDraw.Draw(text_img)
        text_draw.text((0, 0), text, font=font, fill=255)
        
        # 计算缩放比例
        bbox = text_img.getbbox()
        if not bbox:
            return (font, None)
            
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        scale_x = min(box_width / text_width, 1.2)
        scale_y = min(box_height / text_height, 1.2)
        
        # 缩放文字图像
        scaled_img = text_img.resize(
            (int(text_width * scale_x), int(text_height * scale_y)),
            Image.Resampling.LANCZOS
        )
        
        return (None, scaled_img)
    
    def image_worker(self):
        """图片生成工作线程"""
        while not self.queue.empty() and self.generating:
            try:
                page_num, data, output_dir = self.queue.get(timeout=1)
                img_path = os.path.join(output_dir, f"page_{page_num}.png")
                
                # 创建与原始图像大小相同的图像
                img_height, img_width = self.sticker_image.shape[:2]
                img = Image.new('RGB', (img_width, img_height), color='white')
                draw = ImageDraw.Draw(img)
                
                # 绘制每个标签内容
                for idx, (device_code, password) in enumerate(data):
                    if idx >= len(self.detected_contours):
                        break  # 防止数据超出检测到的标签数量
                        
                    x, y, w, h = self.detected_contours[idx]
                    
                    # 计算上下区域高度（各占一半）
                    upper_height = h / 2
                    lower_height = h / 2
                    
                    # 绘制设备码（顶部）
                    if device_code:
                        text = f"设备码：{device_code}"
                        # 适配文字到上半区域
                        font, text_img = self.fit_text_to_box(
                            draw, text, 
                            w - 10, upper_height - 10,  # 留一点边距
                            self.default_font
                        )
                        
                        if text_img:
                            # 绘制变形文字
                            img.paste(
                                ImageOps.colorize(text_img, (255,255,255), (0,0,0)),
                                (x + 5, y + 5),
                                text_img
                            )
                        else:
                            # 绘制正常文字
                            draw.text(
                                (x + 5, y + 5),
                                text,
                                font=font,
                                fill='black'
                            )
                    
                    # 绘制密码（底部）
                    if password:
                        text = f"密钥：{password}"
                        # 适配文字到下半区域
                        font, text_img = self.fit_text_to_box(
                            draw, text, 
                            w - 10, lower_height - 10,  # 留一点边距
                            self.default_font
                        )
                        
                        if text_img:
                            # 绘制变形文字
                            img.paste(
                                ImageOps.colorize(text_img, (255,255,255), (0,0,0)),
                                (x + 5, y + int(upper_height) + 5),
                                text_img
                            )
                        else:
                            # 绘制正常文字
                            draw.text(
                                (x + 5, y + int(upper_height) + 5),
                                text,
                                font=font,
                                fill='black'
                            )
                
                # 保存图片
                img.save(img_path, dpi=(DPI, DPI))
                
                # 更新进度
                progress = (page_num / self.total_pages) * 100
                self.progress_var.set(progress)
                self.status_var.set(f"已生成：第 {page_num} 页")
                
            except Exception as e:
                self.status_var.set(f"生成失败：{str(e)}")
                print(f"错误：{e}")
            finally:
                self.queue.task_done()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBasedStickerGeneratorApp(root)
    root.mainloop()
    