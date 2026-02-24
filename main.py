import streamlit as st
import secrets
import html
import logging
import re

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================

# 設定安全日誌：確保不記錄任何 PII (如玩家明文 ID 或真實 IP)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

# 初始化 Session State (確保單一瀏覽器視窗的狀態隔離)
if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

# ==========================================
# ⚙️ 核心邏輯模組
# ==========================================

def generate_secure_room_code() -> str:
    """使用密碼學安全的隨機數生成 6 碼房號，防禦房間枚舉攻擊"""
    # secrets.token_hex(3) 會產生 6 個字元的 Hex 字串，如 'A1B2C3'
    return secrets.token_hex(3).upper()

def validate_and_sanitize_id(raw_id: str) -> str:
    """嚴格的輸入驗證與過濾，防禦 XSS 與注入攻擊"""
    if not raw_id:
        return ""
    # 僅允許英數字與底線，長度限制 3~12 碼
    if not re.match(r"^[a-zA-Z0-9_]{3,12}$", raw_id):
        raise ValueError("玩家 ID 僅限 3~12 碼英數字與底線。")
    # HTML 轉義，確保即使繞過正則，也不會執行惡意腳本
    return html.escape(raw_id)

def create_room(player_id: str):
    """建立房間的伺服器端邏輯"""
    try:
        safe_id = validate_and_sanitize_id(player_id)
        room_code = generate_secure_room_code()
        
        # 狀態更新
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        
        # 安全日誌：去識別化記錄，僅顯示 ID 前兩碼，其餘遮蔽
        masked_id = safe_id[:2] + "****" if len(safe_id) > 2 else "****"
        logging.info(f"Room created: {room_code} by Player Hash/Mask: {masked_id}")
        
    except ValueError as e:
        st.error(str(e))

def join_room(room_code: str, player_id: str):
    """加入房間的伺服器端邏輯"""
    try:
        safe_id = validate_and_sanitize_id(player_id)
        # 基本的房號格式驗證，防止惡意負載
        if not re.match(r"^[A-F0-9]{6}$", room_code):
            raise ValueError("無效的房號格式。")
            
        # 狀態更新 (此處未來需與後端 Redis/DB 進行連線查驗)
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        
        masked_id = safe_id[:2] + "****" if len(safe_id) > 2 else "****"
        logging.info(f"Player {masked_id} joined Room: {room_code}")
        
    except ValueError as e:
        st.error(str(e))

# ==========================================
# 🖥️ Streamlit 前端渲染視圖
# ==========================================

def render_lobby():
    st.title("⚔️ 三國之巔：大廳")
    st.write("請建立新對戰房間，或輸入房號加入戰局。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("建立房間")
        create_id = st.text_input("輸入你的玩家 ID", key="create_id", help="限 3~12 碼英數字")
        if st.button("創建專屬房", use_container_width=True):
            if create_id:
                create_room(create_id)
                st.rerun()
            else:
                st.warning("請先輸入玩家 ID！")
                
    with col2:
        st.subheader("加入房間")
        join_code = st.text_input("輸入 6 碼房號", key="join_code").upper()
        join_id = st.text_input("輸入你的玩家 ID", key="join_id")
        if st.button("加入戰局", use_container_width=True):
            if join_code and join_id:
                join_room(join_code, join_id)
                st.rerun()
            else:
                st.warning("請完整填寫房號與玩家 ID！")

def render_room():
    st.title(f"🏰 房間：{st.session_state.current_room}")
    st.success(f"歡迎參戰，{st.session_state.player_id}！")
    st.write("等待其他玩家加入...(此處未來將實作陣營選擇與 AI 補位邏輯)")
    
    if st.button("離開房間", type="primary"):
        st.session_state.current_room = None
        st.session_state.player_id = None
        st.rerun()

# 路由控制
if st.session_state.current_room is None:
    render_lobby()
else:
    render_room()
