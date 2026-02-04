import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import os
import threading
from queue import Queue
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
import platform

# 常量定义 - 单位：mm
A4_WIDTH = 210  # A4宽度
A4_HEIGHT = 297  # A4高度

# 贴纸区域总尺寸（用户指定）
STICKER_SHEET_WIDTH = 198  # 横向总宽度19.8cm
STICKER_SHEET_HEIGHT = 165  # 竖向总高度16.5cm

# 贴纸网格参数
COLUMNS = 6  # 横向6列
ROWS = 14    # 竖向14行

# 贴纸区域内部边缘和间隔（用户指定）
HORIZONTAL_EDGE = 2  # 横向两边边缘（左/右各2mm）
VERTICAL_EDGE = 1    # 竖向两边边缘（上/下各1mm）
COLUMN_GAP = 1       # 列之间间隔1mm
ROW_GAP = 1          # 行之间间隔1mm

# 精确计算单张贴纸尺寸
STICKER_WIDTH = (STICKER_SHEET_WIDTH - HORIZONTAL_EDGE*2 - COLUMN_GAP*(COLUMNS-1)) / COLUMNS  # 31.5mm
STICKER_HEIGHT = (STICKER_SHEET_HEIGHT - VERTICAL_EDGE*2 - ROW_GAP*(ROWS-1)) / ROWS  # ~10.714mm

# 贴纸区域在A4上的位置（整体左移2mm，下移0.5mm）
SHEET_ORIGIN_X = -2   # 左移2mm
SHEET_ORIGIN_Y = 0.5  # 下移0.5mm（按最新要求调整）

# 图片参数（300dpi保证打印清晰度）
DPI = 300
MM_TO_PIXEL = DPI / 25.4  # 毫米到像素的转换因子（1mm ≈ 11.811像素）

# A4尺寸（像素）
A4_WIDTH_PX = int(A4_WIDTH * MM_TO_PIXEL)
A4_HEIGHT_PX = int(A4_HEIGHT * MM_TO_PIXEL)

class StickerGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("精确贴纸生成器")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        
        # 数据存储
        self.raw_data = []  # 原始有效数据
        self.paged_data = []  # 按页划分的数据
        self.current_page = 0
        self.total_pages = 0
        
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
        
        # 绑定事件
        self.preview_canvas.bind("<Configure>", self.on_canvas_resize)
    
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
        
        # 文件选择
        file_frame = ttk.LabelFrame(top_frame, text="数据文件 (CSV/Excel)", padding="5")
        file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="浏览", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # 操作按钮
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(btn_frame, text="生成图片", command=self.start_generation).pack(side=tk.LEFT, padx=5)
        
        # 分页控制
        page_frame = ttk.Frame(main_frame)
        page_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(page_frame, text="上一页", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        self.page_label = ttk.Label(page_frame, text="第 0/0 页")
        self.page_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(page_frame, text="下一页", command=self.next_page).pack(side=tk.LEFT, padx=5)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(
            main_frame, 
            text=f"布局预览 - 单张尺寸:{STICKER_WIDTH:.2f}x{STICKER_HEIGHT:.2f}mm（文字贴紧边框）", 
            padding="10"
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="#f5f5f5", borderwidth=1, relief=tk.SUNKEN)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W)
        
        self.update_preview()
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("数据文件", "*.xlsx;*.xls;*.csv")],
            title="选择包含device_code和password的文件"
        )
        if file_path:
            self.file_path.set(file_path)
            self.load_data(file_path)
    
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
            
            # 分页处理
            items_per_page = ROWS * COLUMNS
            self.total_pages = max(1, math.ceil(len(self.raw_data) / items_per_page))
            self.paged_data = [self.raw_data[i*items_per_page:(i+1)*items_per_page] 
                              for i in range(self.total_pages)]
            
            self.current_page = 0
            self.update_page_label()
            self.update_preview()
            self.status_var.set(f"加载完成：{len(self.raw_data)}条数据，共{self.total_pages}页")
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("加载失败")
    
    def get_sticker_position(self, index):
        """计算贴纸绝对坐标（mm）"""
        row = index // COLUMNS
        col = index % COLUMNS
        
        x = round(SHEET_ORIGIN_X + HORIZONTAL_EDGE + col * (STICKER_WIDTH + COLUMN_GAP), 4)
        y = round(SHEET_ORIGIN_Y + VERTICAL_EDGE + row * (STICKER_HEIGHT + ROW_GAP), 4)
        
        return (x, y, row, col)
    
    def update_preview(self):
        """绘制预览，文字贴紧边框"""
        self.preview_canvas.delete("all")
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()
        
        if canvas_w < 50 or canvas_h < 50:
            return
        
        # 缩放计算
        scale = min(canvas_w / A4_WIDTH, canvas_h / A4_HEIGHT) * 0.95
        a4_display_w = A4_WIDTH * scale
        a4_display_h = A4_HEIGHT * scale
        offset_x = (canvas_w - a4_display_w) / 2
        offset_y = (canvas_h - a4_display_h) / 2
        
        # 绘制A4背景
        self.preview_canvas.create_rectangle(
            offset_x, offset_y,
            offset_x + a4_display_w,
            offset_y + a4_display_h,
            fill="white", outline="gray", width=2
        )
        
        # 绘制A4标签
        self.preview_canvas.create_text(
            offset_x + a4_display_w/2, offset_y + 15,
            text=f"A4纸 ({A4_WIDTH}mm × {A4_HEIGHT}mm) - 整体下移0.5mm",
            font=("SimHei", 10), fill="gray"
        )
        
        # 绘制贴纸区域
        sheet_display_x = offset_x + SHEET_ORIGIN_X * scale
        sheet_display_y = offset_y + SHEET_ORIGIN_Y * scale
        sheet_display_w = STICKER_SHEET_WIDTH * scale
        sheet_display_h = STICKER_SHEET_HEIGHT * scale
        
        self.preview_canvas.create_rectangle(
            sheet_display_x, sheet_display_y,
            sheet_display_x + sheet_display_w,
            sheet_display_y + sheet_display_h,
            fill="#e6f7ff", outline="blue", width=2
        )
        
        # 绘制当前页数据
        if self.total_pages > 0 and self.current_page < len(self.paged_data):
            page_data = self.paged_data[self.current_page]
            for idx, (device_code, password) in enumerate(page_data):
                x, y, row, col = self.get_sticker_position(idx)
                
                # 转换为预览坐标
                preview_x = offset_x + x * scale
                preview_y = offset_y + y * scale
                preview_w = STICKER_WIDTH * scale
                preview_h = STICKER_HEIGHT * scale
                
                # 绘制贴纸边框
                self.preview_canvas.create_rectangle(
                    preview_x, preview_y,
                    preview_x + preview_w,
                    preview_y + preview_h,
                    fill="white", outline="black", width=1
                )
                
                # 绘制坐标标签
                self.preview_canvas.create_text(
                    preview_x + 5, preview_y + 10,
                    text=f"({row},{col})",
                    font=("SimHei", 6), fill="#999"
                )
                
                # 绘制文字（贴紧边框，最大化填充）
                if device_code or password:
                    # 计算字体大小（尽可能大）
                    font_size = min(int(preview_w / 9), int(preview_h / 4))
                    font_size = max(5, font_size)
                    
                    # 设备码（顶部贴紧上边框）
                    self.preview_canvas.create_text(
                        preview_x, preview_y,  # 左上角对齐，贴紧边框
                        text=f"设备码：{device_code}",
                        anchor=tk.NW, font=("SimHei", font_size)
                    )
                    
                    # 密码（底部贴紧下边框，与设备码紧挨着）
                    self.preview_canvas.create_text(
                        preview_x, preview_y + preview_h - font_size - 2,  # 贴紧下边框
                        text=f"密钥：{password}",
                        anchor=tk.NW, font=("SimHei", font_size)
                    )
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
            self.update_preview()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_label()
            self.update_preview()
    
    def update_page_label(self):
        self.page_label.config(text=f"第 {self.current_page + 1}/{self.total_pages} 页")
    
    def on_canvas_resize(self, event):
        self.update_preview()
    
    def start_generation(self):
        if not self.paged_data:
            messagebox.showwarning("警告", "请先加载数据")
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
        """
        调整文字大小并在必要时轻微变形以完全填充方框
        返回：(字体, 调整后的文字图像)
        """
        # 先尝试调整字体大小
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
        
        # 计算缩放比例（限制在1.2倍以内，避免过度变形）
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
                
                # 创建A4图片
                img = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), color='white')
                draw = ImageDraw.Draw(img)
                
                # 绘制每个贴纸
                for idx, (device_code, password) in enumerate(data):
                    x, y, _, _ = self.get_sticker_position(idx)
                    
                    # 转换为像素坐标
                    x_px = x * MM_TO_PIXEL
                    y_px = y * MM_TO_PIXEL
                    width_px = STICKER_WIDTH * MM_TO_PIXEL
                    height_px = STICKER_HEIGHT * MM_TO_PIXEL
                    
                    # 绘制贴纸边框
                    draw.rectangle(
                        [x_px, y_px, x_px + width_px, y_px + height_px],
                        outline='black', width=1
                    )
                    
                    # 计算上下区域高度（各占一半）
                    upper_height = height_px / 2
                    lower_height = height_px / 2
                    
                    # 绘制设备码（顶部贴紧上边框）
                    if device_code:
                        text = f"设备码：{device_code}"
                        # 适配文字到上半区域
                        font, text_img = self.fit_text_to_box(
                            draw, text, 
                            width_px, upper_height,
                            self.default_font
                        )
                        
                        if text_img:
                            # 变形文字的绘制位置（贴紧上边缘）
                            img.paste(
                                ImageOps.colorize(text_img, (255,255,255), (0,0,0)),
                                (int(x_px), int(y_px)),
                                text_img
                            )
                        else:
                            # 正常文字的绘制位置（贴紧上边缘）
                            draw.text(
                                (x_px, y_px),  # 左上角对齐，无任何内边距
                                text,
                                font=font,
                                fill='black'
                            )
                    
                    # 绘制密码（底部贴紧下边框）
                    if password:
                        text = f"密钥：{password}"
                        # 适配文字到下半区域
                        font, text_img = self.fit_text_to_box(
                            draw, text, 
                            width_px, lower_height,
                            self.default_font
                        )
                        
                        if text_img:
                            # 变形文字的绘制位置（贴紧下边缘）
                            img.paste(
                                ImageOps.colorize(text_img, (255,255,255), (0,0,0)),
                                (int(x_px), int(y_px + upper_height)),
                                text_img
                            )
                        else:
                            # 正常文字的绘制位置（贴紧下边缘）
                            draw.text(
                                (x_px, y_px + upper_height),  # 紧接上半区域，无间隙
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
    app = StickerGeneratorApp(root)
    root.mainloop()
    
