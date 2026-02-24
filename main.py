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

# 模擬伺服器端的全域房間狀態庫 (實務上應使用 Redis 或資料庫)
if 'global_rooms' not in st.session_state:
    st.session_state.global_rooms = {}

VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# ⚙️ 核心邏輯與狀態管理器
# ==========================================

def generate_secure_room_code() -> str:
    """使用密碼學安全的隨機數生成 6 碼房號，防禦房間枚舉攻擊"""
    return secrets.token_hex(3).upper()

def validate_and_sanitize_id(raw_id: str) -> str:
    """嚴格的輸入驗證與過濾，防禦 XSS 與注入攻擊"""
    if not raw_id:
        return ""
    if not re.match(r"^[a-zA-Z0-9_]{3,12}$", raw_id):
        raise ValueError("玩家 ID 僅限 3~12 碼英數字與底線。")
    return html.escape(raw_id)

def init_room_state(room_code: str):
    """安全初始化房間狀態，預設為封閉且空的安全狀態"""
    if room_code not in st.session_state.global_rooms:
        st.session_state.global_rooms[room_code] = {
            "players": {},       # { "player_id": "faction" }
            "ai_factions": [],   # 記錄由 AI 接管的陣營
            "status": "lobby"    # 狀態機：lobby -> playing -> finished
        }

def create_room(player_id: str):
    """建立房間的伺服器端邏輯"""
    try:
        safe_id = validate_and_sanitize_id(player_id)
        room_code = generate_secure_room_code()
        
        # 初始化伺服器端房間狀態
        init_room_state(room_code)
        
        # 更新客戶端狀態
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        
        masked_id = safe_id[:2] + "****" if len(safe_id) > 2 else "****"
        logging.info(f"Room created: {room_code} by Player: {masked_id}")
        
    except ValueError as e:
        st.error(str(e))

def join_room(room_code: str, player_id: str):
    """加入房間的伺服器端邏輯"""
    try:
        safe_id = validate_and_sanitize_id(player_id)
        if not re.match(r"^[A-F0-9]{6}$", room_code):
            raise ValueError("無效的房號格式。")
            
        # 驗證房間是否存在於伺服器中
        if room_code not in st.session_state.global_rooms:
            raise ValueError("找不到該房間，或房間已關閉。")
            
        # 驗證房間狀態是否允許加入
        if st.session_state.global_rooms[room_code]["status"] != "lobby":
            raise ValueError("該房間已開始遊戲，無法加入。")
            
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        
        masked_id = safe_id[:2] + "****" if len(safe_id) > 2 else "****"
        logging.info(f"Player {masked_id} joined Room: {room_code}")
        
    except ValueError as e:
        st.error(str(e))

def assign_faction(room_code: str, player_id: str, requested_faction: str) -> bool:
    """伺服器端陣營分配與驗證，防禦併發覆寫與越權佔用"""
    room = st.session_state.global_rooms.get(room_code)
    if not room or room["status"] != "lobby":
        return False
        
    if requested_faction not in VALID_FACTIONS:
        return False

    taken_factions = list(room["players"].values()) + room["ai_factions"]
    if requested_faction in taken_factions:
        return False

    room["players"][player_id] = requested_faction
    return True

def fill_ai_factions_and_start(room_code: str):
    """狀態流轉：關閉房間，AI 接管剩餘空位，進入遊戲狀態"""
    room = st.session_state.global_rooms.get(room_code)
    if not room or room["status"] != "lobby":
        return

    taken_factions = list(room["players"].values())
    remaining_factions = [f for f in VALID_FACTIONS if f not in taken_factions]
    
    room["ai_factions"] = remaining_factions
    room["status"] = "playing" # 狀態機推進，鎖定房間
    logging.info(f"Room {room_code} locked. AI took over: {remaining_factions}")

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
    room_code = st.session_state.current_room
    player_id = st.session_state.player_id
    room = st.session_state.global_rooms.get(room_code)
    
    st.title(f"🏰 房間：{room_code}")
    
    # 防禦性檢查：若伺服器端狀態遺失，強制踢回大廳
    if not room:
        st.error("房間狀態異常或已過期，請重新加入。")
        st.session_state.current_room = None
        if st.button("返回大廳"):
            st.rerun()
        return

    # --- 狀態 1：Lobby 佈陣準備 ---
    if room["status"] == "lobby":
        st.success(f"歡迎參戰，主公 {player_id}！")
        st.write("請選擇您的陣營：")
        
        cols = st.columns(4)
        for idx, faction in enumerate(VALID_FACTIONS):
            is_taken = faction in room["players"].values()
            taken_by = [p for p, f in room["players"].items() if f == faction]
            
            with cols[idx]:
                if is_taken:
                    display_name = taken_by[0] if taken_by[0] == player_id else f"{taken_by[0][:2]}***"
                    st.button(f"{faction}\n(已由 {display_name} 選擇)", disabled=True, key=f"btn_{faction}")
                else:
                    if st.button(f"選擇 {faction}", key=f"btn_{faction}"):
                        if assign_faction(room_code, player_id, faction):
                            st.rerun()
                        else:
                            st.error("該陣營已被搶走，請重新選擇！")
                            
        st.divider()
        col_start, col_leave = st.columns([3, 1])
        with col_start:
            # 必須有玩家選擇陣營才能開始
            can_start = len(room["players"]) > 0
            if st.button("🚀 準備完畢，讓 AI 接管剩餘空位並開始遊戲！", type="primary", disabled=not can_start):
                fill_ai_factions_and_start(room_code)
                st.rerun()
        with col_leave:
            if st.button("離開房間"):
                # 安全清除客戶端狀態，保留伺服器端歷史紀錄以供除錯
                st.session_state.current_room = None
                st.session_state.player_id = None
                st.rerun()

    # --- 狀態 2：Playing 遊戲進行中 ---
    elif room["status"] == "playing":
        st.success("遊戲已開始！進入暗選 3 張牌階段...")
        player_faction = room['players'].get(player_id)
        
        st.write(f"**你的陣營：** {player_faction if player_faction else '觀戰者'}")
        st.write(f"**玩家陣容：** {', '.join([f'{k[:2]}*** ({v})' for k,v in room['players'].items()])}")
        st.write(f"**AI 接管陣營：** {', '.join(room['ai_factions']) if room['ai_factions'] else '無'}")
        
        st.info("此處將實作：載入陣營武將資料與安全出牌邏輯。")
        
        # 暫時的離開按鈕供測試用
        if st.button("離開遊戲 (測試用)"):
            st.session_state.current_room = None
            st.rerun()

# ==========================================
# 🚀 應用程式主路由
# ==========================================
if st.session_state.current_room is None:
    render_lobby()
else:
    render_room()
