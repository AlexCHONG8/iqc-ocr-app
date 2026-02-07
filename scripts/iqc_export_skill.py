import re
import math
import json
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class DimensionStats:
    name: str
    spec: str
    nominal: float
    usl: float
    lsl: float
    measurements: List[float]
    mean: float = 0.0
    max_val: float = 0.0
    min_val: float = 0.0
    std_dev_overall: float = 0.0
    std_dev_within: float = 0.0
    cp: float = 0.0
    cpk: float = 0.0
    pp: float = 0.0
    ppk: float = 0.0
    six_sigma_spread: float = 0.0
    status: str = "OK"
    suggestion: str = ""
    conclusion: str = ""
    
    # Subgroup data for Xbar-R
    subgroups: List[dict] = None # List of {mean, range}
    x_bar_bar: float = 0.0
    r_bar: float = 0.0
    ucl_x: float = 0.0
    lcl_x: float = 0.0
    ucl_r: float = 0.0
    lcl_r: float = 0.0

    def calculate(self):
        if not self.measurements:
            return
        
        n_total = len(self.measurements)
        self.mean = sum(self.measurements) / n_total
        self.max_val = max(self.measurements)
        self.min_val = min(self.measurements)
        
        # 1. Overall Statistics (Ppk)
        if n_total > 1:
            variance = sum((x - self.mean) ** 2 for x in self.measurements) / (n_total - 1)
            self.std_dev_overall = math.sqrt(variance)
        else:
            self.std_dev_overall = 0.0
            
        self.six_sigma_spread = 6 * self.std_dev_overall

        # 2. Subgroup Analysis (n=5)
        subgroup_size = 5
        self.subgroups = []
        ranges = []
        means = []
        for i in range(0, n_total, subgroup_size):
            group = self.measurements[i:i + subgroup_size]
            if len(group) == subgroup_size:
                g_mean = sum(group) / subgroup_size
                g_range = max(group) - min(group)
                self.subgroups.append({"mean": g_mean, "range": g_range, "values": group})
                means.append(g_mean)
                ranges.append(g_range)
        
        if ranges:
            self.x_bar_bar = sum(means) / len(means)
            self.r_bar = sum(ranges) / len(ranges)
            
            # Constants for n=5
            A2 = 0.577
            D4 = 2.114
            D3 = 0
            d2 = 2.326
            
            self.ucl_x = self.x_bar_bar + A2 * self.r_bar
            self.lcl_x = self.x_bar_bar - A2 * self.r_bar
            self.ucl_r = D4 * self.r_bar
            self.lcl_r = D3 * self.r_bar
            
            # 3. Within Statistics (Cpk)
            self.std_dev_within = self.r_bar / d2
        else:
            self.std_dev_within = self.std_dev_overall

        # 4. Capability Indices
        def calc_indices(sigma):
            if sigma > 0:
                p = (self.usl - self.lsl) / (6 * sigma)
                pu = (self.usl - self.mean) / (3 * sigma)
                pl = (self.mean - self.lsl) / (3 * sigma)
                pk = min(pu, pl)
                return p, pk
            return 0.0, 0.0

        self.cp, self.cpk = calc_indices(self.std_dev_within)
        self.pp, self.ppk = calc_indices(self.std_dev_overall)

        # 5. Status & Suggestion
        if self.max_val > self.usl or self.min_val < self.lsl:
            self.status = "NG"
        
        self._generate_suggestion()
        self._generate_conclusion()

    def _generate_suggestion(self):
        if self.cpk < 1.0:
            self.suggestion = "【红色警示】该过程能力严重不足 (Cpk < 1.0)。目前虽无超标，但过程波动偏大，极易产生不合格品。建议：1. 检查生产设备精度；2. 反馈供方调整工艺参数；3. 对此批次实施 100% 检验。"
        elif self.cpk < 1.33:
            self.suggestion = "【橙色预警】过程能力尚可 (1.0 ≤ Cpk < 1.33)。属于受控但偏紧状态。建议加强末端监控，定期校准测量仪器，观察趋势防止下滑。"
        else:
            self.suggestion = "【绿色优良】过程能力极佳 (Cpk ≥ 1.33)。生产工艺非常稳定。建议保持当前控制状态，可考虑降低抽样频次以节省成本。"
        
        # Check for Bias
        tolerance = self.usl - self.lsl
        bias = abs(self.mean - self.nominal)
        if bias > (tolerance * 0.2) and self.cpk < 1.33:
            self.suggestion += " 另外发现均值明显偏离规格中心，建议调整机台中心值以消除偏差。"

    def _generate_conclusion(self):
        if self.status == "NG":
            self.conclusion = f"【最终结论：不合格】该检验项存在超标数值。即便 Cpk 良好，物理超标即判定为不合格项，需启动异常处理流程。"
        elif self.cpk < 1.33:
            self.conclusion = f"【最终结论：合格但过程不稳】虽实测值均在规格内，但 Cpk({self.cpk:.2f}) 未达到 1.33 的行业标杆要求，过程散布较大，建议对生产过程进行干预。"
        else:
            self.conclusion = f"【最终结论：优质合格】实测值全部合格，且过程能力指数 Cpk({self.cpk:.2f}) 表现优异，过程非常稳定。"

def parse_spec(spec_str: str):
    """
    Parses strings like '27.80+0.10-0.00' or 'Φ6.00±0.10'
    """
    spec_str = spec_str.replace('(mm)', '').replace(' ', '').replace('Φ', '')
    
    # Pattern for ± (e.g., 6.00±0.10)
    match_plus_minus = re.search(r'([\d.]+)[±±]([\d.]+)', spec_str)
    if match_plus_minus:
        nominal = float(match_plus_minus.group(1))
        tol = float(match_plus_minus.group(2))
        return nominal, nominal + tol, nominal - tol
    
    # Pattern for + / - (e.g., 27.80+0.10-0.00)
    match_two_tols = re.search(r'([\d.]+)\+([\d.]+)-([\d.]+)', spec_str)
    if match_two_tols:
        nominal = float(match_two_tols.group(1))
        upper = float(match_two_tols.group(2))
        lower = float(match_two_tols.group(3))
        return nominal, nominal + upper, nominal - lower

    # Pattern for just one (e.g., 27.8+0.1)
    match_one_tol = re.search(r'([\d.]+)\+([\d.]+)', spec_str)
    if match_one_tol:
        nominal = float(match_one_tol.group(1))
        upper = float(match_one_tol.group(2))
        return nominal, nominal + upper, nominal # Assumption: lower is 0 or same as nominal
        
    return 0.0, 0.0, 0.0

def extract_iqc_data(content: str):
    # Split content into sections (likely tables)
    # The dimension table usually contains "检验位置" and "1", "11", "13"
    
    # Extract headers
    meta = {
        "material_name": re.search(r'物料名称.*?<td colspan="2">(.*?)</td>', content).group(1) if re.search(r'物料名称', content) else "Unknown",
        "material_code": re.search(r'物料编码.*?<td colspan="2">(.*?)</td>', content).group(1) if re.search(r'物料编码', content) else "N/A",
        "batch_no": re.search(r'物料批号.*?<td colspan="2">(.*?)</td>', content).group(1) if re.search(r'物料批号', content) else "N/A",
        "supplier": re.search(r'供应商名称.*?<td colspan="2">(.*?)</td>', content).group(1) if re.search(r'供应商名称', content) else "N/A",
        "date": re.search(r'进料日期.*?<td colspan="2">(.*?)</td>', content).group(1) if re.search(r'进料日期', content) else "N/A",
    }

    dimensions = []
    
    # Target the dimension table specifically
    # It contains "检验位置" followed by "检验标准"
    dim_table_match = re.search(r'检验位置.*?检验标准.*?</table>', content, re.S)
    if dim_table_match:
        table_html = dim_table_match.group(0)
        
        # Extract labels from "检验位置" row
        labels_match = re.search(r'检验位置</td><td colspan="2">(.*?)</td><td colspan="2">(.*?)</td><td colspan="2">(.*?)</td>', table_html)
        labels = ["尺寸 " + l for l in labels_match.groups()] if labels_match else ["尺寸 1", "尺寸 11", "尺寸 13"]

        # Extract specs from "检验标准" row
        # Notice we use table_html here to limit the scope
        spec_match = re.search(r'检验标准</td><td colspan="2">(.*?)</td><td colspan="2">(.*?)</td><td colspan="2">(.*?)</td>', table_html)
        
        if spec_match:
            specs = spec_match.groups()
            dim_data = [[], [], []]
            
            # Extract measurements
            # <tr><td>序号</td><td>测试结果</td><td>结果判定</td>...</tr>
            rows = re.findall(r'<tr><td>\d+</td><td>([\d.]+)</td><td>.*?</td><td>([\d.]+)</td><td>.*?</td><td>([\d.]+)</td><td>.*?</td></tr>', table_html)
            
            for row in rows:
                dim_data[0].append(float(row[0]))
                dim_data[1].append(float(row[1]))
                dim_data[2].append(float(row[2]))
                
            for i, spec in enumerate(specs):
                nominal, usl, lsl = parse_spec(spec)
                ds = DimensionStats(name=labels[i], spec=spec, nominal=nominal, usl=usl, lsl=lsl, measurements=dim_data[i])
                ds.calculate()
                dimensions.append(asdict(ds))

    return {"meta": meta, "dimensions": dimensions}
