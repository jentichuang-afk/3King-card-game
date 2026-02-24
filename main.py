import streamlit as st
import secrets
import html
import logging
import re
import random

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None
if 'global_rooms' not in st.session_state:
    st.session_state.global_rooms = {}

VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🗄️ 靜態遊戲資料 (模擬安全唯讀的資料庫)
# ==========================================
# 每個陣營 15 人，共 60 人
FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇", "郭嘉", "典韋", "許褚", "荀彧", "夏侯淵", "曹丕", "曹仁", "賈詡", "徐晃", "張郃", "龐德"],
    "蜀": ["劉備", "關羽", "諸葛亮", "張飛", "趙雲", "馬超", "黃忠", "魏延", "龐統", "姜維", "法正", "黃月英", "馬岱", "關平", "劉禪"],
    "吳": ["孫權", "周瑜", "太史慈", "孫策", "陸遜", "呂蒙", "甘寧", "黃蓋", "凌統", "周泰", "魯肅", "孫尚香", "大喬", "小喬", "程普"],
    "其他": ["呂布", "董卓", "貂蟬", "袁紹", "華佗", "顏良", "文醜", "左慈", "公孫瓚", "袁術", "孟獲", "祝融", "張角", "盧植", "皇甫嵩"]
}

def get_general_stats(name: str):
    """模擬從資料庫安全讀取武將數值 (此處以隨機生成代替，實際應查表)"""
    # 使用 name 作為亂數種子，確保同一個武將的數值在遊戲中是固定的
    rng = random.Random(name) 
    return {
        "武力": rng.randint(40, 100), "智力": rng.randint(40, 100),
        "統帥": rng.randint(40, 100), "政治": rng.randint(40, 100),
        "魅力": rng.randint(40, 100), "運氣": rng.randint(40, 100)
    }

# ==========================================
# ⚙️ 核心邏輯與狀態管理器
# ==========================================

def generate_secure_room_code() -> str:
    return secrets.token_hex(3).upper()

def validate_and_sanitize_id(raw_id: str) -> str:
    if not raw_id: return ""
    if not re.match(r"^[a-zA-Z0-9_]{3,12}$", raw_id):
        raise ValueError("玩家 ID 僅限 3~12 碼英數字與底線。")
    return html.escape(raw_id)

def init_room_state(room_code: str):
    if room_code not in st.session_state.global_rooms:
        st.session_state.global_rooms[room_code] = {
            "players": {},         # { player_id: faction }
            "ai_factions": [],     # ["魏", "吳"...]
            "status": "lobby",     # lobby -> playing -> resolution -> finished
            "round": 1,            # 目前回合 (1~5)
            "decks": {},           # 每個玩家/AI 剩餘的可用武將 { id: [武將名...] }
            "locked_cards": {},    # 本回合暗選的 3 張牌 { id: [武將名...] }
            "scores": {}           # 總積分 { id: int }
        }

def create_room(player_id: str):
    try:
        safe_id = validate_and_sanitize_id(player_id)
        room_code = generate_secure_room_code()
        init_room_state(room_code)
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        logging.info(f"Room created: {room_code} by Player: {safe_id[:2]}***")
    except ValueError as e:
        st.error(str(e))

def join_room(room_code: str, player_id: str):
    try:
        safe_id = validate_and_sanitize_id(player_id)
        if not re.match(r"^[A-F0-9]{6}$", room_code): raise ValueError("無效的房號格式。")
        if room_code not in st.session_state.global_rooms: raise ValueError("找不到該房間。")
        if st.session_state.global_rooms[room_code]["status"] != "lobby": raise ValueError("房間已開戰。")
            
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        logging.info(f"Player {safe_id[:2]}*** joined Room: {room_code}")
    except ValueError as e:
        st.error(str(e))

def assign_faction(room_code: str, player_id: str, requested_faction: str) -> bool:
    room = st.session_state.global_rooms.get(room_code)
    if not room or room["status"] != "lobby": return False
    if requested_faction not in VALID_FACTIONS: return False
    taken = list(room["players"].values()) + room["ai_factions"]
    if requested_faction in taken: return False
    room["players"][player_id] = requested_faction
    return True

def fill_ai_factions_and_start(room_code: str):
    """狀態流轉：大廳 -> 遊戲開始，並進行安全發牌"""
    room = st.session_state.global_rooms.get(room_code)
    if not room or room["status"] != "lobby": return

    taken_factions = list(room["players"].values())
    remaining_factions = [f for f in VALID_FACTIONS if f not in taken_factions]
    room["ai_factions"] = remaining_factions
    
    # 1. 伺服器端安全發牌：初始化所有真人與 AI 的牌庫 (15 張)
    for pid, faction in room["players"].items():
        room["decks"][pid] = list(FACTION_ROSTERS[faction])
        room["scores"][pid] = 0
        
    for ai_fac in room["ai_factions"]:
        ai_id = f"AI_{ai_fac}"
        room["decks"][ai_id] = list(FACTION_ROSTERS[ai_fac])
        room["scores"][ai_id] = 0

    # 2. 狀態機推進至佈陣階段
    room["status"] = "playing" 
    logging.info(f"Room {room_code} locked. Decks dealt safely.")

def lock_in_cards(room_code: str, player_id: str, selected_cards: list):
    """伺服器端驗證出牌，防禦竄改與防偷看機制"""
    room = st.session_state.global_rooms.get(room_code)
    if not room or room["status"] != "playing": return
    
    # 防禦驗證 1：確保選了剛好 3 張
    if len(selected_cards) != 3:
        st.error("必須選擇剛好 3 名武將！")
        return
        
    # 防禦驗證 2：防重播與竄改 (確保這 3 張牌真的在玩家的剩餘牌庫中)
    player_deck = room["decks"].get(player_id, [])
    if not all(card in player_deck for card in selected_cards):
        logging.warning(f"Tampering detected! {player_id[:2]}*** tried to play invalid cards.")
        st.error("檢測到異常出牌，請重新選擇！")
        return

    # 安全寫入：存入 locked_cards，此時絕對不廣播給其他玩家
    room["locked_cards"][player_id] = selected_cards
    logging.info(f"Player {player_id[:2]}*** locked in 3 cards securely.")
    
    # AI 自動出牌邏輯 (若 AI 尚未出牌)
    for ai_fac in room["ai_factions"]:
        ai_id = f"AI_{ai_fac}"
        if ai_id not in room["locked_cards"]:
            import random
            ai_deck = room["decks"][ai_id]
            # AI 隨機選 3 張 (後續可升級為 LLM 決策)
            room["locked_cards"][ai_id] = random.sample(ai_deck, 3)

    # 檢查是否所有人(4個陣營)都已出牌
    total_factions = len(room["players"]) + len(room["ai_factions"])
    if len(room["locked_cards"]) == total_factions:
        room["status"] = "resolution" # 所有人準備完畢，進入結算擲骰子階段
        logging.info(f"Room {room_code} all locked. Entering resolution phase.")

# ==========================================
# 🖥️ Streamlit 前端渲染視圖
# ==========================================
# (render_lobby 保持與先前相同，此處略過以節省空間，請沿用上一版)
def render_lobby():
    st.title("⚔️ 三國之巔：大廳")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("建立房間")
        create_id = st.text_input("輸入你的玩家 ID", key="create_id")
        if st.button("創建專屬房"): create_room(create_id); st.rerun()
    with col2:
        st.subheader("加入房間")
        join_code = st.text_input("輸入 6 碼房號", key="join_code").upper()
        join_id = st.text_input("輸入你的玩家 ID", key="join_id")
        if st.button("加入戰局"): join_room(join_code, join_id); st.rerun()

def render_room():
    room_code = st.session_state.current_room
    player_id = st.session_state.player_id
    room = st.session_state.global_rooms.get(room_code)
    
    if not room:
        st.error("房間狀態異常，請重新加入。"); st.session_state.current_room = None; st.rerun()

    st.title(f"🏰 房間：{room_code} | 第 {room.get('round', 1)}/5 回合")

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
                    st.button(f"{faction}\n(已選擇)", disabled=True, key=f"btn_{faction}")
                else:
                    if st.button(f"選擇 {faction}", key=f"btn_{faction}"):
                        assign_faction(room_code, player_id, faction); st.rerun()
        st.divider()
        if st.button("🚀 所有人準備完畢，開始遊戲！", type="primary", disabled=len(room["players"])==0):
            fill_ai_factions_and_start(room_code); st.rerun()

    # --- 狀態 2：Playing 暗選出牌階段 ---
    elif room["status"] == "playing":
        player_faction = room['players'].get(player_id)
        player_deck = room['decks'].get(player_id, [])
        has_locked = player_id in room["locked_cards"]

        st.subheader(f"🛡️ 你的陣營：{player_faction} (剩餘 {len(player_deck)} 名武將)")
        
        if has_locked:
            st.info("🔒 你已鎖定本回合的 3 名武將！等待其他對手中...")
            # 安全設計：這裡絕對不顯示其他人出了什麼牌
            if st.button("🔄 刷新狀態", type="primary"): st.rerun()
        else:
            st.write("請從下方點選 3 名武將出戰：")
            # 使用 multiselect 讓玩家挑選
            selected = st.multiselect("選擇出戰武將 (限3名)", options=player_deck, max_selections=3)
            
            # 顯示選中武將的數值供玩家參考
            if selected:
                cols = st.columns(len(selected))
                for i, name in enumerate(selected):
                    stats = get_general_stats(name)
                    with cols[i]:
                        st.caption(f"**{name}**")
                        st.write(f"武:{stats['武力']} 智:{stats['智力']} 統:{stats['統帥']}")
            
            if st.button("🔐 鎖定出戰陣容 (點擊後不可更改)", type="primary"):
                if len(selected) == 3:
                    lock_in_cards(room_code, player_id, selected)
                    st.rerun()
                else:
                    st.warning("主公，必須精確點齊 3 名武將方可出征！")

    # --- 狀態 3：Resolution 結算階段 (待後續開發) ---
    elif room["status"] == "resolution":
        st.success("🎉 所有陣營皆已出牌！")
        st.info("請房主擲骰子以決定本回合比拼的屬性！(即將實作)")
        if st.button("測試：重置回合(開發用)"):
            room["status"] = "playing"
            room["locked_cards"] = {}
            st.rerun()

if st.session_state.current_room is None:
    render_lobby()
else:
    render_room()
