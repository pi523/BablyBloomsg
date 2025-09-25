import streamlit as st
import os
import requests
from datetime import datetime
import json

# 页面配置
st.set_page_config(
    page_title="BabyBloomSG AI助手",
    page_icon="🇸🇬",
    layout="wide"
)

st.title("🇸🇬 BabyBloomSG AI智能家庭政策助手")
st.markdown("**专业的新加坡家庭政策咨询AI，帮您规划美好未来！**")

# 侧边栏：API配置
st.sidebar.header("🔑 API配置")
qwen_api_key = st.sidebar.text_input("通义千问API Key", type="password", 
                                     help="从阿里云DashScope获取")
hf_token = st.sidebar.text_input("HuggingFace Token", type="password",
                                help="从HuggingFace获取")

# 用户信息
st.sidebar.header("👤 个人信息")
citizen = st.sidebar.selectbox("公民身份", ["新加坡公民", "PR", "外国人"])
income = st.sidebar.number_input("家庭月收入 (SGD)", min_value=0, value=5000)
children = st.sidebar.number_input("已有子女数", min_value=0, value=0)

# 政策知识库（简化版）
POLICY_KB = {
    'fertility': {
        'cash_gifts': {'1-2胎': 8000, '3-4胎': 10000, '5胎以上': 10000},
        'cda_matching': {'1-2胎': 3000, '3-6胎': 9000},
        'website': 'https://www.babybonus.msf.gov.sg'
    },
    'housing': {
        'bto_requirements': {
            '年龄': 21,
            '收入上限': {'2房': 7000, '3-5房': 14000}
        },
        'grants': {'家庭津贴': 80000, '首购津贴': 40000},
        'price_ranges': {
            '2房': [200000, 350000], '3房': [300000, 450000],
            '4房': [400000, 600000], '5房': [500000, 750000]
        }
    },
    'marriage': {
        'age_requirement': 21,
        'cost_range': [26, 42],
        'documents': ['身份证(NRIC/FIN)', '出生证明', '单身证明'],
        'website': 'https://www.rom.gov.sg'
    }
}

def get_exchange_rate():
    """获取实时汇率"""
    try:
        r = requests.get('https://api.exchangerate-api.com/v4/latest/SGD', timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                'USD': data['rates'].get('USD', 0.74),
                'CNY': data['rates'].get('CNY', 5.3),
                'MYR': data['rates'].get('MYR', 3.3)
            }
    except:
        pass
    return {'USD': 0.74, 'CNY': 5.3, 'MYR': 3.3}

def detect_intent(question):
    """简单的意图识别"""
    q = question.lower()
    if any(word in q for word in ['生育', '津贴', 'baby', '孩子', '怀孕']):
        return 'fertility'
    elif any(word in q for word in ['住房', 'bto', 'hdb', '房子']):
        return 'housing'  
    elif any(word in q for word in ['结婚', '婚姻', 'rom']):
        return 'marriage'
    return 'general'

def generate_response(question, intent, user_info):
    """生成政策回答"""
    rates = get_exchange_rate()
    citizen_status = user_info.get('citizen', True)
    income = user_info.get('income', 0)
    kids = user_info.get('children', 0)
    
    if intent == 'fertility':
        data = POLICY_KB['fertility']
        n = kids + 1  # 下一胎
        band = '1-2胎' if n <= 2 else ('3-4胎' if n <= 4 else '5胎以上')
        cash = data['cash_gifts'][band]
        cda = data['cda_matching']['1-2胎' if n <= 2 else '3-6胎']
        
        return f"""
💰 **新加坡生育津贴详情（预估第{n}胎）**

🎁 **现金奖励**: S${cash:,} (约¥{int(cash * rates['CNY']):,})
💳 **CDA配对**: S${cda:,}
📋 **申请条件**:
  • 孩子必须是新加坡公民
  • 出生后18个月内申请
  
🌐 **官方网站**: {data['website']}

{"✅ 您符合申请条件" if citizen_status else "❌ 需要公民身份才能申请"}
        """
        
    elif intent == 'housing':
        data = POLICY_KB['housing']
        req = data['bto_requirements']
        
        income_ok = income <= req['收入上限']['3-5房']
        citizen_ok = citizen_status
        
        return f"""
🏠 **HDB/BTO住房政策指南**

💰 **价格范围**:
  • 3房式: S${data['price_ranges']['3房'][0]:,} - S${data['price_ranges']['3房'][1]:,}
  • 4房式: S${data['price_ranges']['4房'][0]:,} - S${data['price_ranges']['4房'][1]:,}

✅ **资格检查** (基于您的信息):
  • 收入要求: {'✅' if income_ok else '❌'} (S${income:,} {'<=' if income_ok else '>'} S${req['收入上限']['3-5房']:,})
  • 公民身份: {'✅' if citizen_ok else '❌'}

💸 **可用津贴**:
  • 家庭津贴: S${data['grants']['家庭津贴']:,}
  • 首购津贴: S${data['grants']['首购津贴']:,}
        """
        
    elif intent == 'marriage':
        data = POLICY_KB['marriage']
        return f"""
💒 **新加坡结婚注册指南**

📋 **必需文件**:
{chr(10).join(f'  • {doc}' for doc in data['documents'])}

💰 **费用**: S${data['cost_range'][0]} - S${data['cost_range'][1]}
🌐 **官网**: {data['website']}
        """
    
    return "我正在学习更多政策知识，请尝试询问生育津贴、住房申请或结婚注册相关问题。"

def call_qwen_api(question, context, api_key):
    """调用通义千问API"""
    if not api_key:
        return "请先配置通义千问API密钥"
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-max",
        "messages": [
            {
                "role": "system", 
                "content": "你是BabyBloomSG，新加坡家庭政策专业AI助手。请基于提供的政策信息，用中文回答用户问题，语调温暖专业，使用emoji让回答更友好。"
            },
            {
                "role": "user",
                "content": f"政策背景信息：{context}\n\n用户问题：{question}"
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"API调用失败: {response.status_code}"
            
    except Exception as e:
        return f"网络错误: {str(e)}"

# 主界面
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！我是BabyBloomSG AI助手，专门帮助您了解新加坡的家庭政策。您可以问我关于生育津贴、住房申请、结婚注册等问题。"}
    ]

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # AI回复
    with st.chat_message("assistant"):
        with st.spinner("AI思考中..."):
            # 检测意图
            intent = detect_intent(prompt)
            
            # 构建用户信息
            user_info = {
                'citizen': citizen == "新加坡公民",
                'income': income,
                'children': children
            }
            
            # 生成基础回答
            basic_response = generate_response(prompt, intent, user_info)
            
            # 如果有API密钥，使用AI增强回答
            if qwen_api_key:
                ai_response = call_qwen_api(prompt, basic_response, qwen_api_key)
                final_response = ai_response
            else:
                final_response = basic_response + "\n\n💡 配置API密钥可获得更智能的回答"
            
            st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})

# 底部说明
st.markdown("---")
st.markdown("""
### 🚀 快速开始指南
1. **获取API密钥**: 访问 [阿里云DashScope](https://dashscope.console.aliyun.com/) 获取通义千问API密钥
2. **配置密钥**: 在左侧边栏输入API密钥
3. **个性化设置**: 填写您的基本信息获得定制建议
4. **开始咨询**: 询问任何新加坡家庭政策问题

### ⚠️ 重要提醒
所有政策信息仅供参考，请以新加坡政府官方最新公告为准。
""")