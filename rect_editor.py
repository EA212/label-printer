import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import pandas as pd
import re
import os
from PIL import Image, ImageDraw, ImageFont
import math

class A4CoordinateEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("A4绝对坐标文本编辑工具")
        self.root.geometry("1200x900")
        
        # A4纸物理参数（毫米）
        self.a4_width_mm = 210
        self.a4_height_mm = 297
        
        # 导出图片参数（300dpi：1mm ≈ 11.811像素）
        self.dpi = 300
        self.mm_to_px = self.dpi / 25.4  # 毫米转像素系数
        self.a4_width_px = int(self.a4_width_mm * self.mm_to_px)
        self.a4_height_px = int(self.a4_height_mm * self.mm_to_px)
        
        # 数据存储
        self.position_data = None  # 包含编号、x坐标(mm)、y坐标(mm)
        self.other_datas = {}      # 其他CSV数据（如password等，键为文件名）
        self.text_items = []       # 存储文本项信息：{编号、x、y、文字、字体大小、偏移量}
        self.preview_scale = 0.5   # 预览缩放比例（A4太大，缩小显示）
        
        # 创建界面
        self.create_widgets()
        
        # 绑定事件
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.root.bind("<Configure>", self.on_window_resize)

    def create_widgets(self):
        # 顶部控制栏
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 导入位置CSV
        ttk.Button(control_frame, text="导入位置CSV", command=self.import_position_csv).pack(side=tk.LEFT, padx=5)
        
        # 导入其他CSV（如password）
        ttk.Button(control_frame, text="导入参数CSV", command=self.import_other_csv).pack(side=tk.LEFT, padx=5)
        
        # 文字模板
        ttk.Label(control_frame, text="文字模板:").pack(side=tk.LEFT, padx=5)
        self.text_template = tk.StringVar(value="机器码：{device_id}\n密钥：{password}")
        ttk.Entry(control_frame, textvariable=self.text_template, width=60).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="应用模板", command=self.apply_template).pack(side=tk.LEFT, padx=5)
        
        # 导出按钮
        ttk.Button(control_frame, text="导出A4图片", command=self.export_a4_image).pack(side=tk.RIGHT, padx=5)
        
        # 预览区域
        preview_frame = ttk.Frame(self.root)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # A4预览画布（白色背景模拟A4纸）
        self.canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=2, highlightbackground="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏显示坐标信息
        self.status_var = tk.StringVar(value="就绪 | A4尺寸: 210mm×297mm | 预览比例: 50%")
        ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def import_position_csv(self):
        """导入包含编号、x坐标、y坐标的CSV（坐标单位：毫米）"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv")])
        if not file_path:
            return
            
        try:
            self.position_data = pd.read_csv(file_path)
            required_cols = ['编号', 'X坐标', 'Y坐标']
            for col in required_cols:
                if col not in self.position_data.columns:
                    messagebox.showerror("错误", f"位置CSV缺少列：{col}")
                    return
            
            # 初始化文本项（基于坐标）
            self.text_items = []
            for _, row in self.position_data.iterrows():
                self.text_items.append({
                    
                    "x_mm": float(row['X坐标']),
                    "y_mm": float(row['Y坐标']),
                    "text": "",
                    "font_size": 12,
                    "offset_x": 0,  # 手动调整偏移（像素）
                    "offset_y": 0
                })
            
            # 刷新预览
            self.refresh_preview()
            self.status_var.set(f"已导入位置数据：{len(self.text_items)}个点 | A4尺寸: 210mm×297mm")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{str(e)}")

    def import_other_csv(self):
        """导入其他参数CSV（如password、device_id等）"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv")])
        if not file_path:
            return
            
        try:
            df = pd.read_csv(file_path)
            # 假设以"编号"作为关联键
            if "编号" not in df.columns:
                messagebox.showerror("错误", "参数CSV必须包含'编号'列用于关联")
                return
            
            filename = os.path.basename(file_path)
            self.other_datas[filename] = df
            self.status_var.set(f"已导入参数CSV：{filename} | 共{len(df)}条数据")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{str(e)}")

    def apply_template(self):
        """将模板应用到所有文本项，替换{变量}"""
        if not self.position_data or not self.text_items:
            messagebox.showwarning("提示", "请先导入位置CSV")
            return
            
        template = self.text_template.get()
        # 收集所有可用数据列（位置数据+所有参数数据）
        all_data = self.position_data.copy()
        for df in self.other_datas.values():
            all_data = pd.merge(all_data, df, on="编号", how="left")
        
        # 替换每个文本项的变量
        for i, item in enumerate(self.text_items):
            # 找到对应编号的行
            row = all_data[all_data['编号'] == item['id']].iloc[0].to_dict() if len(all_data) > i else {}
            
            # 替换模板中的变量
            text = template
            for key, value in row.items():
                text = text.replace(f"{{{key}}}", str(value) if pd.notna(value) else f"{{{key}}}")
            
            item['text'] = text
        
        self.refresh_preview()

    def refresh_preview(self):
        """刷新预览画布（按预览比例显示A4纸上的内容）"""
        self.canvas.delete("all")
        
        # 绘制A4纸边框（预览用）
        a4_preview_width = int(self.a4_width_mm * self.mm_to_px * self.preview_scale)
        a4_preview_height = int(self.a4_height_mm * self.mm_to_px * self.preview_scale)
        self.canvas.create_rectangle(0, 0, a4_preview_width, a4_preview_height, outline="black", width=2)
        
        # 绘制所有文本项
        for item in self.text_items:
            # 计算预览位置（A4绝对坐标 × 缩放比例）
            x_px = (item['x_mm'] * self.mm_to_px + item['offset_x']) * self.preview_scale
            y_px = (item['y_mm'] * self.mm_to_px + item['offset_y']) * self.preview_scale
            
            # 绘制文本（预览用，字体按比例缩放）
            text_id = self.canvas.create_text(
                x_px, y_px, 
                text=item['text'],
                font=("SimHei", int(item['font_size'] * self.preview_scale)),
                anchor=tk.NW  # 以左上角为原点，匹配实际打印逻辑
            )
            
            # 绑定双击事件用于编辑
            self.canvas.tag_bind(text_id, "<Double-1>", lambda e, it=item: self.edit_text_item(it))
        
        # 设置画布滚动区域
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def edit_text_item(self, item):
        """编辑单个文本项（字体大小、位置偏移等）"""
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑 编号：{item['id']}")
        edit_window.geometry("400x300")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 文字内容
        ttk.Label(edit_window, text="文字内容：").pack(anchor=tk.W, padx=10, pady=5)
        text_widget = tk.Text(edit_window, height=6, wrap=tk.WORD)
        text_widget.pack(fill=tk.X, padx=10, pady=5)
        text_widget.insert(tk.END, item['text'])
        
        # 字体大小
        frame = ttk.Frame(edit_window)
        frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(frame, text="字体大小：").pack(side=tk.LEFT)
        font_size_var = tk.IntVar(value=item['font_size'])
        ttk.Spinbox(frame, from_=6, to=72, textvariable=font_size_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 位置偏移（相对于原始坐标）
        ttk.Label(edit_window, text="位置微调（像素）：").pack(anchor=tk.W, padx=10, pady=5)
        offset_frame = ttk.Frame(edit_window)
        offset_frame.pack(fill=tk.X, padx=10)
        
        ttk.Label(offset_frame, text="X偏移：").pack(side=tk.LEFT)
        offset_x_var = tk.IntVar(value=item['offset_x'])
        ttk.Spinbox(offset_frame, from_=-50, to=50, textvariable=offset_x_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(offset_frame, text="Y偏移：").pack(side=tk.LEFT)
        offset_y_var = tk.IntVar(value=item['offset_y'])
        ttk.Spinbox(offset_frame, from_=-50, to=50, textvariable=offset_y_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 应用按钮
        def apply():
            item['text'] = text_widget.get("1.0", tk.END).rstrip("\n")
            item['font_size'] = font_size_var.get()
            item['offset_x'] = offset_x_var.get()
            item['offset_y'] = offset_y_var.get()
            self.refresh_preview()
            edit_window.destroy()
        
        ttk.Button(edit_window, text="应用", command=apply).pack(pady=10)

    def export_a4_image(self):
        """导出A4大小图片，只包含文字，不包含方框，严格按绝对坐标"""
        if not self.text_items:
            messagebox.showwarning("提示", "没有可导出的内容")
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg")]
        )
        if not save_path:
            return
        
        try:
            # 创建A4尺寸的空白图片（白色背景）
            image = Image.new("RGB", (self.a4_width_px, self.a4_height_px), color="white")
            draw = ImageDraw.Draw(image)
            
            # 遍历所有文本项，按绝对坐标绘制
            for item in self.text_items:
                if not item['text']:
                    continue
                
                # 计算实际像素位置（考虑偏移量）
                x_px = item['x_mm'] * self.mm_to_px + item['offset_x']
                y_px = item['y_mm'] * self.mm_to_px + item['offset_y']
                
                # 加载字体（确保支持中文）
                try:
                    font = ImageFont.truetype("simhei.ttf", item['font_size'])
                except:
                    #  fallback字体
                    font = ImageFont.load_default()
                    messagebox.showwarning("提示", f"编号{item['id']}：未找到黑体字体，使用默认字体")
                
                # 绘制文字（左上角对齐）
                draw.text((x_px, y_px), item['text'], font=font, fill="black")
            
            # 保存图片
            image.save(save_path, dpi=(self.dpi, self.dpi))
            messagebox.showinfo("成功", f"已导出A4图片到：\n{save_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")

    def on_zoom(self, event):
        """预览缩放"""
        if event.delta > 0:
            self.preview_scale = min(1.0, self.preview_scale + 0.1)
        else:
            self.preview_scale = max(0.2, self.preview_scale - 0.1)
        
        self.refresh_preview()
        self.status_var.set(f"预览比例：{int(self.preview_scale*100)}% | A4尺寸: 210mm×297mm")

    def on_window_resize(self, event):
        """窗口大小改变时刷新预览"""
        self.refresh_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = A4CoordinateEditor(root)
    root.mainloop()
    
