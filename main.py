import streamlit as st
import secrets
import html
import logging
import re
import random
import pandas as pd  # 新增 pandas 以支援更強大的資料表排序功能

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
# 設定安全日誌：確保不記錄任何 PII (如玩家明文 ID 或真實 IP)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

# 初始化客戶端 Session State (確保單一瀏覽器視窗的狀態隔離)
if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

# 模擬伺服器端的全域房間狀態庫 (實務上應使用 Redis 或資料庫)
if 'global_rooms' not in st.session_state:
    st.session_state.global_rooms = {}

VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🗄️ 靜態遊戲資料 (模擬安全唯讀的資料庫)
# ==========================================
FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇", "郭嘉", "典韋", "許褚", "荀彧", "夏侯淵", "曹丕", "曹仁", "賈詡", "徐晃", "張郃", "龐德"],
    "蜀": ["劉備", "關羽", "諸葛亮", "張飛", "趙雲", "馬超", "黃忠", "魏延", "龐統", "姜維", "法正", "黃月英", "馬岱", "關平", "劉禪"],
    "吳": ["孫權", "周瑜", "太史慈", "孫策", "陸遜", "呂蒙", "甘寧", "黃蓋", "凌統", "周泰", "魯肅", "孫尚香", "大喬", "小喬", "程普"],
    "其他": ["呂布", "董卓", "貂蟬", "袁紹", "華佗", "顏良", "文醜", "左慈", "公孫瓚", "袁術", "孟獲", "祝融", "張角", "盧植", "皇甫嵩"]
}

def get_general_stats(name: str):
    """模擬從資料庫安全讀取武將數值。使用 name 作為亂數種子，確保數值固定防竄改"""
    rng = random.Random(name) 
    return {
        "武力": rng.randint(40, 100), "智力": rng.randint(40, 100),
        "統帥": rng.randint(40, 100), "政治": rng.randint(40, 100),
        "魅力": rng.randint(40, 100), "運氣": rng.randint(40, 100)
    }

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
    if room_code not in st.session_state.global_rooms:
        st.session_state.global_rooms[room_code] = {
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

# ==========================================
# ⚔️ 遊戲核心邏輯 (伺服器端狀態權威)
# ==========================================
def fill_ai_factions_and_start(room_code: str):
    room = st.session_state.global_rooms.get(room_code)
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
    room = st.session_state.global_rooms.get(room_code)
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
    
    for ai_fac in room["ai_factions"]:
        ai_id = f"AI_{ai_fac}"
        if ai_id not in room["locked_cards"]:
            ai_deck = room["decks"][ai_id]
            room["locked_cards"][ai_id] = random.sample(ai_deck, 3)

    total_factions = len(room["players"]) + len(room["ai_factions"])
    if len(room["locked_cards"]) == total_factions:
        room["status"] = "resolution_pending" 

def resolve_round(room_code: str):
    room = st.session_state.global_rooms.get(room_code)
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
    room = st.session_state.global_rooms.get(room_code)
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
                    display_name = taken_by[0] if taken_by[0] == player_id else f"{taken_by[0][:2]}***"
                    st.button(f"{faction}\n(已由 {display_name} 選擇)", disabled=True, key=f"btn_{faction}")
                else:
                    if st.button(f"選擇 {faction}", key=f"btn_{faction}"):
                        assign_faction(room_code, player_id, faction); st.rerun()
        st.divider()
        if st.button("🚀 所有人準備完畢，開始遊戲！", type="primary", disabled=len(room["players"])==0):
            fill_ai_factions_and_start(room_code); st.rerun()

    # --- 狀態 2：Playing 暗選出牌階段 (🛡️ 更新：加入 6 種屬性面板) ---
    elif room["status"] == "playing":
        player_faction = room['players'].get(player_id)
        player_deck = room['decks'].get(player_id, [])
        has_locked = player_id in room["locked_cards"]

        st.subheader(f"🛡️ 你的陣營：{player_faction} (剩餘 {len(player_deck)} 名武將)")
        
        if has_locked:
            st.info("🔒 你已鎖定本回合的 3 名武將！等待其他對手中...")
            if st.button("🔄 刷新狀態", type="primary"): st.rerun()
        else:
            # 建立唯讀的安全情報面板 (使用 DataFrame 讓玩家可以點擊表頭排序)
            st.write("📊 **軍情處：可用武將能力一覽表** (可點擊欄位標題排序)")
            deck_data = []
            for name in player_deck:
                stats = get_general_stats(name)
                deck_data.append({
                    "武將名": name,
                    "武力": stats["武力"], "智力": stats["智力"], "統帥": stats["統帥"],
                    "政治": stats["政治"], "魅力": stats["魅力"], "運氣": stats["運氣"]
                })
            
            # 渲染資料表
            df = pd.DataFrame(deck_data)
            st.dataframe(df, hide_index=True, use_container_width=True)

            # 選牌區
            st.divider()
            selected = st.multiselect("👇 請從上方名單點選 3 名武將出戰：", options=player_deck, max_selections=3)
            
            if selected:
                st.write("⚔️ **目前選定出戰陣容：**")
                cols = st.columns(len(selected))
                for i, name in enumerate(selected):
                    stats = get_general_stats(name)
                    with cols[i]:
                        st.markdown(f"**{name}**")
                        # 使用 st.code 讓數值對齊排版，更具科技感與儀表板風格
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
        
        for pid, res in sorted_res:
            is_me = (pid == player_id)
            bg_color = "🟢" if is_me else "⚪"
            st.write(f"#### {bg_color} 第 {res['rank']} 名：{res['faction']}陣營 (+{res['points_earned']} 分)")
            st.write(f"出戰武將：{', '.join(res['cards'])} ➔ **總和 {res['attr_total']}**")
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
            # 安全清除客戶端記憶體
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
