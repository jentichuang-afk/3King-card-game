import streamlit as st
import secrets
import html
import logging
import re
import pandas as pd

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
# 設定安全日誌：確保不記錄任何 PII (如玩家明文 ID 或真實 IP)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

# --- 1. 個人狀態隔離 (Session State) ---
if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

# --- 2. 伺服器全域記憶體 (Global State) ---
@st.cache_resource
def get_global_rooms():
    return {}

GLOBAL_ROOMS = get_global_rooms()

VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🗄️ 靜態遊戲資料 (伺服器端唯讀資料庫)
# ==========================================
FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇", "郭嘉", "典韋", "許褚", "荀彧", "夏侯淵", "曹丕", "曹仁", "賈詡", "徐晃", "張郃", "龐德"],
    "蜀": ["劉備", "關羽", "諸葛亮", "張飛", "趙雲", "馬超", "黃忠", "魏延", "龐統", "姜維", "法正", "黃月英", "馬岱", "關平", "劉禪"],
    "吳": ["孫權", "周瑜", "太史慈", "孫策", "陸遜", "呂蒙", "甘寧", "黃蓋", "凌統", "周泰", "魯肅", "孫尚香", "大喬", "小喬", "程普"],
    "其他": ["呂布", "董卓", "貂蟬", "袁紹", "華佗", "顏良", "文醜", "左慈", "公孫瓚", "袁術", "孟獲", "祝融", "張角", "盧植", "皇甫嵩"]
}

GENERALS_STATS = {
    # --- 魏國 ---
    "曹操": {"武力": 72, "智力": 91, "統帥": 96, "政治": 94, "魅力": 96, "運氣": 85},
    "張遼": {"武力": 92, "智力": 78, "統帥": 93, "政治": 58, "魅力": 77, "運氣": 80},
    "司馬懿": {"武力": 63, "智力": 96, "統帥": 98, "政治": 93, "魅力": 87, "運氣": 75},
    "夏侯惇": {"武力": 90, "智力": 60, "統帥": 85, "政治": 70, "魅力": 80, "運氣": 65},
    "郭嘉": {"武力": 15, "智力": 98, "統帥": 80, "政治": 85, "魅力": 75, "運氣": 40},
    "典韋": {"武力": 95, "智力": 35, "統帥": 55, "政治": 29, "魅力": 58, "運氣": 45},
    "許褚": {"武力": 96, "智力": 36, "統帥": 65, "政治": 20, "魅力": 60, "運氣": 60},
    "荀彧": {"武力": 14, "智力": 95, "統帥": 52, "政治": 98, "魅力": 89, "運氣": 70},
    "夏侯淵": {"武力": 91, "智力": 55, "統帥": 84, "政治": 61, "魅力": 78, "運氣": 50},
    "曹丕": {"武力": 71, "智力": 83, "統帥": 75, "政治": 86, "魅力": 85, "運氣": 80},
    "曹仁": {"武力": 86, "智力": 62, "統帥": 89, "政治": 52, "魅力": 76, "運氣": 70},
    "賈詡": {"武力": 48, "智力": 97, "統帥": 86, "政治": 85, "魅力": 53, "運氣": 88},
    "徐晃": {"武力": 90, "智力": 74, "統帥": 88, "政治": 48, "魅力": 71, "運氣": 70},
    "張郃": {"武力": 89, "智力": 69, "統帥": 90, "政治": 57, "魅力": 71, "運氣": 60},
    "龐德": {"武力": 94, "智力": 68, "統帥": 80, "政治": 42, "魅力": 70, "運氣": 40},
    # --- 蜀國 ---
    "劉備": {"武力": 73, "智力": 74, "統帥": 75, "政治": 78, "魅力": 99, "運氣": 95},
    "關羽": {"武力": 97, "智力": 75, "統帥": 95, "政治": 62, "魅力": 93, "運氣": 80},
    "諸葛亮": {"武力": 38, "智力": 100, "統帥": 98, "政治": 95, "魅力": 92, "運氣": 70},
    "張飛": {"武力": 98, "智力": 30, "統帥": 85, "政治": 22, "魅力": 50, "運氣": 60},
    "趙雲": {"武力": 96, "智力": 76, "統帥": 91, "政治": 65, "魅力": 90, "運氣": 85},
    "馬超": {"武力": 97, "智力": 44, "統帥": 88, "政治": 26, "魅力": 82, "運氣": 50},
    "黃忠": {"武力": 93, "智力": 60, "統帥": 86, "政治": 52, "魅力": 75, "運氣": 65},
    "魏延": {"武力": 92, "智力": 69, "統帥": 85, "政治": 46, "魅力": 53, "運氣": 45},
    "龐統": {"武力": 34, "智力": 97, "統帥": 86, "政治": 85, "魅力": 69, "運氣": 30},
    "姜維": {"武力": 89, "智力": 90, "統帥": 91, "政治": 67, "魅力": 80, "運氣": 40},
    "法正": {"武力": 47, "智力": 94, "統帥": 82, "政治": 78, "魅力": 55, "運氣": 60},
    "黃月英": {"武力": 28, "智力": 88, "統帥": 45, "政治": 75, "魅力": 40, "運氣": 60},
    "馬岱": {"武力": 84, "智力": 55, "統帥": 75, "政治": 42, "魅力": 68, "運氣": 70},
    "關平": {"武力": 82, "智力": 68, "統帥": 77, "政治": 60, "魅力": 75, "運氣": 60},
    "劉禪": {"武力": 5, "智力": 9, "統帥": 3, "政治": 12, "魅力": 56, "運氣": 100},
    # --- 吳國 ---
    "孫權": {"武力": 67, "智力": 80, "統帥": 76, "政治": 89, "魅力": 95, "運氣": 88},
    "周瑜": {"武力": 71, "智力": 96, "統帥": 97, "政治": 86, "魅力": 93, "運氣": 75},
    "太史慈": {"武力": 93, "智力": 66, "統帥": 82, "政治": 58, "魅力": 79, "運氣": 60},
    "孫策": {"武力": 92, "智力": 69, "統帥": 90, "政治": 70, "魅力": 90, "運氣": 50},
    "陸遜": {"武力": 69, "智力": 95, "統帥": 96, "政治": 87, "魅力": 85, "運氣": 80},
    "呂蒙": {"武力": 81, "智力": 89, "統帥": 91, "政治": 78, "魅力": 82, "運氣": 70},
    "甘寧": {"武力": 94, "智力": 76, "統帥": 86, "政治": 18, "魅力": 58, "運氣": 65},
    "黃蓋": {"武力": 83, "智力": 65, "統帥": 79, "政治": 50, "魅力": 75, "運氣": 70},
    "凌統": {"武力": 89, "智力": 60, "統帥": 77, "政治": 42, "魅力": 71, "運氣": 60},
    "周泰": {"武力": 91, "智力": 48, "統帥": 76, "政治": 38, "魅力": 61, "運氣": 80},
    "魯肅": {"武力": 43, "智力": 92, "統帥": 80, "政治": 93, "魅力": 89, "運氣": 85},
    "孫尚香": {"武力": 86, "智力": 70, "統帥": 72, "政治": 63, "魅力": 85, "運氣": 75},
    "大喬": {"武力": 11, "智力": 73, "統帥": 26, "政治": 60, "魅力": 92, "運氣": 60},
    "小喬": {"武力": 12, "智力": 74, "統帥": 28, "政治": 62, "魅力": 93, "運氣": 60},
    "程普": {"武力": 79, "智力": 74, "統帥": 84, "政治": 65, "魅力": 75, "運氣": 70},
    # --- 其他 ---
    "呂布": {"武力": 100, "智力": 26, "統帥": 87, "政治": 13, "魅力": 40, "運氣": 30},
    "董卓": {"武力": 87, "智力": 69, "統帥": 84, "政治": 59, "魅力": 35, "運氣": 40},
    "貂蟬": {"武力": 26, "智力": 81, "統帥": 20, "政治": 65, "魅力": 100, "運氣": 75},
    "袁紹": {"武力": 69, "智力": 70, "統帥": 80, "政治": 73, "魅力": 85, "運氣": 60},
    "華佗": {"武力": 15, "智力": 85, "統帥": 10, "政治": 40, "魅力": 90, "運氣": 50},
    "顏良": {"武力": 94, "智力": 42, "統帥": 81, "政治": 32, "魅力": 55, "運氣": 40},
    "文醜": {"武力": 93, "智力": 25, "統帥": 80, "政治": 28, "魅力": 50, "運氣": 40},
    "左慈": {"武力": 20, "智力": 94, "統帥": 15, "政治": 10, "魅力": 80, "運氣": 99},
    "公孫瓚": {"武力": 83, "智力": 60, "統帥": 82, "政治": 45, "魅力": 70, "運氣": 50},
    "袁術": {"武力": 65, "智力": 61, "統帥": 62, "政治": 15, "魅力": 39, "運氣": 30},
    "孟獲": {"武力": 87, "智力": 43, "統帥": 75, "政治": 30, "魅力": 68, "運氣": 70},
    "祝融": {"武力": 85, "智力": 29, "統帥": 68, "政治": 20, "魅力": 72, "運氣": 60},
    "張角": {"武力": 25, "智力": 86, "統帥": 89, "政治": 80, "魅力": 98, "運氣": 45},
    "盧植": {"武力": 64, "智力": 82, "統帥": 85, "政治": 84, "魅力": 81, "運氣": 60},
    "皇甫嵩": {"武力": 71, "智力": 75, "統帥": 87, "政治": 65, "魅力": 78, "運氣": 65}
}

def get_general_stats(name: str):
    default_stats = {"武力": 50, "智力": 50, "統帥": 50, "政治": 50, "魅力": 50, "運氣": 50}
    return GENERALS_STATS.get(name, default_stats)

# ==========================================
# ⚙️ 大廳與房間管理邏輯
# ==========================================
def generate_secure_room_code() -> str:
    return secrets.token_hex(3).upper()

def validate_and_sanitize_id(raw_id: str) -> str:
    if not raw_id: return ""
    if not re.match(r"^[a-zA-Z0-9_]{3,12}$", raw_id):
        raise ValueError("玩家 ID 僅限 3~12 碼英數字與底線。")
    return html.escape(raw_id)

def init_room_state(room_code: str):
    if room_code not in GLOBAL_ROOMS:
        GLOBAL_ROOMS[room_code] = {
            "players": {},         
            "ai_factions": [],     
            "status": "lobby",     
            "round": 1,            
            "decks": {},           
            "locked_cards": {},    
            "scores": {},          
            "last_chosen_attr": "",
            "last_round_results": {} 
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
        if room_code not in GLOBAL_ROOMS: raise ValueError("找不到該房間。")
        if GLOBAL_ROOMS[room_code]["status"] != "lobby": raise ValueError("房間已開戰，無法加入。")
            
        st.session_state.current_room = room_code
        st.session_state.player_id = safe_id
        logging.info(f"Player {safe_id[:2]}*** joined Room: {room_code}")
    except ValueError as e:
        st.error(str(e))

def assign_faction(room_code: str, player_id: str, requested_faction: str) -> bool:
    room = GLOBAL_ROOMS.get(room_code)
    if not room or room["status"] != "lobby": return False
    if requested_faction not in VALID_FACTIONS: return False
    taken = list(room["players"].values()) + room["ai_factions"]
    if requested_faction in taken: return False
    room["players"][player_id] = requested_faction
    return True

# ==========================================
# ⚔️ 遊戲核心邏輯 (伺服器端狀態權威)
# ==========================================
def fill_ai_factions_and_start(room_code: str):
    room = GLOBAL_ROOMS.get(room_code)
    if not room or room["status"] != "lobby": return

    taken_factions = list(room["players"].values())
    remaining_factions = [f for f in VALID_FACTIONS if f not in taken_factions]
    room["ai_factions"] = remaining_factions
    
    for pid, faction in room["players"].items():
        room["decks"][pid] = list(FACTION_ROSTERS[faction])
        room["scores"][pid] = 0
    for ai_fac in room["ai_factions"]:
        ai_id = f"AI_{ai_fac}"
        room["decks"][ai_id] = list(FACTION_ROSTERS[ai_fac])
        room["scores"][ai_id] = 0

    room["status"] = "playing" 
    logging.info(f"Room {room_code} locked. Decks dealt safely.")

def lock_in_cards(room_code: str, player_id: str, selected_cards: list):
    room = GLOBAL_ROOMS.get(room_code)
    if not room or room["status"] != "playing": return
    
    if len(selected_cards) != 3:
        st.error("必須選擇剛好 3 名武將！")
        return
        
    player_deck = room["decks"].get(player_id, [])
    if not all(card in player_deck for card in selected_cards):
        logging.warning(f"Tampering detected! {player_id[:2]}*** tried to play invalid cards.")
        st.error("檢測到異常出牌，請重新選擇！")
        return

    room["locked_cards"][player_id] = selected_cards
    logging.info(f"Player {player_id[:2]}*** locked in 3 cards securely.")
    
    import random
    for ai_fac in room["ai_factions"]:
        ai_id = f"AI_{ai_fac}"
        if ai_id not in room["locked_cards"]:
            ai_deck = room["decks"][ai_id]
            room["locked_cards"][ai_id] = random.sample(ai_deck, 3)

    total_factions = len(room["players"]) + len(room["ai_factions"])
    if len(room["locked_cards"]) == total_factions:
        room["status"] = "resolution_pending" 

def resolve_round(room_code: str):
    room = GLOBAL_ROOMS.get(room_code)
    if not room or room["status"] != "resolution_pending": return

    secure_rng = secrets.SystemRandom()
    attributes = ["武力", "智力", "統帥", "政治", "魅力", "運氣"]
    chosen_attr = secure_rng.choice(attributes)
    
    player_totals = {}
    for pid, cards in room["locked_cards"].items():
        total = sum(get_general_stats(card)[chosen_attr] for card in cards)
        player_totals[pid] = total
        
    sorted_players = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
    score_distribution = {0: 5, 1: 3, 2: 2, 3: 1}
    round_results = {}
    current_rank = 0
    
    for i in range(len(sorted_players)):
        pid, attr_total = sorted_players[i]
        if i > 0 and attr_total == sorted_players[i-1][1]:
            pass 
        else:
            current_rank = i
            
        points_earned = score_distribution.get(current_rank, 0)
        room["scores"][pid] += points_earned
        
        faction_name = room["players"].get(pid, pid.replace("AI_", ""))
        round_results[pid] = {
            "faction": faction_name, "cards": room["locked_cards"][pid],
            "attr_total": attr_total, "points_earned": points_earned, "rank": current_rank + 1
        }
        
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]

    room["last_chosen_attr"] = chosen_attr
    room["last_round_results"] = round_results
    room["status"] = "resolution_result" 
    logging.info(f"Room {room_code} Round {room['round']} resolved. Attr: {chosen_attr}")

def next_round_or_finish(room_code: str):
    room = GLOBAL_ROOMS.get(room_code)
    if not room or room["status"] != "resolution_result": return
    
    room["locked_cards"] = {}
    if room["round"] >= 5:
        room["status"] = "finished"
    else:
        room["round"] += 1
        room["status"] = "playing"

# ==========================================
# 🖥️ Streamlit 前端渲染視圖
# ==========================================

def render_lobby():
    """重新設計的安全大廳視圖，包含全域 ID 輸入與招募板"""
    st.title("⚔️ 三國之巔：大廳")
    
    # 1. 全域玩家身分設定
    st.markdown("### 👤 第一步：確認主公名號")
    player_id_input = st.text_input("請輸入你的玩家 ID (供本局連線使用)：", key="lobby_player_id", help="限 3~12 碼英數字")
    
    st.divider()

    # 2. 建立與私密加入區塊
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🛠️ 建立專屬房間")
        if st.button("創建新戰局", use_container_width=True):
            if player_id_input:
                create_room(player_id_input)
                st.rerun()
            else:
                st.warning("請先在上方輸入玩家 ID！")
                
    with col2:
        st.subheader("🔑 輸入房號加入")
        join_code = st.text_input("輸入 6 碼私密房號", key="join_code").upper()
        if st.button("加入指定戰局", use_container_width=True):
            if player_id_input and join_code:
                join_room(join_code, player_id_input)
                st.rerun()
            elif not player_id_input:
                st.warning("請先在上方輸入玩家 ID！")
            else:
                st.warning("請輸入房號！")

    st.divider()

    # 3. 公開招募板 (防護機制：僅顯示等待中狀態的房間)
    st.subheader("🟢 公開戰局招募板")
    st.write("點擊下方列表即可直接參戰，免去輸入房號的麻煩：")
    
    if st.button("🔄 刷新招募板"):
        st.rerun()

    # 濾出允許加入的房間
    available_rooms = {code: data for code, data in GLOBAL_ROOMS.items() if data["status"] == "lobby"}

    if not available_rooms:
        st.info("目前天下太平，沒有正在招募的公開房間。請自行創建一局！")
    else:
        for code, room_data in available_rooms.items():
            player_count = len(room_data["players"])
            
            # 資安：去識別化顯示房主名稱
            host_id = list(room_data["players"].keys())[0] if room_data["players"] else "空房"
            masked_host = f"{host_id[:2]}***" if len(host_id) > 2 else host_id

            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"**房間：`{code}`** | 👑 房主：{masked_host} | 👥 已加入：{player_count}/4 人")
            with col_btn:
                # 若滿員（實務上由陣營選擇管控，但可做基礎視覺防呆）
                if player_count >= 4:
                    st.button("房間已滿", disabled=True, key=f"full_{code}")
                else:
                    if st.button(f"⚔️ 點擊加入", key=f"join_btn_{code}", use_container_width=True):
                        if player_id_input:
                            join_room(code, player_id_input)
                            st.rerun()
                        else:
                            st.warning("請先在最上方輸入玩家 ID！")
            st.write("---")

def render_room():
    room_code = st.session_state.current_room
    player_id = st.session_state.player_id
    room = GLOBAL_ROOMS.get(room_code)
    
    if not room:
        st.error("房間狀態異常，請重新加入。"); st.session_state.current_room = None; st.rerun()

    st.title(f"🏰 房間：{room_code} | 第 {room.get('round', 1)}/5 回合")

    # --- 狀態 1：Lobby 佈陣準備 ---
    if room["status"] == "lobby":
        st.success(f"歡迎參戰，主公 {player_id}！")
        st.write("請選擇您的陣營：")
        
        st.write(f"👥 目前在房內的玩家人數：{len(room['players'])}")
        if st.button("🔄 刷新房間狀態"): st.rerun()
        
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
            if st.button("🔄 刷新戰局狀態", type="primary"): st.rerun()
        else:
            st.write("📊 **軍情處：可用武將能力一覽表** (可點擊欄位標題排序)")
            deck_data = []
            for name in player_deck:
                stats = get_general_stats(name)
                deck_data.append({
                    "武將名": name,
                    "武力": stats["武力"], "智力": stats["智力"], "統帥": stats["統帥"],
                    "政治": stats["政治"], "魅力": stats["魅力"], "運氣": stats["運氣"]
                })
            
            df = pd.DataFrame(deck_data)
            st.dataframe(df, hide_index=True, use_container_width=True)

            st.divider()
            selected = st.multiselect("👇 請從上方名單點選 3 名武將出戰：", options=player_deck, max_selections=3)
            
            if selected:
                st.write("⚔️ **目前選定出戰陣容：**")
                cols = st.columns(len(selected))
                for i, name in enumerate(selected):
                    stats = get_general_stats(name)
                    with cols[i]:
                        st.markdown(f"**{name}**")
                        st.code(f"武力:{stats['武力']:>3}  政治:{stats['政治']:>3}\n"
                                f"智力:{stats['智力']:>3}  魅力:{stats['魅力']:>3}\n"
                                f"統帥:{stats['統帥']:>3}  運氣:{stats['運氣']:>3}")
            
            if st.button("🔐 鎖定出戰陣容 (點擊後不可更改)", type="primary"):
                if len(selected) == 3:
                    lock_in_cards(room_code, player_id, selected); st.rerun()
                else:
                    st.warning("主公，必須精確點齊 3 名武將方可出征！")

    # --- 狀態 3：Resolution Pending 等待擲骰 ---
    elif room["status"] == "resolution_pending":
        st.success("🎉 所有陣營皆已出戰！")
        st.info("等待系統進行安全亂數擲骰與戰果結算...")
        if st.button("🎲 擲骰子並揭曉戰果 (伺服器端驗證)", type="primary"):
            resolve_round(room_code); st.rerun()

    # --- 狀態 4：Resolution Result 戰報揭曉 ---
    elif room["status"] == "resolution_result":
        st.title("⚔️ 戰報揭曉")
        chosen_attr = room["last_chosen_attr"]
        st.markdown(f"### 🎲 本回合比拼屬性：**【{chosen_attr}】**")
        
        results = room["last_round_results"]
        sorted_res = sorted(results.items(), key=lambda x: x[1]["rank"])
        
        st.subheader("📌 本回合戰果")
        for pid, res in sorted_res:
            is_me = (pid == player_id)
            bg_color = "🟢" if is_me else "⚪"
            st.write(f"#### {bg_color} 第 {res['rank']} 名：{res['faction']}陣營 (+{res['points_earned']} 分)")
            st.write(f"出戰武將：{', '.join(res['cards'])} ➔ **總和 {res['attr_total']}**")
            st.divider()
            
        st.subheader("📊 目前累積總分排名")
        current_scores = sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)
        
        score_data = []
        for rank, (pid, score) in enumerate(current_scores):
            faction = room["players"].get(pid, pid.replace("AI_", ""))
            medal = "🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "🎖️"
            is_me = (pid == player_id)
            marker = "🟢 (你)" if is_me else ""
            score_data.append({
                "排名": f"{medal} 第 {rank + 1} 名",
                "陣營": f"{faction}陣營 {marker}",
                "總分": int(score) 
            })
            
        st.dataframe(pd.DataFrame(score_data), hide_index=True, use_container_width=True)
        st.divider()
        
        if st.button("⏭️ 進入下一回合", type="primary", use_container_width=True):
            next_round_or_finish(room_code); st.rerun()

    # --- 狀態 5：Finished 遊戲結束 ---
    elif room["status"] == "finished":
        st.snow()
        st.title("🏆 戰局結束！天下大勢底定")
        st.subheader("📊 最終積分排行榜")
        
        final_scores = sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)
        for rank, (pid, score) in enumerate(final_scores):
            faction = room["players"].get(pid, pid.replace("AI_", ""))
            medal = "🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "🎖️"
            st.markdown(f"**{medal} {faction}陣營**：**{score}** 分")
            
        if st.button("🚪 離開房間並返回大廳"):
            st.session_state.current_room = None
            st.session_state.player_id = None
            st.rerun()

# ==========================================
# 🚀 應用程式主路由
# ==========================================
if st.session_state.current_room is None:
    render_lobby()
else:
    render_room()
