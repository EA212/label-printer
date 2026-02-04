import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
import math

class CoordinateLabelGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("坐标标签生成器")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # 设置中文字体支持
        self.system_fonts = ["simhei.ttf", "microsoftyahei.ttf", "simsun.ttc", "simkai.ttf"]
        self.selected_font = None
        
        # 数据存储
        self.coordinates_df = None
        self.devices_df = None
        self.preview_image = None
        
        # 创建UI
        self._create_widgets()
        
    def _create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制选项", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 坐标文件选择
        ttk.Label(control_frame, text="坐标CSV文件:").pack(anchor=tk.W, pady=(0, 5))
        self.coord_file_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.coord_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="浏览...", command=self._browse_coord_file).pack(fill=tk.X, pady=(0, 10))
        
        # 设备文件选择
        ttk.Label(control_frame, text="设备信息CSV文件:").pack(anchor=tk.W, pady=(0, 5))
        self.device_file_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.device_file_var, width=30).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="浏览...", command=self._browse_device_file).pack(fill=tk.X, pady=(0, 10))
        
        # 文字设置
        text_settings_frame = ttk.LabelFrame(control_frame, text="文字设置", padding="10")
        text_settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(text_settings_frame, text="文字高度(像素):").pack(anchor=tk.W, pady=(0, 5))
        self.font_size_var = tk.IntVar(value=13)
        ttk.Entry(text_settings_frame, textvariable=self.font_size_var, width=10).pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(text_settings_frame, text="上下间隔(像素):").pack(anchor=tk.W, pady=(0, 5))
        self.spacing_var = tk.IntVar(value=4)
        ttk.Entry(text_settings_frame, textvariable=self.spacing_var, width=10).pack(fill=tk.X, pady=(0, 5))
        
        # 操作按钮
        ttk.Button(control_frame, text="预览", command=self._preview).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="导出图片", command=self._export_image).pack(fill=tk.X)
        
        # 右侧预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览", padding="10")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 预览画布
        self.preview_canvas_frame = ttk.Frame(preview_frame)
        self.preview_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(self.preview_canvas_frame, bg="white")
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(self.preview_canvas_frame, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.preview_canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.preview_canvas.bind('<Configure>', lambda e: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
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
    
    def _generate_image(self, preview=False):
        if self.coordinates_df is None or self.devices_df is None:
            messagebox.showerror("错误", "请先加载坐标文件和设备文件")
            return None
        
        # 检查数据行数是否匹配
        if len(self.coordinates_df) != len(self.devices_df):
            messagebox.showerror("错误", f"坐标点数量 ({len(self.coordinates_df)}) 与设备数量 ({len(self.devices_df)}) 不匹配")
            return None
        
        # A4尺寸在300dpi下的像素: 2480 × 3508
        width, height = 2480, 3508
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 获取文字设置
        font_size = self.font_size_var.get()
        spacing = self.spacing_var.get()
        
        # 获取合适的字体
        font = self._get_font(font_size)
        
        # 处理每个点
        for i in range(len(self.coordinates_df)):
            try:
                # 获取坐标
                x = float(self.coordinates_df.iloc[i]['X坐标'])
                y = float(self.coordinates_df.iloc[i]['Y坐标'])
                
                # 获取设备信息
                device_code = self.devices_df.iloc[i]['device_code']
                password = self.devices_df.iloc[i]['password']
                
                # 准备要显示的文本
                text1 = f"设备码：{device_code}"
                text2 = f"密钥：{password}"
                
                # 计算文本宽度以实现居中对齐
                text1_width = draw.textlength(text1, font=font)
                text2_width = draw.textlength(text2, font=font)
                
                # 计算文字位置（以坐标点为中心）
                # 设备码在上方，密钥在下方，中间间隔spacing像素
                text1_x = x - text1_width / 2  # 水平居中
                text1_y = y - font_size - spacing  # 上方
                
                text2_x = x - text2_width / 2  # 水平居中
                text2_y = y + spacing  # 下方
                
                # 绘制文字
                draw.text((text1_x, text1_y), text1, font=font, fill='black')
                draw.text((text2_x, text2_y), text2, font=font, fill='black')
                
                # 如果是预览，可绘制坐标点标记
                if preview:
                    # 绘制一个小十字标记坐标点
                    marker_size = 5
                    draw.line([(x - marker_size, y), (x + marker_size, y)], fill='red', width=1)
                    draw.line([(x, y - marker_size), (x, y + marker_size)], fill='red', width=1)
                    
            except Exception as e:
                messagebox.showerror("错误", f"处理第 {i+1} 个点时出错: {str(e)}")
                continue
        
        return image
    
    def _preview(self):
        self.status_var.set("正在生成预览...")
        self.root.update()
        
        try:
            # 生成原始尺寸图像
            full_image = self._generate_image(preview=True)
            if full_image is None:
                self.status_var.set("预览生成失败")
                return
            
            # 保存为临时文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # 缩小图像用于预览
            scale_factor = 0.2  # 缩小到20%
            preview_size = (int(full_image.width * scale_factor), int(full_image.height * scale_factor))
            preview_img = full_image.resize(preview_size, Image.Resampling.LANCZOS)
            preview_img.save(temp_filename)
            
            # 在画布上显示预览
            self.preview_image = tk.PhotoImage(file=temp_filename)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
            self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
            
            self.status_var.set("预览生成成功")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成预览时出错: {str(e)}")
            self.status_var.set("预览生成失败")
    
    def _export_image(self):
        if self.coordinates_df is None or self.devices_df is None:
            messagebox.showerror("错误", "请先加载坐标文件和设备文件")
            return
        
        self.status_var.set("正在导出图片...")
        self.root.update()
        
        try:
            # 生成图像
            image = self._generate_image(preview=False)
            if image is None:
                self.status_var.set("导出失败")
                return
            
            # 询问保存位置
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")]
            )
            
            if filename:
                # 保存图像，设置300dpi
                image.save(filename, dpi=(300, 300))
                self.status_var.set(f"图片已导出至: {filename}")
                messagebox.showinfo("成功", f"图片已成功导出至:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("错误", f"导出图片时出错: {str(e)}")
            self.status_var.set("导出失败")

if __name__ == "__main__":
    root = tk.Tk()
    app = CoordinateLabelGenerator(root)
    root.mainloop()
    