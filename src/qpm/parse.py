# -*- coding: utf-8 -*-
from lxml import etree as ET
import os
import sys
import xml.sax.saxutils as saxutils
import concurrent.futures
import copy
from functools import lru_cache
import time  # 添加在文件开头的import部分
from io import BytesIO
import gc
import configparser  # 添加configparser导入


# 设置SA.ini文件路径
SA_CONFIG_FILE = os.path.join(os.path.dirname(sys.argv[0]), "SA.ini")

# 预编译XPath表达式
XPATHS = {
    "current_frame": ET.XPath(".//Current_Frame"),
    "lux_index": ET.XPath("Lux_Index"),
    "average_luma": ET.XPath("Average_Luma"),
    "fps": ET.XPath("FPS"),
    "aecx_metering": ET.XPath(".//AECX_Metering"),
    "sat_ratio": ET.XPath("Sat_Ratio"),
    "dark_ratio": ET.XPath("Dark_Ratio"),
    "general_sas": ET.XPath(".//General_SAs"),
    "analyzer_name": ET.XPath("Analyzer_Name"),
    "analyzer_id": ET.XPath("Analyzer_ID"),
    "luma_component": ET.XPath(".//Luma_Component/Aggregated_Value/start"),
    "target_component_start": ET.XPath(".//Target_Component/Aggregated_Value/start"),
    "target_component_end": ET.XPath(".//Target_Component/Aggregated_Value/end"),
    "confidence_component": ET.XPath(".//Confidence_Component/Aggregated_Value/start"),
    "adjustment_ratio_start": ET.XPath(".//Adjustment_Ratio/start"),
    "adjustment_ratio_end": ET.XPath(".//Adjustment_Ratio/end"),
    "arithmetic_operators": ET.XPath("Arithmetic_Operators"),
    "output_db": ET.XPath(".//Output_DB"),
    "data_name": ET.XPath("dataName"),
    "operands": ET.XPath("Operands"),
    "operation_method": ET.XPath("Operation_Method"),
    "output_value": ET.XPath("Output_Value"),
    "awb_cct": ET.XPath('.//AWB_CurFrameDecision[@Index="1"]/CCT'),  # 新增的XPath
    "short_gain": ET.XPath('.//Exposure_Information[@Index="0"]/Gain'),
    "long_gain": ET.XPath('.//Exposure_Information[@Index="1"]/Gain'),
    "safe_gain": ET.XPath('.//Exposure_Information[@Index="2"]/Gain'),
    "channels_list_0": ET.XPath('.//AECX_CoreStats/Channels_List[@Index="0"]'),
    "channels_list_1": ET.XPath('.//AECX_CoreStats/Channels_List[@Index="1"]'),
    "channel_data": ET.XPath('Channel_Data[@ID="6"]'),
    "value_grid": ET.XPath("Value_Grid"),
    "r_gain": ET.XPath(
        './/Tuning_AWB_Data/AWB_Gains[@Index="0"]'
    ),  # 新增 r_gain 的XPath
    "b_gain": ET.XPath(
        './/Tuning_AWB_Data/AWB_Gains[@Index="2"]'
    ),  # 新增 b_gain 的XPath
    "triangle_index": ET.XPath(".//AWB_TriangleGainAdjust/Triangle_Index"),
    "awb_sagen1data": ET.XPath(".//AWB_SAGen1Data"),  # 添加AWB_SAGen1Data的XPath
    "sa_description": ET.XPath("./SA_Description"),  # 添加SA_Description的XPath
    "assist_data": ET.XPath(".//AWB_SA_Face_Assist/Face_Assist_Confidence"),
    "aec_settled": ET.XPath(".//AEC_Settled"),  # 添加对AEC_Settled的XPath
}

# 在文件开头添加模板定义
SA_TEMPLATE = ET.fromstring("""
<SA>
    <id/>
    <luma/>
    <target>
        <start/>
        <end/>
    </target>
    <confidence/>
    <adjratio>
        <start/>
        <end/>
    </adjratio>
    <step/>
</SA>
""")

OPERATOR_TEMPLATE = ET.fromstring("""
<operator>
    <operators_num/>
    <operators_method/>
</operator>
""")


@lru_cache(maxsize=128)
def get_sa_template():
    return ET.fromstring("""
    <SA>
        <id/>
        <luma/>
        <target>
            <start/>
            <end/>
        </target>
        <confidence/>
        <adjratio>
            <start/>
            <end/>
        </adjratio>
        <step/>
    </SA>
    """)


def parse_xml(file_path):
    """
    解析XML文件，处理可能的命名空间问题
    
    Args:
        file_path: XML文件路径
        
    Returns:
        lxml.etree._Element: 解析后的XML根节点
    """
    try:
        # 创建自定义的解析器
        parser = ET.XMLParser(recover=True, remove_blank_text=True, remove_comments=True)
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # 尝试移除所有命名空间声明
        content = content.replace(b'xmlns:', b'ignore_')
        content = content.replace(b'xmlns=', b'ignore=')
            
        # 使用修改后的内容和自定义解析器解析XML
        tree = ET.fromstring(content, parser=parser)
        
        return tree
    except Exception as e:
        print(f"Error parsing XML file {file_path}: {str(e)}")
        raise


def extract_values(root, path):
    element = root.find(path)
    return [child.text for child in element]


def extract_lux_values(root):
    lux = XPATHS["current_frame"](root)[0]
    lux_index = XPATHS["lux_index"](lux)[0].text
    ava_luma = XPATHS["average_luma"](lux)[0].text
    fps = XPATHS["fps"](lux)[0].text
    return lux_index, ava_luma, fps


def extract_sat_values(root):
    sat = XPATHS["aecx_metering"](root)[0]
    sat_ratio = XPATHS["sat_ratio"](sat)[0].text
    dark_ratio = XPATHS["dark_ratio"](sat)[0].text
    return sat_ratio, dark_ratio


def extract_SA_values(root, sa_name):
    general_sas = XPATHS["general_sas"](root)
    target_sa = None

    # 使用更高效的查找而不是循环所有SA
    for sa in general_sas:
        analyzer_name = XPATHS["analyzer_name"](sa)
        if analyzer_name and analyzer_name[0].text == sa_name:
            target_sa = sa
            break

    if target_sa is None:
        print(f"Error: Required SA {sa_name} not found")
        return None

    # 批量获取数据而不是多次调用XPath
    try:
        SA_name = XPATHS["analyzer_name"](target_sa)[0].text
        id = XPATHS["analyzer_id"](target_sa)[0].text
        luma = XPATHS["luma_component"](target_sa)[0].text
        target_start = XPATHS["target_component_start"](target_sa)[0].text
        target_end = XPATHS["target_component_end"](target_sa)[0].text
        confidence = XPATHS["confidence_component"](target_sa)[0].text
        adjratio_start = XPATHS["adjustment_ratio_start"](target_sa)[0].text
        adjratio_end = XPATHS["adjustment_ratio_end"](target_sa)[0].text
    except (IndexError, AttributeError):
        print(f"Error: Missing required data in {sa_name}")
        return None

    operators_name, calculations, operators_num, operators_method = [], [], [], []
    arithmetic_operators = XPATHS["arithmetic_operators"](target_sa)

    for operator in arithmetic_operators:
        output_db = XPATHS["output_db"](operator)
        if not output_db:
            continue

        output_db_name = XPATHS["data_name"](output_db[0])
        if not output_db_name or not output_db_name[0].text:
            break
            
        operands = [float(op.text) for op in XPATHS["operands"](operator)]
        operation_method = XPATHS["operation_method"](operator)[0].text
        output_value = XPATHS["output_value"](operator)[0].text

        calculation = calculate_operation(operands, operation_method, output_value)
        operators_name.append(output_db_name[0].text)
        calculations.append(calculation)
        operators_num.append(operands)
        operators_method.append(operation_method)
        
    # print(f"sa name:{SA_name},id:{id},luma:{luma},target start:{target_start},target end:{target_end},confidence:{confidence}")
    
    return (
        SA_name,
        id,
        luma,
        target_start,
      target_end,
        confidence,
        operators_name,
        adjratio_start,
        adjratio_end,
        calculations,
        operators_num,
        operators_method,
    )


def calculate_operation(operands, operation_method, output_value):
    if operation_method == "Division(3)":
        return f"{operands[0]} * {operands[1]} / {operands[2]} * {operands[3]} = {output_value}"
    elif operation_method == "Multiplication(2)":
        return f"{operands[0]} * {operands[1]} * {operands[2]} * {operands[3]} = {output_value}"
    elif operation_method == "Addition(0)":
        return f"{operands[0]} * {operands[1]} + {operands[2]} * {operands[3]} = {output_value}"
    elif operation_method == "Subtraction(1)":
        return f"{operands[0]} * {operands[1]} - {operands[2]} * {operands[3]} = {output_value}"
    elif operation_method == "Min(5)":
        return f"min({operands[0]} * {operands[1]}, {operands[2]} * {operands[3]}) = {output_value}"
    elif operation_method == "Max(4)":
        return f"max({operands[0]} * {operands[1]},{operands[2]} * {operands[3]}) = {output_value}"
    elif operation_method == "CondSmaller(13)":
        return f"({operands[0]} 小于 {operands[1]} ? {operands[2]} : {operands[3]}) = {cond_smaller(operands[0], operands[1], operands[2], operands[3])}"
    elif operation_method == "CondLarger(12)":
        return f"({operands[0]} 大于 {operands[1]} ? {operands[2]} : {operands[3]}) = {cond_larger(operands[0], operands[1], operands[2], operands[3])}"
    elif operation_method == "CondEqual(14)":
        return f"({operands[0]} 等于 {operands[1]} ? {operands[2]} : {operands[3]}) = {cond_equal(operands[0], operands[1], operands[2], operands[3])}"
    elif operation_method == "Largest(8)":
        return f"max({operands[0]},{operands[1]},{operands[2]},{operands[3]}) = {output_value}"
    elif operation_method == "Smallest(6)":
        return f"min({operands[0]},{operands[1]},{operands[2]},{operands[3]}) = {output_value}"
    else:
        return f"Unknown operation method: {operation_method}"


def cond_smaller(value, threshold, true_value, false_value):
    return true_value if value < threshold else false_value


def cond_larger(value, threshold, true_value, false_value):
    return true_value if value > threshold else false_value


def cond_equal(value, threshold, true_value, false_value):
    return true_value if value == threshold else false_value


def calculate_safe_exp_values(
    root,
    file_name_without_ext,
    file_path,
    **kwargs
):
    # 从配置文件加载SA配置
    required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

    # 创建SA值字典，用于之后查找
    sa_values_dict = {}

    # 从kwargs中提取所有SA值
    for sa_name in required_sas + optional_sas:
        param_name = f"{sa_name}_values"
        if param_name in kwargs:
            sa_values_dict[sa_name] = kwargs[param_name]

    # 检查必需的参数是否存在
    missing_required = [sa for sa in required_sas if sa not in sa_values_dict or sa_values_dict[sa] is None]
    if missing_required:
        raise ValueError(f"缺少必需的SA参数: {', '.join(missing_required)}")

    # 获取必需SA的值
    framesa_values = sa_values_dict.get("FrameSA")
    # SatPrevSA_values = sa_values_dict.get("SatPrevSA")
    # DarkPrevSA_values = sa_values_dict.get("DarkPrevSA")
    # BrightenImgSA_values = sa_values_dict.get("BrightenImgSA")
    # YHistSA_values = sa_values_dict.get("YHistSA")
    SafeAggSA_values = sa_values_dict.get("SafeAggSA")
    ShortAggSA_values = sa_values_dict.get("ShortAggSA")
    LongAggSA_values = sa_values_dict.get("LongAggSA")

    # 获取可选SA的值 (根据需要自行添加)
    FaceSA_values = sa_values_dict.get("FaceSA")
    ShortSatPrevSA_values = sa_values_dict.get("ShortSatPrevSA")
    LongDarkPrevSA_values = sa_values_dict.get("LongDarkPrevSA")

    # 解包FrameSA的值
    (
        FrameSA,
        Frame_id,
        Frame_luma,
        Frame_target_start,
        Frame_target_end,
        Frame_confidence,
        Frame_operators_name,
        Frame_adjratio_start,
        Frame_adjratio_end,
        Frame_calculations,
        Frame_operators_num,
        Frame_operators_method,
    ) = framesa_values

    # 解包其他必需SA的值，如果存在
    if SafeAggSA_values:
        SafeAgg_adjratio_start = SafeAggSA_values[7]
    else:
         raise ValueError("SafeAggSA is required") # Or handle missing case
    if ShortAggSA_values:
        ShortAgg_adjratio_start = ShortAggSA_values[7]
    else:
         raise ValueError("ShortAggSA is required") # Or handle missing case

    # 初始化 active_sa_list (此部分在您的示例中缺失，需要根据原始逻辑或新需求添加)
    # 例如，可以像之前一样添加 base_sa 和 optional_sa
    active_sa_list = []
    # (需要添加填充 active_sa_list 的逻辑)
    # 示例填充逻辑 (需要根据实际情况调整):
    base_sa_names = ["SatPrevSA", "DarkPrevSA", "BrightenImgSA"] # 示例
    for sa_name in base_sa_names:
         sa_value = sa_values_dict.get(sa_name)
         if sa_value is not None and len(sa_value) >= 9: # Check length
             active_sa_list.append((sa_value, sa_value[5], sa_value[7], sa_value[8], sa_name)) # confidence, start, end, name

    optional_sa_pairs = [] # Store optional SA pairs for later use in save_results_to_xml
    for sa_name in optional_sas:
        sa_value = sa_values_dict.get(sa_name)
        if sa_value is not None and len(sa_value) >= 9:
            optional_sa_pairs.append((sa_value, sa_name)) # Store pair
            if sa_name != "FaceSA": # Exclude FaceSA initially
                active_sa_list.append((sa_value, sa_value[5], sa_value[7], sa_value[8], sa_name))


    results_str = []
    result = []
    result_confidence = []
    name_list = []
    framesa_adjratio = float(Frame_adjratio_start) * float(Frame_confidence)
    framesa_adjratio = round(framesa_adjratio, 5)

    # 判断是否为人脸场景并获取FaceSA的值
    is_face_scene = False
    face_sa_values = None # Renamed to avoid conflict
    FaceSA_data = sa_values_dict.get("FaceSA") # Get FaceSA data using the correct key

    if (
        FaceSA_data is not None
        and isinstance(FaceSA_data, tuple)
        and len(FaceSA_data) >= 12
    ):
        try:
            face_confidence_val = float(FaceSA_data[5]) # Use a different variable name
            if face_confidence_val != 0:
                is_face_scene = True
                face_sa_values = FaceSA_data # Assign the actual data
        except (ValueError, TypeError) as e:
            print(f"Warning: Error processing FaceSA: {str(e)}")

    if is_face_scene and face_sa_values is not None:
        # 人脸场景逻辑
        face_confidence = float(face_sa_values[5])
        face_adjratio_start = float(face_sa_values[7])
        face_adjratio_end = float(face_sa_values[8])

        print("\n--- 人脸场景处理 ---")
        print(f"FaceSA Confidence: {face_confidence}, AdjRatio Start: {face_adjratio_start}, AdjRatio End: {face_adjratio_end}")

        # 先计算FaceSA的值
        name_list.append("FaceSA") # FaceSA 始终先添加
        # 使用 face_adjratio_start 进行计算 (根据您的代码片段)
        face_calc_value = face_confidence * face_adjratio_start
        face_cal_str = f"{face_confidence} * {face_adjratio_start} = {round(face_calc_value, 5)}"
        print(f"  - 添加 FaceSA 到计算: {face_cal_str}")
        results_str.append(face_cal_str)
        result.append(face_calc_value)
        result_confidence.append(face_confidence)

        # 遍历其他SA进计算（排除FaceSA）
        print("  - 遍历其他活动的SA (基于FaceSA区间):")
        for (
            sa_data, # Use sa_data to avoid confusion
            confidence,
            adjratio_start,
            adjratio_end,
            sa_name,
        ) in active_sa_list:
             print(f"    - 正在检查 SA: {sa_name}")
             # Basic checks (confidence > 0, adjratio non-negative)
             if float(confidence) == 0:
                 print(f"      - 跳过 {sa_name}: Confidence 为 0")
                 continue
             if float(adjratio_start) < 0 or float(adjratio_end) < 0:
                 print(f"      - 跳过 {sa_name}: AdjRatio 包含负值 ({adjratio_start}, {adjratio_end})")
                 continue

             # 人脸场景区间判断 (检查是否在 agg_sas 中)
             if sa_name in agg_sas:
                 if float(adjratio_start) >= face_adjratio_end:
                     print(f"        - {adjratio_start} >= {face_adjratio_end} 且 {sa_name} 在 agg_sas 中，使用 adjratio_start ({adjratio_start})")
                     if sa_name not in name_list: # 避免重复添加名称和值
                         name_list.append(sa_name)
                         calc_value = float(confidence) * float(adjratio_start)
                         cal_str = f"{confidence} * {adjratio_start} = {round(calc_value, 5)}"
                         results_str.append(cal_str)
                         result.append(calc_value)
                         result_confidence.append(float(confidence))
                 elif float(adjratio_end) <= face_adjratio_start:
                     print(f"        - {adjratio_end} <= {face_adjratio_start} 且 {sa_name} 在 agg_sas 中，使用 adjratio_end ({adjratio_end})")
                     if sa_name not in name_list: # 避免重复添加名称和值
                         name_list.append(sa_name)
                         calc_value = float(confidence) * float(adjratio_end)
                         cal_str = f"{confidence} * {adjratio_end} = {round(calc_value, 5)}"
                         results_str.append(cal_str)
                         result.append(calc_value)
                         result_confidence.append(float(confidence))
                 else:
                     print(f"        - {sa_name} 在 agg_sas 中但区间重叠，跳过")
             else:
                 print(f"      - 跳过 {sa_name}: 不在 agg_sas 列表中")

    else:
        # 无人脸场景逻辑
        print("\n--- 非人脸场景处理 ---")
        print(f"FrameSA Confidence: {Frame_confidence}, AdjRatio Start: {Frame_adjratio_start}, AdjRatio End: {Frame_adjratio_end}")
        print("  - 遍历活动的SA (基于FrameSA区间):")
        for (
            sa_data, # Use sa_data
            confidence,
            adjratio_start,
            adjratio_end,
            sa_name,
        ) in active_sa_list:
            print(f"    - 正在检查 SA: {sa_name}")
            # Basic checks
            if float(confidence) == 0:
                 print(f"      - 跳过 {sa_name}: Confidence 为 0")
                 continue
            if float(adjratio_start) < 0 or float(adjratio_end) < 0:
                 print(f"      - 跳过 {sa_name}: AdjRatio 包含负值 ({adjratio_start}, {adjratio_end})")
                 continue

            # 非人脸场景区间判断 (检查是否在 agg_sas 中)
            if sa_name in agg_sas:
                if float(adjratio_start) >= float(Frame_adjratio_end):
                    print(f"        - {adjratio_start} >= {Frame_adjratio_end} 且 {sa_name} 在 agg_sas 中，使用 adjratio_start ({adjratio_start})")
                    if sa_name not in name_list: # 避免重复添加名称和值
                        name_list.append(sa_name)
                        calc_value = float(confidence) * float(adjratio_start)
                        cal_str = f"{confidence} * {adjratio_start} = {round(calc_value, 5)}"
                        results_str.append(cal_str)
                        result.append(calc_value)
                        result_confidence.append(float(confidence))
                elif float(adjratio_end) <= float(Frame_adjratio_start):
                    print(f"        - {adjratio_end} <= {Frame_adjratio_start} 且 {sa_name} 在 agg_sas 中，使用 adjratio_end ({adjratio_end})")
                    if sa_name not in name_list: # 避免重复添加名称和值
                        name_list.append(sa_name)
                        calc_value = float(confidence) * float(adjratio_end)
                        cal_str = f"{confidence} * {adjratio_end} = {round(calc_value, 5)}"
                        results_str.append(cal_str)
                        result.append(calc_value)
                        result_confidence.append(float(confidence))
                else:
                     print(f"        - {sa_name} 在 agg_sas 中但区间重叠，跳过")
            else:
                 print(f"      - 跳过 {sa_name}: 不在 agg_sas 列表中")


    # --- 聚合计算逻辑 (FrameSA 始终参与) ---
    safe_agg_value_from_sa = round(float(SafeAgg_adjratio_start), 5) # 使用之前解包的值

    # 聚合计算 (可能包含FaceSA或其他SA, 且始终包含FrameSA)
    if is_face_scene:
        # 人脸场景: 聚合 result (含FaceSA) 和 result_confidence (含FaceSA), 再加上 FrameSA
        print("\n--- 聚合计算 (人脸 + FrameSA) ---")
        result_sum = sum(result) + framesa_adjratio # Add FrameSA contribution
        confidence_sum = sum(float(conf) for conf in result_confidence) + float(Frame_confidence) # Add FrameSA contribution
        contributing_sas_other = name_list # name_list contains FaceSA + others qualified
        contributing_sas_all_names = contributing_sas_other + ['FrameSA']
        
        if confidence_sum == 0:
                calculated_agg_ratio = 0 # Avoid division by zero
                print("警告: 人脸场景聚合 confidence 总和为 0")
        else:
                calculated_agg_ratio = result_sum / confidence_sum

        # Format the string to show all contributing SAs including FrameSA
        str_1 = f"adjratio({' + '.join(map(str, contributing_sas_all_names))})/confidence({' + '.join(map(str, contributing_sas_all_names))})"
        res_str = f"{str_1}=\n({' + '.join(map(lambda x: str(round(float(x), 5)), result))} + {round(framesa_adjratio, 5)}) / ({' + '.join(map(lambda x: str(round(float(x), 5)), result_confidence))} + {round(float(Frame_confidence), 5)}) = {safe_agg_value_from_sa}"

    else:
        # 非人脸场景: 聚合 result, result_confidence 并加上 FrameSA (逻辑不变)
        print("\n--- 聚合计算 (非人脸 + FrameSA) ---")
        result_sum = sum(result) + framesa_adjratio
        confidence_sum = sum(float(conf) for conf in result_confidence) + float(Frame_confidence)
        contributing_sas = name_list
        contributing_sas_all_names = contributing_sas + ['FrameSA']
        
        if confidence_sum == 0:
            calculated_agg_ratio = 0
            print("警告: 非人脸场景聚合 confidence 总和为 0")
        else:
            calculated_agg_ratio = result_sum / confidence_sum

        str_1 = f"adjratio({' + '.join(map(str, contributing_sas))} +FrameSA)/confidence({' + '.join(map(str, contributing_sas))} + FrameSA)"
        # Note: The string formatting for non-face case already included FrameSA correctly
        res_str = f"{str_1}=\n({' + '.join(map(lambda x: str(round(float(x), 5)), result))} + {round(framesa_adjratio, 5)}) / ({' + '.join(map(lambda x: str(round(float(x), 5)), result_confidence))} + {round(float(Frame_confidence), 5)}) = {safe_agg_value_from_sa}"


    # 获取ShortAgg和SafeAgg的adjratio值 (使用之前解包的值)
    short = float(ShortAgg_adjratio_start)
    safe = float(SafeAgg_adjratio_start) # This is the value reported by SafeAggSA

    print(f"ShortAgg AdjRatio Start: {short}, SafeAgg AdjRatio Start (Reported): {safe}")
    
    # DRC Gain Calculation: Use the reported SafeAgg value / ShortAgg value
    if short == 0:
        adrc_gain = 0 # Avoid division by zero
        print("警告: ShortAgg AdjRatio 为 0，DRC Gain 设为 0")
    else:
        adrc_gain = safe / short
        adrc_gain = round(adrc_gain, 2)
        
    adrc_gain_str = f"{safe} / {short} = {adrc_gain}"
    framesa_adjratio_str = (
        f"{Frame_adjratio_start} * {Frame_confidence} = {framesa_adjratio}"
    )

    # Extract lux and sat values using the passed root
    lux_values = extract_lux_values(root)
    sat_values = extract_sat_values(root)

    # 创建包含所有必需和有效可选SA的列表用于保存结果
    # (需要确保使用正确的变量名和检查)
    final_sa_values_for_xml = []
    all_sa_names_in_order = sa_order # Use order from config

    for sa_name in all_sa_names_in_order:
        sa_data = sa_values_dict.get(sa_name)
        if sa_data is not None and isinstance(sa_data, tuple):
             final_sa_values_for_xml.append(sa_data)
        # else: # Optional: Log missing SAs for the XML output list
        #     print(f"Info: SA '{sa_name}' from order config not found or invalid, skipping for XML output.")

    save_results_to_xml(
        root, # Pass the root element
        lux_values,
        sat_values,
        final_sa_values_for_xml, # Pass the ordered list
        framesa_adjratio_str,
        res_str,
        adrc_gain_str,
        file_name_without_ext,
        file_path,
        short, # Pass ShortAgg value
        safe,  # Pass SafeAgg value
    )


def save_results_to_xml(
    root, # Add root parameter
    lux_values,
    sat_values,
    sa_values,
    framesa_adjratio_str,
    res_str,
    adrc_gain_str,
    file_name_without_ext,
    file_path,
    short,
    safe,
):
    try:
        lux_index, ava_luma, fps = lux_values
        sat_ratio, dark_ratio = sat_values

        output_root = ET.Element("Analyzer") # Create a new root for the output XML

        # 减少重复的元素创建模式，使用函数
        def add_element(parent, name, value):
            elem = ET.SubElement(parent, name)
            elem.text = saxutils.escape(str(value))
            return elem

        # 添加基本信息
        add_element(output_root, "lux_index", lux_index)
        add_element(output_root, "ava_luma", ava_luma)
        add_element(output_root, "fps", fps)
        add_element(output_root, "sat_ratio", sat_ratio)
        add_element(output_root, "dark_ratio", dark_ratio)

        # 提取额外信息 - 使用传入的root
        # parsed_root = parse_xml(file_path) # Remove redundant parse

        # 提取并添加CCT和gain值
        cct_value = XPATHS["awb_cct"](root) # Use the passed root
        if cct_value:
            add_element(output_root, "CCT", cct_value[0].text)

        # 提取gain值
        short_gain = XPATHS["short_gain"](root) # Use the passed root
        if short_gain:
            add_element(output_root, "short_gain", short_gain[0].text)

        long_gain = XPATHS["long_gain"](root) # Use the passed root
        if long_gain:
            add_element(output_root, "long_gain", long_gain[0].text)

        safe_gain = XPATHS["safe_gain"](root) # Use the passed root
        if safe_gain:
            add_element(output_root, "safe_gain", safe_gain[0].text)

        # 提取并添加 r_gain 和 b_gain 值
        r_gain = XPATHS["r_gain"](root) # Use the passed root
        if r_gain:
            add_element(output_root, "r_gain", r_gain[0].text)

        b_gain = XPATHS["b_gain"](root) # Use the passed root
        if b_gain:
            add_element(output_root, "b_gain", b_gain[0].text)

        # 提取并添加AEC_Settled值
        aec_settled = XPATHS["aec_settled"](root) # Use the passed root
        if aec_settled and len(aec_settled) > 0:
            add_element(output_root, "aec_settled", aec_settled[0].text)

        triangle_index = XPATHS["triangle_index"](root) # Use the passed root
        if triangle_index:
            add_element(output_root, "triangle_index", triangle_index[0].text)

        # 从配置文件加载SA顺序
        _, _, sa_order, agg_sas = load_sa_config()

        # 添加SA信息
        sa_elem = ET.SubElement(output_root, "SA") # Append to the new root

        # 创建SA值的字典，方便查找
        sa_dict = {}
        for sa_value in sa_values:
            if isinstance(sa_value, tuple) and len(sa_value) >= 1:
                try:
                    SA_name = sa_value[0]
                    sa_dict[SA_name] = sa_value
                    # print(f"添加到sa_dict: {SA_name}")  # 调试信息
                except Exception as e:
                    print(f"Warning: Error processing SA value: {str(e)}")
                    continue

        # 打印字典中所有的SA名称
        # print(f"sa_dict中的所有SA: {', '.join(sa_dict.keys())}")

        # 按照定义的顺序添加SA
        for sa_name in sa_order:
            if sa_name in sa_dict:
                sa_value = sa_dict[sa_name]
                try:
                    (
                        SA_name,
                        id,
                        luma,
                        target_start,
                        target_end,
                        confidence,
                        operators_name,
                        adjratio_start,
                        adjratio_end,
                        calculations,
                        operators_num,
                        operators_method,
                    ) = sa_value

                    # print(f"正在写入SA: {SA_name}")  # 添加调试信息

                    # 使用模板创建SA元素
                    sa_item = copy.deepcopy(get_sa_template())
                    sa_item.tag = SA_name  # 修改标签名为SA名称

                    # 填充模板数据
                    sa_item.find("id").text = saxutils.escape(str(id))
                    sa_item.find("luma").text = saxutils.escape(str(luma))
                    sa_item.find("target/start").text = saxutils.escape(
                        str(target_start)
                    )
                    sa_item.find("target/end").text = saxutils.escape(str(target_end))
                    sa_item.find("confidence").text = saxutils.escape(str(confidence))
                    sa_item.find("adjratio/start").text = saxutils.escape(
                        str(adjratio_start)
                    )
                    sa_item.find("adjratio/end").text = saxutils.escape(
                        str(adjratio_end)
                    )

                    # 处理操作符
                    step_elem = sa_item.find("step")
                    if operators_name and calculations and operators_num and operators_method:
                        for op_name, calc, nums, method in zip(
                            operators_name, calculations, operators_num, operators_method
                        ):
                            op = copy.deepcopy(OPERATOR_TEMPLATE)
                            # 修改标签名称处理逻辑
                            op_tag = op_name
                            if str(op_name)[0].isdigit():
                                op_tag = f"op_{op_name}"
                            # 移除非法字符
                            op_tag = ''.join(c for c in op_tag if c.isalnum() or c in '_-')
                            op.tag = op_tag
                            op.find("operators_num").text = saxutils.escape(
                                ", ".join(map(str, nums))
                            )
                            op.find("operators_method").text = saxutils.escape(str(method))
                            op.text = saxutils.escape(str(calc))
                            step_elem.append(op)

                    sa_elem.append(sa_item)

                except Exception as e:
                    print(f"Warning: Error processing SA {sa_name}: {str(e)}")
                    continue

        # 添加计算结果
        frame_sa_elem = ET.SubElement(output_root, "FrameSA") # Append to the new root
        frame_sa_elem.text = str(framesa_adjratio_str)

        safe_agg_sa_adj_ratio_elem = ET.SubElement(output_root, "SafeAggSAAdjRatio") # Append to the new root
        safe_agg_sa_adj_ratio_elem.text = saxutils.escape(str(res_str))

        drc_gain_elem = ET.SubElement(output_root, "DRCgain") # Append to the new root
        drc_gain_elem.text = saxutils.escape(str(adrc_gain_str))

        short_elem = ET.SubElement(output_root, "Short") # Append to the new root
        short_elem.text = saxutils.escape(str(short))

        safe_elem = ET.SubElement(output_root, "Safe") # Append to the new root
        safe_elem.text = saxutils.escape(str(safe))

        # 从parsed_root中提取AWB SA描述并添加到输出XML - Use the passed root
        awb_descriptions = extract_awb_sa_descriptions(root)
        if awb_descriptions:
            awb_sa_elem = ET.SubElement(output_root, "awb_sa") # Append to the new root

            # 检查Face Assist数据 - Use the passed root
            face_assist_data = XPATHS["assist_data"](root)
            if (
                face_assist_data
                and len(face_assist_data) > 0
                and face_assist_data[0].text
            ):
                try:
                    face_assist_value = float(face_assist_data[0].text)
                    if face_assist_value != 0:
                        # 如果Face Assist数值不为零，添加FACE Assist到awb_sa中
                        awb_descriptions.append("FACE Assist")
                except (ValueError, TypeError):
                    pass  # 如果转换失败，则不添加FACE Assist

            awb_sa_elem.text = saxutils.escape(",".join(awb_descriptions))

        # 修改channel数据的写入方式 - Use the passed root
        channel_values = extract_channel_values(root)
        if channel_values:
            for channel_key, values in channel_values.items():
                channel_elem = ET.SubElement(output_root, channel_key) # Append to the new root
                # 将所有值转换为字符串并用逗号连接
                channel_elem.text = ",".join(map(str, values))

        # 使用内存写入优化写入速度
        buffer = BytesIO()
        tree = ET.ElementTree(output_root) # Use the new root
        tree.write(buffer, encoding="utf-8", pretty_print=True, xml_declaration=True)

        # 一次性写入文件
        output_file = os.path.join(
            os.path.dirname(file_path), f"{file_name_without_ext}_new.xml"
        )
        with open(output_file, "wb") as f:
            f.write(buffer.getvalue())

        print(f"Saved result to: {output_file}")

    except Exception as e:
        print(f"Error in save_results_to_xml: {str(e)}")
        raise


def parse_main(folder_path, log_callback=None):
    start_time = time.time()
    processed_files = 0
    total_files = 0

    # 从配置文件加载SA配置
    required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

    # 获取需要处理的文件列表
    file_list = [
        f
        for f in os.listdir(folder_path)
        if f.endswith(".xml") and not f.endswith("_new.xml")
    ]

    total_files = len(file_list)

    # 分批处理文件，减少内存占用
    batch_size = 50  # 根据系统性能调整批处理大小

    for batch_start in range(0, len(file_list), batch_size):
        batch_end = min(batch_start + batch_size, len(file_list))
        batch = file_list[batch_start:batch_end]

        # 使用有限的线程池处理批次
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    process_file,
                    os.path.join(folder_path, filename),
                    folder_path,
                    log_callback,
                ): filename
                for filename in batch
            }

            for future in concurrent.futures.as_completed(futures):
                filename = futures[future]
                try:
                    result = future.result()
                    if result:
                        processed_files += 1
                except Exception as e:
                    message = f"Error processing file {filename}: {str(e)}"
                    print(message)
                    if log_callback:
                        log_callback(message)

        # 在批次之间强制垃圾回收
        gc.collect()
    end_time = time.time()
    total_time = end_time - start_time
    speed = processed_files / total_time if total_time > 0 else 0

    print(f"\n处理完成 | 总文件: {total_files} | 成功处理: {processed_files}")
    print(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")

    if log_callback:
        log_callback(
            f"\n处理完成 | 总文件: {total_files} | 成功处理: {processed_files}"
        )
        log_callback(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")


def process_file(filename, folder_path, log_callback=None):
    if os.path.isdir(filename):
        return False

    file_name_without_ext = os.path.splitext(os.path.basename(filename))[0]

    # 检查是否存在对应的 _new.xml 文件
    new_xml_file = os.path.join(folder_path, f"{file_name_without_ext}_new.xml")
    if os.path.exists(new_xml_file):
        message = f"Skipping file: {filename} as {file_name_without_ext}_new.xml already exists."
        print(message)
        if log_callback:
            log_callback(message)
        return False

    message = f"Processing file: {filename}"
    if log_callback:
        log_callback(message)

    try:
        # 从配置文件加载SA配置
        required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

        # 减少在内存中保存的完整XML树
        root = None
        try:
            root = parse_xml(filename)

            # 提取并打印AWB_SAGen1Data中的SA_Description
            # awb_descriptions = extract_awb_sa_descriptions(root) # Moved to save_results_to_xml

            # Extract channel values early to ensure they're available
            # channel_values = extract_channel_values(root) # Moved to save_results_to_xml
            # if channel_values is None:
            #     message = f"Warning: Could not extract channel values from {filename}"
            #     print(message)
            #     if log_callback:
            #         log_callback(message)

        except Exception as e:
            message = f"Error: Could not parse XML file {filename}: {str(e)}"
            print(message)
            if log_callback:
                log_callback(message)
            return False

        sa_values = {}
        missing_required_sa = False

        # --- 处理 FrameSA 或 EVFrameSA 的备选逻辑 ---
        frame_sa_data = extract_SA_values(root, "FrameSA")
        if frame_sa_data:
            sa_values["FrameSA"] = frame_sa_data
            message = f"找到 FrameSA"
            print(message)
            if log_callback:
                log_callback(message)
        else:
            # 如果 FrameSA 未找到，尝试查找 EVFrameSA
            evframe_sa_data = extract_SA_values(root, "EVFrameSA")
            if evframe_sa_data:
                sa_values["FrameSA"] = evframe_sa_data
                message = f"未找到 FrameSA，使用 EVFrameSA 作为替代"
                print(message)
                if log_callback:
                    log_callback(message)
            else:
                # 如果 FrameSA 和 EVFrameSA 都未找到
                message = f"Error: 必需的 SA FrameSA 或 EVFrameSA 未找到"
                print(message)
                missing_required_sa = True
                if log_callback:
                    log_callback(message)

        if missing_required_sa:
            root = None
            gc.collect()
            return False
        # --- 结束 FrameSA 或 EVFrameSA 的备选逻辑 ---


        # 检查必需的SAs (跳过已处理的 FrameSA)
        for sa_name in required_sas:
            if sa_name == "FrameSA": # FrameSA 已在上面处理
                continue
            sa_value = extract_SA_values(root, sa_name)
            if sa_value is None:
                message = f"Error: Required SA {sa_name} not found"
                print(message)
                missing_required_sa = True
                break
            sa_values[sa_name] = sa_value

        if missing_required_sa:
            # Clear root reference to potentially free memory sooner
            root = None
            gc.collect()
            return False

        # 检查可选的SAs - 如果不存在则使用None值
        for sa_name in optional_sas:
            sa_value = extract_SA_values(root, sa_name)
            sa_values[sa_name] = sa_value  # 如果不存在就是None
            # if sa_name == "FaceDarkSA":
            #     print(f"FaceDarkSA提取结果: {sa_value is not None}")  # 调试信息

        # 确保所有必需的值都存在后再调用计算函数
        if all(key in sa_values for key in required_sas):
            try:
                # 创建参数字典
                sa_args = {
                    "root": root, # Pass the root element
                    "file_name_without_ext": file_name_without_ext,
                    "file_path": filename,
                }

                # 添加所有SA参数
                for sa_name in required_sas + optional_sas:
                    sa_args[f"{sa_name}_values"] = sa_values.get(sa_name)

                # 检查必要参数是否齐全
                missing_args = [arg for arg in ["root", "file_name_without_ext", "file_path"] if arg not in sa_args]
                if missing_args:
                    raise ValueError(f"缺少必要参数: {', '.join(missing_args)}")

                # 调用函数
                calculate_safe_exp_values(**sa_args)
            except Exception as e:
                message = f"Error in calculate_safe_exp_values: {str(e)}"
                print(message)
                # Clear root reference on error
                root = None
                gc.collect()
                return False
        else:
             # This case should ideally be caught by missing_required_sa check,
             # but added for robustness
             message = f"Error: Not all required SAs were found after extraction for file {filename}"
             print(message)
             # Clear root reference on error
             root = None
             gc.collect()
             return False


        # Clear root reference after successful processing
        root = None
        gc.collect()

        return True  # 处理成功
    except Exception as e:
        message = f"Error processing file {filename}: {str(e)}"
        if log_callback:
            log_callback(message)
        # Ensure root is cleared even for unexpected errors
        root = None
        gc.collect()
        return False


def extract_channel_values(root):
    """提取Index为0和1的Channels_List中Channel_Data的Value_Grid值（只提取前256个）"""
    try:
        # 创建字典存储不同Index的channel数据
        channel_data = {}

        # 提取Index=0的channel数据
        channel_0 = XPATHS["channels_list_0"](root)
        if channel_0:
            # 直接使用gridRGratio作为通道0的名称
            channel_data_0 = XPATHS["channel_data"](channel_0[0])
            if channel_data_0:
                value_grids_0 = XPATHS["value_grid"](channel_data_0[0])
                values_0 = []
                # 只提取前256个值
                for i, grid in enumerate(value_grids_0):
                    if i >= 256:  # 达到255个后停止
                        break
                    values_0.append(float(grid.text))
                channel_data["channel_0_gridRGratio"] = values_0  # 修改这里的名称

        # 提取Index=1的channel数据
        channel_1 = XPATHS["channels_list_1"](root)
        if channel_1:
            # 直接使用gridBGratio作为通道1的名称
            channel_data_1 = XPATHS["channel_data"](channel_1[0])
            if channel_data_1:
                value_grids_1 = XPATHS["value_grid"](channel_data_1[0])
                values_1 = []
                # 只提取前255个值
                for i, grid in enumerate(value_grids_1):
                    if i >= 255:  # 达到255个后停止
                        break
                    values_1.append(float(grid.text))
                channel_data["channel_1_gridBGratio"] = values_1  # 修改这里的名称

        return channel_data

    except Exception as e:
        print(f"Error extracting channel values: {str(e)}")
        return None


def extract_awb_sa_descriptions(root):
    """
    遍历AWB_SAGen1Data中所有SA_Description节点，打印非空的text值

    Args:
        root: XML根节点

    Returns:
        包含所有非空SA_Description的列表
    """
    descriptions = []

    # 使用XPath获取所有AWB_SAGen1Data节点
    sagen1data_nodes = XPATHS["awb_sagen1data"](root)

    if not sagen1data_nodes:
        print("未找到AWB_SAGen1Data节点")
        return descriptions

    print(f"找到 {len(sagen1data_nodes)} 个AWB_SAGen1Data节点")

    # 遍历每个AWB_SAGen1Data节点
    for i, node in enumerate(sagen1data_nodes):
        # 获取SA_Description子节点
        sa_desc_nodes = XPATHS["sa_description"](node)

        for desc in sa_desc_nodes:
            if desc is not None and desc.text and desc.text.strip():
                print(f"AWB_SAGen1Data[{i}] SA_Description: {desc.text.strip()}")
                descriptions.append(desc.text.strip())

    if not descriptions:
        print("未找到非空的SA_Description")

    return descriptions


def load_sa_config(config_file=SA_CONFIG_FILE):
    """
    从配置文件中读取SA相关的配置
    
    Args:
        config_file: 配置文件路径，默认为'SA.ini'
        
    Returns:
        tuple: (required_sas, optional_sas, sa_order, agg_sas)
    """
    config = configparser.ConfigParser()
    try:
        # 如果配置文件不存在，则使用默认配置
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件 {config_file} 不存在")
        
        # 显式指定使用UTF-8编码读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config.read_file(f)
        
        # 读取并分割配置项
        required_sas = config['SA_CONFIG']['required_sas'].strip().split(',')
        optional_sas = config['SA_CONFIG']['optional_sas'].strip().split(',')
        sa_order = config['SA_CONFIG']['sa_order'].strip().split(',')
        
        # 读取参与SafeAggSAAdjRatio计算的SA列表
        agg_sas = config['SA_CONFIG']['agg_sas'].strip().split(',')
        
        return required_sas, optional_sas, sa_order, agg_sas
    except Exception as e:
        print(f"Error reading config file {config_file}: {str(e)}")
        # 返回默认值
        return (
            ["FrameSA", "SatPrevSA", "DarkPrevSA", "BrightenImgSA", "YHistSA", "SafeAggSA", "ShortAggSA", "LongAggSA"],
            ["FaceSA", "ExtremeColorSA", "ShortSatPrevSA", "LongDarkPrevSA", "ADRCCapSA", "TouchSA", "FaceDarkSA", "IlluminanceSA", "AFBrktFlagSA"],
            ["FrameSA", "SatPrevSA", "DarkPrevSA", "BrightenImgSA", "FaceSA", "ExtremeColorSA", "ShortSatPrevSA", 
             "LongDarkPrevSA", "YHistSA", "TouchSA", "FaceDarkSA", "IlluminanceSA", "AFBrktFlagSA", "ADRCCapSA", "SafeAggSA", "ShortAggSA", "LongAggSA"],
            ["SatPrevSA", "DarkPrevSA", "BrightenImgSA", "FaceSA", "ExtremeColorSA", "FaceDarkSA"]
        )


if __name__ == "__main__":
    file_path = r"C:\Users\chenyang3\Downloads\11"
    parse_main(file_path)