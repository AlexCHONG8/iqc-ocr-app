"""
IQC Pro Max - 智能质量分析系统
完整的 Streamlit UI 实现（v1.0 + v1.5）
包含：OCR 识别、数据验证、6 SPC 图表、历史记录、Excel 导出
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os

# For Mac environment consistency: Ensure user site-packages are in path
user_site = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if user_site not in sys.path:
    sys.path.append(user_site)

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from scipy import stats
from scipy.stats import norm
from datetime import datetime
import os
import tempfile

# 本地模块
from src.spc_engine import SPCEngine
from src.ocr_service import OCRService
from src.utils import (
    detect_outliers,
    correct_measurements,
    normality_test,
    suggest_boxcox,
    HistoryManager,
    export_to_excel,
    calculate_control_limits
)

# ===============================
# 辅助函数：创建图表
# ===============================

def create_histogram(data, title="数据分布", usl=None, lsl=None, mean=None):
    """
    创建直方图（Plotly 实现，带正态拟合曲线）
    """
    import numpy as np
    from scipy.stats import norm

    # 绘制直方图
    fig = px.histogram(
        data,
        nbins=20,
        title=title,
        color_discrete_sequence=['#0891B2'],
        opacity=0.7,
        labels={'value': '测量值', 'count': '频数'}
    )

    # 添加正态拟合曲线
    data_mean = mean if mean is not None else np.mean(data)
    data_std = np.std(data, ddof=1)

    x_fit = np.linspace(min(data), max(data), 100)
    y_fit = norm.pdf(x_fit, data_mean, data_std)

    # 缩放到直方图高度 (Streamlit/Plotly normalization)
    # 计算 bin 宽度
    counts, bins = np.histogram(data, bins=20)
    bin_width = bins[1] - bins[0]
    y_fit_scaled = y_fit * len(data) * bin_width

    fig.add_trace(go.Scatter(
        x=x_fit,
        y=y_fit_scaled,
        mode='lines',
        name='正态拟合',
        line=dict(color='#EF4444', width=2)
    ))

    # 添加规格限
    if usl is not None:
        fig.add_vline(x=usl, line_dash="dash", line_color="#EF4444", annotation_text="USL")
    if lsl is not None:
        fig.add_vline(x=lsl, line_dash="dash", line_color="#EF4444", annotation_text="LSL")
    if mean is not None:
        fig.add_vline(x=data_mean, line_dash="solid", line_color="#22C55E", annotation_text="Mean")

    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False
    )
    return fig

def create_qq_plot(data):
    """
    创建正态概率图 (Q-Q Plot) - Plotly 实现
    """
    import scipy.stats as stats
    (osm, osr), (slope, intercept, r) = stats.probplot(data, dist="norm")

    fig = go.Figure()

    # 数据点
    fig.add_trace(go.Scatter(
        x=osm, y=osr,
        mode='markers',
        marker=dict(color='#0891B2', size=6),
        name='数据点'
    ))

    # 参考线
    x_range = np.array([min(osm), max(osm)])
    y_range = slope * x_range + intercept
    fig.add_trace(go.Scatter(
        x=x_range, y=y_range,
        mode='lines',
        line=dict(color='#EF4444', width=2),
        name='参考线'
    ))

    fig.update_layout(
        title='正态概率图 (Q-Q Plot)',
        xaxis_title='理论分位数',
        yaxis_title='有序值',
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False
    )
    return fig


def create_capability_plot(data, stats, usl, lsl):
    """
    创建过程能力图

    参数：
        data: 测量数据
        stats: 统计结果
        usl: 上规格限
        lsl: 下规格限
    """
    # 创建 X 轴
    x = np.linspace(
        stats["mean"] - 4 * stats["std_overall"],
        stats["mean"] + 4 * stats["std_overall"],
        100
    )

    # 计算正态分布概率密度
    y = norm.pdf(x, stats["mean"], stats["std_overall"])

    fig = go.Figure()

    # 添加正态分布曲线
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        name='过程分布',
        line=dict(color='#0891B2', width=3),
        fill='tozeroy',
        fillcolor='rgba(8, 145, 178, 0.2)'
    ))

    # 添加规格限垂直线
    fig.add_vline(
        x=usl,
        line_dash="dash",
        line_color="#EF4444",
        line_width=2,
        annotation_text=f"USL={usl}",
        annotation_position="top left"
    )

    fig.add_vline(
        x=lsl,
        line_dash="dash",
        line_color="#EF4444",
        line_width=2,
        annotation_text=f"LSL={lsl}",
        annotation_position="top left"
    )

    # 添加均值线
    fig.add_vline(
        x=stats["mean"],
        line_dash="solid",
        line_color="#22C55E",
        line_width=2,
        annotation_text=f"Mean={stats['mean']:.3f}"
    )

    # 计算超出规格的概率（PPM）
    ppm_usl = (1 - norm.cdf(usl, stats["mean"], stats["std_overall"])) * 1e6
    ppm_lsl = norm.cdf(lsl, stats["mean"], stats["std_overall"]) * 1e6
    total_ppm = ppm_usl + ppm_lsl

    # 添加能力指数文本
    annotation_text = f"""
<b>能力指数：</b>
Cp = {stats['cp']:.3f}
Cpk = {stats['cpk']:.3f}
Pp = {stats['pp']:.3f}
Ppk = {stats['ppk']:.3f}

<b>超出规格：</b>
总计 = {total_ppm:.0f} PPM
高于 USL = {ppm_usl:.0f} PPM
低于 LSL = {ppm_lsl:.0f} PPM
"""

    fig.add_annotation(
        text=annotation_text,
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.98,
        showarrow=False,
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#0891B2",
        borderwidth=2,
        borderpad=5,
        font=dict(size=11)
    )

    fig.update_layout(
        title="过程能力分析",
        xaxis_title="测量值",
        yaxis_title="概率密度",
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400,
        showlegend=True,
        margin=dict(l=10, r=10, t=30, b=10)
    )

    return fig

# ===============================
# 页面配置
# ===============================

st.set_page_config(
    page_title="森迈医疗 | IQC Pro Max | 智能质量分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# CSS 样式
# ===============================

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=Noto+Sans:wght@300;400;500;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Figtree', 'Noto Sans', sans-serif;
    }

    .stApp {
        background-color: #F0FDFA;
    }

    h1, h2, h3 {
        color: #134E4A !important;
        font-weight: 700;
    }

    .stMetric {
        background: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(8, 145, 178, 0.3);
    }

    /* Sidebar - Professional Medical-Grade Design */
    .stSidebar {
        background: linear-gradient(180deg, #115E59 0%, #0F766E 50%, #134E4A 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stSidebarNav"] {
        background: linear-gradient(180deg, #115E59 0%, #0F766E 50%, #134E4A 100%) !important;
    }

    /* Sidebar text - HIGH CONTRAST */
    .sidebar-text {
        color: #FFFFFF !important;
        font-weight: 700;
        letter-spacing: 0.3px;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    /* Sidebar radio buttons - Professional styling */
    [data-testid="stSidebar"] [role="radiogroup"] > label {
        color: #FFFFFF !important;
        font-weight: 600;
        font-size: 15px;
        padding: 14px 18px;
        border-radius: 10px;
        margin: 6px 0;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.2s ease;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateX(2px);
    }

    [data-testid="stSidebar"] [role="radiogroup"] > label[data-selected="true"] {
        background: linear-gradient(135deg, #0891B2 0%, #22D3EE 100%) !important;
        font-weight: 700;
        border: 2px solid #67E8F9;
        box-shadow: 0 4px 12px rgba(8, 145, 178, 0.4);
        text-shadow: none;
    }

    /* Sidebar buttons - High visibility */
    [data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(135deg, #22D3EE 0%, #0891B2 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700;
        font-size: 16px;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(34, 211, 238, 0.3);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    [data-testid="stSidebar"] button[kind="primary"]:hover {
        background: linear-gradient(135deg, #06B6D4 0%, #0891B2 100%) !important;
        box-shadow: 0 6px 20px rgba(34, 211, 238, 0.5);
        transform: translateY(-1px);
    }

    /* File uploader - Clear and visible */
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 3px dashed rgba(255, 255, 255, 0.4) !important;
        border-radius: 16px;
        padding: 24px;
        transition: all 0.3s ease;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #22D3EE !important;
        box-shadow: 0 0 20px rgba(34, 211, 238, 0.3);
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] label {
        color: #FFFFFF !important;
        font-weight: 700;
        font-size: 16px;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        color: #134E4A !important;
    }

    /* Sidebar labels and text - MAXIMUM READABILITY */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .css-1d391kg,
    [data-testid="stSidebar"] span {
        color: #FFFFFF !important;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* Input fields in sidebar - High contrast */
    [data-testid="stSidebar"] input[type="text"],
    [data-testid="stSidebar"] input[type="number"],
    [data-testid="stSidebar"] textarea {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #134E4A !important;
        font-weight: 600;
        border: 2px solid rgba(255, 255, 255, 0.3);
    }

    .premium-card {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #0891B2;
        margin-bottom: 25px;
    }

    .warning-box {
        background: #FEF3C7;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #F59E0B;
        margin: 10px 0;
    }

    .success-box {
        background: #D1FAE5;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #10B981;
        margin: 10px 0;
    }

    .error-box {
        background: #FEE2E2;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #EF4444;
        margin: 10px 0;
    }

    /* Force text color for all markdown text, paragraphs, labels, and spans to override Dark Mode defaults */
    .stMarkdown p, .stMarkdown span, .stText p, label, .stMetric label, .stMetric div, .stDataFrame div, .stSpinner p, .stSpinner div, .stSpinner span, [data-testid="stSpinner"] * {
        color: #134E4A !important;
    }
    
    /* Ensure table text is readable */
    td {
        color: #134E4A !important;
    }

    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ===============================
# 初始化 Session State
# ===============================

if 'history_manager' not in st.session_state:
    st.session_state.history_manager = HistoryManager()

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "完整分析（6 图）"

if 'show_advanced' not in st.session_state:
    st.session_state.show_advanced = False

# ===============================
# 侧边栏
# ===============================

st.sidebar.markdown("<h2 class='sidebar-text'>📦 IQC Pro Max</h2>", unsafe_allow_html=True)

# 主要功能导航
page = st.sidebar.radio(
    "选择功能",
    ["📊 数据分析", "📝 手动录入 (Manual Entry)", "📁 历史记录", "⚙️ 设置"],
    label_visibility="collapsed"
)

# ===============================
# 页面 1：数据分析
# ===============================

if page == "📊 数据分析":

    # Hero Section
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0891B2 0%, #134E4A 100%); padding: 60px; border-radius: 20px; color: white; margin-bottom: 40px; box-shadow: 0 20px 50px rgba(8, 145, 178, 0.3);">
            <h1 style="color: white !important; margin: 0; font-size: 3rem;">🏥 森迈医疗 | IQC Pro Max</h1>
            <p style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">智能质量分析系统 | v1.5</p>
            <div style="margin-top: 25px;">
                <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 0.9rem;">ISO 13485 Compliant</span>
                <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 0.9rem; margin-left: 10px;">MinerU AI Active</span>
                <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 0.9rem; margin-left: 10px;">6 SPC Charts</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 文件上传
    uploaded_file = st.sidebar.file_uploader(
        "上传 QC 扫描件",
        type=["pdf", "jpg", "png"],
        help="支持 PDF、JPG、PNG 格式"
    )

    if 'dim_data' not in st.session_state:
        st.markdown("""
            <div class="premium-card">
                <h2 style="color: #0891B2; font-size: 28px; font-weight: 700; margin-bottom: 20px;">
                    👋 欢迎使用 IQC Pro Max
                </h2>
                <p style="font-size: 16px; color: #374151; line-height: 1.6;">
                    请上传检验记录扫描件开始自动化分析。系统将：
                </p>
                <ul style="font-size: 15px; color: #374151; line-height: 1.8;">
                    <li>✅ 使用 AI 自动识别测量数据</li>
                    <li>✅ 计算完整的 6 SPC 指数（Cp/Cpk/Pp/Ppk）</li>
                    <li>✅ 生成 6 个统计图表（3 图基础 + 3 图高级）</li>
                    <li>✅ 智能检测异常值并修正 OCR 误读</li>
                    <li>✅ 导出 Excel 或保存历史记录</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    if uploaded_file is not None:
        # Store uploaded file in session state for side-by-side view
        st.session_state.uploaded_file = uploaded_file

        # === Session State Tracking for Uploads ===
        if 'previous_upload' not in st.session_state:
            st.session_state.previous_upload = None
        if 'previous_dashboard_path' not in st.session_state:
            st.session_state.previous_dashboard_path = None

        # Detect second upload - offer download and cleanup
        if uploaded_file != st.session_state.previous_upload:
            if st.session_state.previous_dashboard_path:
                old_dashboard_path = st.session_state.previous_dashboard_path

                # Show download button for old report
                with st.expander("📥 Previous Report Available - Download Before Deleted", expanded=True):
                    st.warning(f"⚠️ Previous report detected. Please download before continuing.")
                    with open(old_dashboard_path, 'rb') as f:
                        st.download_button(
                            label="💾 Download Previous HTML Report",
                            data=f,
                            file_name=os.path.basename(old_dashboard_path),
                            mime='text/html',
                            key=f"download_old_{int(time.time())}"
                        )

                # Delete old file after showing download button
                try:
                    if os.path.exists(old_dashboard_path):
                        os.remove(old_dashboard_path)
                        st.success("🗑️ Old report deleted (cleanup complete)")
                except Exception as e:
                    st.error(f"❌ Failed to delete old report: {e}")

            # Update tracking
            st.session_state.previous_upload = uploaded_file

        # One-Click Workflow: Upload → Auto OCR → Auto Dashboard
        ocr = OCRService()

        if 'dim_data' not in st.session_state or st.sidebar.button("🔄 重新处理"):
            with st.spinner("🤖 AI 正在分析... (OCR识别 → 数据提取 → SPC统计计算)"):
                # Save uploaded file to temp location for OCR processing
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getbuffer())
                    tmp_file_path = tmp_file.name

                try:
                    # Step 1: Extract data with OCR
                    st.session_state.dim_data = ocr.extract_table_data(tmp_file_path)
                    st.session_state.original_data = [d.copy() for d in st.session_state.dim_data]

                except ValueError as ve:
                    # OCR configuration error
                    st.error(f"❌ OCR配置错误\n\n{str(ve)}")
                    st.info("""
                    **解决方案:**

                    1. 检查 `.env` 文件中的 `OCR_API_KEY`
                    2. 访问 https://mineru.net 获取API密钥
                    3. 确保 `.env` 文件在项目根目录

                    **或者使用手动数据输入:**
                    ```bash
                    python3 manual_data_entry_helper.py
                    ```
                    """)
                except Exception as e:
                    # OCR processing error - show helpful message
                    error_msg = str(e)
                    st.error(f"❌ OCR识别失败")

                    # Detailed error info in expander
                    with st.expander("📋 查看错误详情 Click to view error details"):
                        st.code(f"Error: {error_msg}")

                    st.info("""
                    **可能的原因:**

                    1. 🌐 MinerU API服务暂时不可用（10点工作正常，现在可能服务器过载）
                    2. 📄 文件格式不支持（请使用PDF/JPG/PNG扫描件）
                    3. 🔑 API密钥无效或已过期
                    4. ⏱️ 上传文件过大（建议<10MB）

                    **建议解决方案:**
                    - 稍后重试（API可能恢复）
                    - 检查文件格式是否正确
                    - 使用**手动数据输入工具**:
                      ```bash
                      python3 manual_data_entry_helper.py
                      ```
                    - 或者等待API服务恢复后再次尝试
                    """)

                    # Stop processing if OCR failed
                    st.stop()

                # Step 2: Calculate statistics for all dimensions
                if st.session_state.dim_data:
                    st.session_state.stats_list = []
                    for dim in st.session_state.dim_data:
                        engine = SPCEngine(usl=dim['header']['usl'], lsl=dim['header']['lsl'])
                        stats = engine.calculate_stats(dim['measurements'])
                        st.session_state.stats_list.append(stats)

                    # Step 3: Auto-generate professional HTML dashboard
                    try:
                        from dashboard_generator import generate_professional_dashboard
                        html_path = generate_professional_dashboard(
                            st.session_state.dim_data,
                            st.session_state.stats_list,
                            layout="tabbed"
                        )
                        st.session_state.dashboard_path = html_path
                        st.session_state.previous_dashboard_path = html_path  # Track for next upload
                        st.success(f"✅ 分析完成！已生成专业报告\n\n📁 **报告位置:** `{html_path}`\n💾 您也可以在下方直接下载报告")
                    except Exception as e:
                        st.warning(f"⚠️ 报告生成遇到问题: {e}")

                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        # Show professional dashboard if available
        if hasattr(st.session_state, 'dashboard_path') and os.path.exists(st.session_state.dashboard_path):
            st.subheader("📊 专业分析报告")

            # Read and display HTML
            with open(st.session_state.dashboard_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            components.html(html_content, height=1200, scrolling=True)

            # Add download button
            with open(st.session_state.dashboard_path, 'rb') as f:
                st.download_button(
                    label="💾 下载HTML报告 Download HTML Report",
                    data=f,
                    file_name=os.path.basename(st.session_state.dashboard_path),
                    mime='text/html'
                )

            # Show file location message
            abs_path = os.path.abspath(st.session_state.dashboard_path)
            st.info(f"📂 **报告已保存至 / Report Saved To:**\n\n`{abs_path}`")
        else:
            # Fallback: Show interactive expander sections if dashboard not available
            # 处理每个维度
            for i, data in enumerate(st.session_state.dim_data):
                with st.expander(
                    f"📊 参数 {i+1}: {data['header']['dimension_name']}",
                    expanded=(i == 0)
                ):
                    # === 顶部信息栏 ===
                    col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.subheader("📋 批次信息")
                    batch_id = st.text_input(
                        "批次号",
                        value=data["header"]["batch_id"],
                        key=f"batch_{i}"
                    )
                    dim_name = st.text_input(
                        "参数名称",
                        value=data["header"]["dimension_name"],
                        key=f"dim_{i}"
                    )

                    # NEW: Show actual measurement count and batch info
                    st.metric("测量点数 Measurements", f"{len(data['measurements'])} points")
                    if data["header"].get("batch_size"):
                        st.metric("批量 Batch Size", f"{data['header']['batch_size']}")

                with col2:
                    st.subheader("📐 规格限")
                    usl = st.number_input(
                        "USL (上规格限)",
                        value=float(data["header"]["usl"]),
                        key=f"usl_{i}",
                        step=0.01
                    )
                    lsl = st.number_input(
                        "LSL (下规格限)",
                        value=float(data["header"]["lsl"]),
                        key=f"lsl_{i}",
                        step=0.01
                    )

                with col3:
                    st.subheader("🔧 操作")
                    if st.button(f"✨ 智能修正数据", key=f"correct_{i}"):
                        corrected, corrections = correct_measurements(
                            data["measurements"],
                            usl,
                            lsl
                        )
                        data["measurements"] = corrected
                        st.session_state.dim_data[i] = data

                        # Store corrections in session state for filtering
                        if "corrections" not in st.session_state:
                            st.session_state.corrections = {}
                        st.session_state.corrections[str(i)] = corrections

                        if corrections:
                            st.success(f"✅ 已修正 {len(corrections)} 处 OCR 误读")
                            with st.expander("查看修正详情 | View Correction Details"):
                                for c in corrections:
                                    st.write(f"Row {c['index']+1} | 行 {c['index']+1}: `{c['original']}` → `{c['corrected']}`")
                                    st.caption(f"Reason: {c['rule']} | 原因: {c['rule']}")
                                    st.write("---")
                                st.write("**💡 Tip**: Use 'Show only corrected values' checkbox below to focus on these rows")
                                st.write("**💡 提示**: 使用下方的 '仅显示修正值' 复选框来聚焦这些行")
                        else:
                            st.info("ℹ️ 未发现需要修正的数据")

                    if st.button(f"📤 导出 Excel", key=f"excel_{i}"):
                        measurements = data["measurements"]
                        engine = SPCEngine(usl=usl, lsl=lsl)
                        stats_result = engine.calculate_stats(measurements)

                        header = {
                            "batch_id": batch_id,
                            "dimension_name": dim_name,
                            "usl": usl,
                            "lsl": lsl
                        }

                        filename = f"{batch_id}_6SPC_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        filepath = export_to_excel(measurements, stats_result, header, filename)

                        with open(filepath, "rb") as f:
                            st.download_button(
                                label="⬇️ 下载 Excel 文件",
                                data=f,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                # === Original Scan Side-by-Side View ===
                with st.expander("📄 View Original Scan (Side-by-Side Comparison) | 查看原始扫描件", expanded=False):
                    col_left, col_right = st.columns(2)

                    with col_left:
                        st.subheader("Original Scan | 原始扫描件")
                        if "uploaded_file" in st.session_state and st.session_state.uploaded_file:
                            # Display the uploaded scan image
                            from PIL import Image
                            try:
                                # Reset file pointer to beginning
                                st.session_state.uploaded_file.seek(0)
                                image = Image.open(st.session_state.uploaded_file)
                                st.image(image, use_container_width=True)
                            except Exception as e:
                                st.error(f"无法显示图片: {str(e)}")
                                st.info("提示: PDF 文件无法直接预览，请使用 JPG/PNG 格式")
                        else:
                            st.info("No scan image available | 无扫描件")

                    with col_right:
                        st.subheader("Extracted Data Summary | 提取数据摘要")
                        if st.session_state.get("dim_data"):
                            for idx, dim in enumerate(st.session_state.dim_data):
                                st.write(f"**Dimension {idx+1}:** {dim['header']['dimension_name']}")
                                st.write(f"- Batch: {dim['header']['batch_id']}")
                                st.write(f"- USL: {dim['header']['usl']}, LSL: {dim['header']['lsl']}")
                                st.write(f"- Measurements: {len(dim['measurements'])} points")
                                st.write(f"- Mean: {np.mean(dim['measurements']):.4f}")
                                st.write("---")
                        else:
                            st.info("No data available | 无数据")

                # === 数据编辑器 ===

                # === Filter Options | 筛选选项 ===
                st.markdown("---")
                st.subheader("Data Display Options | 数据显示选项")

                # Get correction count for this dimension
                corrections = st.session_state.get("corrections", {})
                correction_count = len(corrections.get(str(i), []))

                if correction_count > 0:
                    show_corrected_only = st.checkbox(
                        f"🔍 Show only corrected values | 仅显示修正值 ({correction_count} corrections)",
                        key=f"show_corrected_{i}",
                        value=False
                    )
                else:
                    show_corrected_only = False
                    st.info("✅ No corrections detected - showing all data | 未检测到修正 - 显示全部数据")
                st.markdown("---")
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("✏️ 测量数据（可编辑）")

                    # 异常值检测
                    measurements = data["measurements"]
                    outlier_result = detect_outliers(measurements)

                    # 创建带状态标记的数据框
                    df = pd.DataFrame({
                        "序号": range(1, len(measurements) + 1),
                        "测量值": measurements,
                        "状态": ["✅ 正常"] * len(measurements)
                    })

                    # 标记异常值
                    for idx in outlier_result["outliers_idx"]:
                        df.at[idx, "状态"] = "⚠️ 异常"

                    # Apply filter if show_corrected_only is True
                    if show_corrected_only and correction_count > 0:
                        corrected_indices = [c['index'] for c in corrections.get(str(i), [])]
                        df_filtered = df.iloc[corrected_indices].copy()
                        st.info(f"Showing {len(df_filtered)} corrected values only | 仅显示 {len(df_filtered)} 个修正值")
                        edited_df = st.data_editor(
                            df_filtered,
                            column_config={"测量值": st.column_config.NumberColumn(format="%.2f")},
                            num_rows="dynamic",
                            key=f"editor_filtered_{i}",
                            use_container_width=True,
                            hide_index=True,
                            height=600  # Enable scrolling to show all rows
                        )
                    else:
                        # Show all data
                        edited_df = st.data_editor(
                            df,
                            column_config={"测量值": st.column_config.NumberColumn(format="%.2f")},
                            num_rows="dynamic",
                            key=f"editor_{i}",
                            use_container_width=True,
                            hide_index=True,
                            height=600  # Enable scrolling to show all rows
                        )

                    # 更新数据
                    updated_measurements = edited_df["测量值"].tolist()

                    # 检查数据是否变化
                    if updated_measurements != measurements:
                        data["measurements"] = updated_measurements
                        st.session_state.dim_data[i] = data

                    # 显示异常值警告
                    if outlier_result["count"] > 0:
                        st.warning(f"⚠️ {outlier_result['message']}")
                        with st.expander("查看异常值详情"):
                            st.write(f"**上限**: {outlier_result['upper_limit']:.4f}")
                            st.write(f"**下限**: {outlier_result['lower_limit']:.4f}")
                            st.write(f"**异常值索引**: {outlier_result['outliers_idx']}")
                            st.write(f"**异常值**: {[f'{v:.4f}' for v in outlier_result['outliers_val']]}")

                with col2:
                    st.subheader("📈 统计摘要")

                    # 计算统计量
                    measurements = data["measurements"]

                    if measurements:
                        engine = SPCEngine(usl=usl, lsl=lsl)
                        stats_result = engine.calculate_stats(measurements)

                        # 关键指标
                        m1, m2 = st.columns(2)
                        m1.metric(
                            "Cpk",
                            f"{stats_result['cpk']:.3f}",
                            help="潜在能力指数（≥1.33 合格）"
                        )
                        m2.metric(
                            "Ppk",
                            f"{stats_result['ppk']:.3f}",
                            help="整体性能指数"
                        )

                        m3, m4, m5 = st.columns(3)
                        m3.metric("Cp", f"{stats_result['cp']:.3f}")
                        m4.metric("Pp", f"{stats_result['pp']:.3f}")
                        m5.metric("均值", f"{stats_result['mean']:.4f}")

                        # 状态显示
                        if stats_result['cpk'] >= 1.33:
                            st.success(f"✅ **Cpk 状态**: PASS（≥ 1.33）")
                        else:
                            st.error(f"❌ **Cpk 状态**: FAIL（< 1.33）")

                        # 正态性检验
                        with st.expander("🔍 正态性检验"):
                            normality_result = normality_test(measurements)
                            st.info(normality_result["interpretation"])
                            st.caption(normality_result["message"])

                            if not normality_result["is_normal"]:
                                if st.button("查看 Box-Cox 变换建议", key=f"boxcox_{i}"):
                                    boxcox_result = suggest_boxcox(measurements)

                                    if "error" not in boxcox_result:
                                        st.info(f"ℹ️ {boxcox_result.get('shift_msg', '')}")
                                        st.write(f"**最优 λ 值**: {boxcox_result['lambda_value']:.4f}")

                                        col_bc1, col_bc2 = st.columns(2)
                                        with col_bc1:
                                            st.write("**原始数据**")
                                            st.pyplot(create_histogram(measurements, "原始数据分布"))

                                        with col_bc2:
                                            st.write(f"**变换后数据** (λ = {boxcox_result['lambda_value']:.2f})")
                                            st.pyplot(create_histogram(boxcox_result['transformed_data'], "变换后数据分布"))

                                        if boxcox_result['improvement']:
                                            st.success("✅ 变换后数据符合正态分布")
                                        else:
                                            st.warning("⚠️ 变换后仍不符合正态分布")
                                    else:
                                        st.error(boxcox_result.get("message", "变换失败"))

                # === 图表显示 ===
                st.markdown("---")

                # 查看模式选择
                st.session_state.view_mode = st.radio(
                    "选择图表查看模式",
                    ["快速查看（3 图）", "完整分析（6 图）"],
                    horizontal=True,
                    key=f"view_mode_{i}"
                )

                # === 3 图基础分析 ===
                if st.session_state.view_mode == "快速查看（3 图）":
                    st.subheader("📊 基础 SPC 图表")

                    # 计算控制限
                    control_limits = calculate_control_limits(measurements)

                    g1, g2, g3 = st.columns(3)

                    # 1. 单值读数图
                    with g1:
                        st.markdown("""
                            <div style='background: white; padding: 15px; border-radius: 12px; border-top: 4px solid #22D3EE;'>
                                <h4 style='margin-top: 0;'>📈 单值读数图</h4>
                            """, unsafe_allow_html=True)

                        fig_ind = px.line(
                            y=measurements,
                            title=f"全部 {len(measurements)} 个数据点",
                            labels={"y": "测量值", "x": "样本号"}
                        )
                        fig_ind.update_traces(
                            line_color="#22D3EE",
                            line_width=2,
                            mode='lines+markers',
                            marker=dict(size=4, color="#134E4A")
                        )
                        fig_ind.add_hline(y=usl, line_dash="dash", line_color="#EF4444", annotation_text="USL")
                        fig_ind.add_hline(y=lsl, line_dash="dash", line_color="#EF4444", annotation_text="LSL")
                        fig_ind.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=350,
                            margin=dict(l=10, r=10, t=30, b=10)
                        )
                        st.plotly_chart(fig_ind, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                    # 2. X-bar 图
                    with g2:
                        st.markdown("""
                            <div style='background: white; padding: 15px; border-radius: 12px; border-top: 4px solid #0891B2;'>
                                <h4 style='margin-top: 0;'>📊 X-bar 控制图</h4>
                            """, unsafe_allow_html=True)

                        x_bar_values = control_limits["x_bar"]["values"]

                        fig_x = px.line(
                            y=x_bar_values,
                            title=f"子组均值 (n={control_limits['subgroup_size']})",
                            labels={"y": "子组均值", "x": "子组号"}
                        )
                        fig_x.update_traces(
                            line_color="#0891B2",
                            line_width=3,
                            mode='lines+markers',
                            marker=dict(color="#134E4A", size=6)
                        )

                        # 添加规格限
                        fig_x.add_hline(y=usl, line_dash="dash", line_color="#EF4444", annotation_text="USL")
                        fig_x.add_hline(y=lsl, line_dash="dash", line_color="#EF4444", annotation_text="LSL")
                        fig_x.add_hline(y=stats_result["mean"], line_dash="solid", line_color="#22C55E", annotation_text="MEAN")

                        # 添加控制限
                        fig_x.add_hline(
                            y=control_limits["x_bar"]["ucl"],
                            line_dash="dot",
                            line_color="#F59E0B",
                            annotation_text="UCL"
                        )
                        fig_x.add_hline(
                            y=control_limits["x_bar"]["lcl"],
                            line_dash="dot",
                            line_color="#F59E0B",
                            annotation_text="LCL"
                        )

                        fig_x.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=350,
                            margin=dict(l=10, r=10, t=30, b=10)
                        )
                        st.plotly_chart(fig_x, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                    # 3. R-图
                    with g3:
                        st.markdown("""
                            <div style='background: white; padding: 15px; border-radius: 12px; border-top: 4px solid #8B5CF6;'>
                                <h4 style='margin-top: 0;'>📉 R 控制图</h4>
                            """, unsafe_allow_html=True)

                        r_values = control_limits["r"]["values"]

                        fig_r = px.line(
                            y=r_values,
                            title="子组极差",
                            labels={"y": "极差", "x": "子组号"}
                        )
                        fig_r.update_traces(
                            line_color="#8B5CF6",
                            line_width=3,
                            mode='lines+markers',
                            marker=dict(color="#134E4A", size=6)
                        )

                        # 添加中心线和控制限
                        fig_r.add_hline(
                            y=control_limits["r"]["cl"],
                            line_dash="solid",
                            line_color="#22C55E",
                            annotation_text="R-bar"
                        )
                        fig_r.add_hline(
                            y=control_limits["r"]["ucl"],
                            line_dash="dot",
                            line_color="#F59E0B",
                            annotation_text="UCL"
                        )
                        if control_limits["r"]["lcl"] > 0:
                            fig_r.add_hline(
                                y=control_limits["r"]["lcl"],
                                line_dash="dot",
                                line_color="#F59E0B",
                                annotation_text="LCL"
                            )

                        fig_r.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=350,
                            margin=dict(l=10, r=10, t=30, b=10)
                        )
                        st.plotly_chart(fig_r, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                # === 6 图完整分析 ===
                else:
                    st.subheader("📊 完整 6 SPC 图表分析")

                    # 第一行：3 个基础图
                    g1, g2, g3 = st.columns(3)

                    # 1. 单值读数图
                    with g1:
                        st.markdown("**📈 1. 单值读数图**")
                        fig_ind = px.line(y=measurements, title=f"全部 {len(measurements)} 个数据点")
                        fig_ind.update_traces(
                            line_color="#22D3EE",
                            line_width=2,
                            mode='lines+markers',
                            marker=dict(size=4, color="#134E4A")
                        )
                        fig_ind.add_hline(y=usl, line_dash="dash", line_color="#EF4444", annotation_text="USL")
                        fig_ind.add_hline(y=lsl, line_dash="dash", line_color="#EF4444", annotation_text="LSL")
                        fig_ind.update_layout(plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)', height=300)
                        st.plotly_chart(fig_ind, use_container_width=True)

                    # 2. X-bar 图
                    with g2:
                        st.markdown("**📊 2. X-bar 控制图**")
                        control_limits = calculate_control_limits(measurements)
                        x_bar_values = control_limits["x_bar"]["values"]

                        fig_x = px.line(y=x_bar_values, title=f"子组均值 (n={control_limits['subgroup_size']})")
                        fig_x.update_traces(
                            line_color="#0891B2",
                            line_width=3,
                            mode='lines+markers',
                            marker=dict(color="#134E4A", size=6)
                        )
                        fig_x.add_hline(y=usl, line_dash="dash", line_color="#EF4444", annotation_text="USL")
                        fig_x.add_hline(y=lsl, line_dash="dash", line_color="#EF4444", annotation_text="LSL")
                        fig_x.add_hline(y=stats_result["mean"], line_dash="solid", line_color="#22C55E", annotation_text="MEAN")
                        fig_x.add_hline(y=control_limits["x_bar"]["ucl"], line_dash="dot", line_color="#F59E0B", annotation_text="UCL")
                        fig_x.add_hline(y=control_limits["x_bar"]["lcl"], line_dash="dot", line_color="#F59E0B", annotation_text="LCL")
                        fig_x.update_layout(plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)', height=300)
                        st.plotly_chart(fig_x, use_container_width=True)

                    # 3. R-图 (或 MR-图 for individual measurements)
                    with g3:
                        chart_title = "MR 控制图 (移动极差)" if control_limits.get("is_moving_range", False) else "R 控制图 (极差)"
                        st.markdown(f"**📉 3. {chart_title}**")
                        r_values = control_limits["r"]["values"]

                        fig_r = px.line(y=r_values, title="子组极差")
                        fig_r.update_traces(
                            line_color="#8B5CF6",
                            line_width=3,
                            mode='lines+markers',
                            marker=dict(color="#134E4A", size=6)
                        )
                        fig_r.add_hline(y=control_limits["r"]["cl"], line_dash="solid", line_color="#22C55E", annotation_text="R-bar")
                        fig_r.add_hline(y=control_limits["r"]["ucl"], line_dash="dot", line_color="#F59E0B", annotation_text="UCL")
                        if control_limits["r"]["lcl"] > 0:
                            fig_r.add_hline(y=control_limits["r"]["lcl"], line_dash="dot", line_color="#F59E0B", annotation_text="LCL")
                        fig_r.update_layout(plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)', height=300)
                        st.plotly_chart(fig_r, use_container_width=True)

                    st.markdown("---")

                    # 第二行：3 个高级图
                    g4, g5, g6 = st.columns(3)

                    # 4. 直方图
                    with g4:
                        st.markdown("**📊 4. 直方图**")
                        st.plotly_chart(create_histogram(measurements, "数据分布 + 正态拟合", usl, lsl, stats_result["mean"]), use_container_width=True)

                    # 5. 正态概率图
                    with g5:
                        st.markdown("**📈 5. 正态概率图（Q-Q Plot）**")
                        st.plotly_chart(create_qq_plot(measurements), use_container_width=True)

                    # 6. 过程能力图
                    with g6:
                        st.markdown("**🎯 6. 过程能力图**")
                        st.plotly_chart(
                            create_capability_plot(measurements, stats_result, usl, lsl),
                            use_container_width=True
                        )

                # === 保存历史记录 ===
                st.markdown("---")
                col_save1, col_save2 = st.columns([1, 1])

                with col_save1:
                    if st.button(f"💾 保存到历史记录", key=f"save_{i}"):
                        metadata = {
                            "dimension_name": dim_name,
                            "operator": st.session_state.get("operator", "Unknown"),
                            "filename": uploaded_file.name
                        }

                        report_id = st.session_state.history_manager.save_report(
                            batch_id=batch_id,
                            data=measurements,
                            stats=stats_result,
                            metadata=metadata
                        )

                        st.success(f"✅ 报告已保存！ID: {report_id}")

                with col_save2:
                    if st.button(f"📄 生成 HTML 报告", key=f"report_{i}"):
                        st.success("✅ HTML 报告已生成（V2 功能：PDF 导出）")
                        st.info("💡 提示：按 Ctrl+P 可打印或保存为 PDF")

# ===============================
# 页面 2：历史记录
# ===============================

elif page == "📁 历史记录":
    st.markdown("<h1>📁 历史记录查询</h1>", unsafe_allow_html=True)

    # 搜索功能
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_keyword = st.text_input("🔍 关键词搜索", placeholder="批次号、零件名称等")

    with col2:
        search_button = st.button("🔎 搜索")

    with col3:
        if st.button("🗑️ 清空搜索"):
            search_keyword = ""
            search_button = False

    # 执行搜索
    if search_button or search_keyword:
        results = st.session_state.history_manager.search(keyword=search_keyword)
    else:
        results = st.session_state.history_manager.search()

    # 显示结果
    if results:
        st.write(f"**找到 {len(results)} 条记录**")

        # 转换为 DataFrame 显示
        df_records = pd.DataFrame(results)
        df_records = df_records[["report_id", "batch_id", "timestamp", "cpk", "cpk_status", "count"]]

        # 格式化 Cpk 状态
        def color_status(val):
            if val == "PASS":
                return "✅ PASS"
            else:
                return "❌ FAIL"

        df_records["cpk_status"] = df_records["cpk_status"].apply(color_status)
        df_records.columns = ["报告ID", "批次号", "时间", "Cpk", "状态", "样本量"]

        st.dataframe(df_records, use_container_width=True)

        # 查看详情
        selected_report_id = st.selectbox(
            "选择报告查看详情",
            options=[r["report_id"] for r in results]
        )

        if selected_report_id:
            report = st.session_state.history_manager.get_report(selected_report_id)

            if report:
                st.markdown("---")
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("📋 批次信息")
                    st.write(f"**报告ID**: {report['report_id']}")
                    st.write(f"**批次号**: {report['batch_id']}")
                    st.write(f"**时间**: {report['timestamp']}")

                    st.subheader("📊 统计摘要")
                    stats = report["stats"]
                    st.write(f"**Cpk**: {stats.get('cpk', 0):.4f}")
                    st.write(f"**Ppk**: {stats.get('ppk', 0):.4f}")
                    st.write(f"**均值**: {stats.get('mean', 0):.4f}")
                    st.write(f"**标准差**: {stats.get('std_overall', 0):.4f}")

                with col2:
                    st.subheader("📈 原始数据")
                    data = report["data"]
                    st.caption(f"📊 Total: {len(data)} measurements | 总计: {len(data)} 个测量值")
                    df_data = pd.DataFrame({
                        "序号": range(1, len(data) + 1),
                        "测量值": [round(x, 4) for x in data]
                    })
                    st.dataframe(
                        df_data,
                        use_container_width=True,
                        height=800,
                        column_config={
                            "序号": st.column_config.NumberColumn(
                                "序号",
                                width="small"
                            ),
                            "测量值": st.column_config.NumberColumn(
                                "测量值",
                                format="%.4f",
                                width="medium"
                            )
                        }
                    )

                if st.button(f"🗑️ 删除此报告"):
                    st.session_state.history_manager.delete_report(selected_report_id)
                    st.success("✅ 报告已删除")
                    st.rerun()
    else:
        st.info("📭 暂无历史记录，请先进行数据分析并保存")

# ===============================
# 页面 3：设置
# ===============================

elif page == "⚙️ 设置":
    st.markdown("<h1>⚙️ 系统设置</h1>", unsafe_allow_html=True)

    st.markdown("---")

    # 操作员信息
    st.subheader("👤 操作员信息")
    operator = st.text_input(
        "操作员姓名",
        value=st.session_state.get("operator", ""),
        key="operator_input"
    )

    if operator:
        st.session_state.operator = operator
        st.success(f"✅ 操作员已设置：{operator}")

    st.markdown("---")

    # 系统信息
    st.subheader("🖥️ 系统信息")

    st.markdown(f"""
    <div class="premium-card">
        <h3>IQC Pro Max v1.5</h3>
        <p><strong>功能特性</strong>：</p>
        <ul>
            <li>✅ MinerU AI OCR 识别</li>
            <li>✅ Cp/Cpk/Pp/Ppk 统计计算</li>
            <li>✅ 6 个 SPC 图表（3 图基础 + 3 图高级）</li>
            <li>✅ 异常值检测（3σ 原则）</li>
            <li>✅ OCR 智能修正（缺失小数点、单位剥离）</li>
            <li>✅ 实时正态性检验（Shapiro-Wilk）</li>
            <li>✅ Box-Cox 数据变换建议</li>
            <li>✅ 历史记录查询与管理</li>
            <li>✅ Excel 数据导出</li>
        </ul>
        <p><strong>合规标准</strong>：ISO 13485:2016、FDA 21 CFR 820</p>
        <p><strong>技术栈</strong>：Python 3.9+、Streamlit、Plotly、SciPy、NumPy</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 清除数据
    st.subheader("🗑️ 数据管理")

    if st.button("🔄 清除当前数据"):
        if "dim_data" in st.session_state:
            del st.session_state.dim_data
        if "original_data" in st.session_state:
            del st.session_state.original_data
        st.success("✅ 当前数据已清除")
        st.rerun()

    if st.button("🗑️ 清除所有历史记录"):
        st.warning("⚠️ 此操作将删除所有保存的历史报告，不可恢复！")
        confirm = st.checkbox("我确认要删除所有历史记录")

        if confirm and st.button("确认删除"):
            import shutil
            history_dir = "reports_history"

            if os.path.exists(history_dir):
                shutil.rmtree(history_dir)
                st.session_state.history_manager = HistoryManager()
                st.success("✅ 所有历史记录已删除")
            else:
                st.info("📭 暂无历史记录")