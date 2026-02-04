import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import random
import string
import os

class ReversibleCSVGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("可逆CSV生成器")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))
        self.style.configure("TText", font=("SimHei", 10))
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 种子输入
        ttk.Label(main_frame, text="种子 (留空将自动生成):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.seed_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.seed_var, width=50).grid(row=0, column=1, pady=5)
        
        # 数量输入
        ttk.Label(main_frame, text="生成数量:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.count_var = tk.StringVar(value="10")
        ttk.Entry(main_frame, textvariable=self.count_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="生成CSV", command=self.generate_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="测试转换", command=self.test_conversion).pack(side=tk.LEFT, padx=5)
        
        # 预览区域
        ttk.Label(main_frame, text="预览:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.preview_text = tk.Text(main_frame, height=10, width=60)
        self.preview_text.grid(row=3, column=1, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 生成一个随机种子作为默认
        self.seed_var.set(str(random.randint(100000, 999999)))
    
    def get_seed(self):
        """获取种子，如果为空则生成一个"""
        seed_str = self.seed_var.get().strip()
        if not seed_str:
            seed = random.randint(100000, 999999)
            self.seed_var.set(str(seed))
            return seed
        try:
            return int(seed_str)
        except ValueError:
            messagebox.showerror("错误", "种子必须是整数")
            return None
    
    def get_count(self):
        """获取生成数量"""
        try:
            count = int(self.count_var.get().strip())
            if count <= 0:
                raise ValueError
            return count
        except ValueError:
            messagebox.showerror("错误", "数量必须是正整数")
            return None
    
    def device_to_password(self, device_num, seed):
        """将设备编号转换为密码"""
        # 使用种子进行可逆转换
        base = device_num + seed
        # 确保结果在有效范围内
        transformed = (base * 12345) % 99990 + 10  # 确保4位数字范围
        
        # 提取前4位数字
        num_part = transformed % 10000
        # 生成字母部分 (基于转换后的值确保可逆)
        letter_index = (transformed // 10000) % 26
        letter = string.ascii_letters[letter_index]
        
        # 格式化为4位数字加1位字母
        return f"{num_part:04d}{letter}"
    
    def password_to_device(self, password, seed):
        """将密码转换回设备编号"""
        if len(password) != 5:
            return None
        
        num_part = password[:4]
        letter = password[4]
        
        try:
            num = int(num_part)
        except ValueError:
            return None
        
        # 找到字母对应的索引
        try:
            letter_index = string.ascii_letters.index(letter)
        except ValueError:
            return None
        
        # 反向转换
        transformed = num + letter_index * 10000
        base = (transformed * 87654) % 99990  # 12345的模逆
        device_num = (base - seed) % 99990
        
        return device_num
    
    def generate_csv(self):
        """生成CSV文件"""
        seed = self.get_seed()
        count = self.get_count()
        
        if seed is None or count is None:
            return
        
        # 询问保存路径
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 生成数据
        data = []
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "password,device_code\n")
        
        for i in range(count):
            device_num = i
            device_code = f"E{i:04d}"  # 从E0000开始
            password = self.device_to_password(device_num, seed)
            data.append((password, device_code))
            self.preview_text.insert(tk.END, f"{password},{device_code}\n")
        
        # 保存到CSV
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["password", "device_code"])
                writer.writerows(data)
            
            self.status_var.set(f"成功生成 {count} 条记录到 {os.path.basename(file_path)}")
            messagebox.showinfo("成功", f"CSV文件已保存到:\n{file_path}")
        except Exception as e:
            self.status_var.set(f"生成失败: {str(e)}")
            messagebox.showerror("错误", f"保存文件时出错:\n{str(e)}")
    
    def test_conversion(self):
        """测试转换是否可逆"""
        seed = self.get_seed()
        if seed is None:
            return
        
        # 随机测试几个值
        test_numbers = [0, 5, 10, 100, 500, 1000, random.randint(0, 9999)]
        results = []
        all_passed = True
        
        for num in test_numbers:
            device_code = f"E{num:04d}"
            password = self.device_to_password(num, seed)
            converted_back = self.password_to_device(password, seed)
            
            passed = (converted_back == num)
            if not passed:
                all_passed = False
            
            results.append(
                f"设备编号: {device_code} -> 密码: {password} -> "
                f"转换回: E{converted_back:04d} {'✓' if passed else '✗'}"
            )
        
        # 显示测试结果
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "转换测试结果:\n\n")
        for result in results:
            self.preview_text.insert(tk.END, result + "\n")
        
        if all_passed:
            self.status_var.set("所有转换测试通过")
        else:
            self.status_var.set("转换测试失败")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReversibleCSVGenerator(root)
    root.mainloop()
