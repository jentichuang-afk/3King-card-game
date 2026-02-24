import streamlit as st
import secrets
import html
import logging
import re
import pandas as pd
import random
import json
import os
import google.generativeai as genai

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

# 安全載入 API Key (支援環境變數或 Streamlit Secrets)
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

if API_KEY:
    genai.configure(api_key=API_KEY)
    # 使用輕量且快速的模型，適合遊戲即時決策
    MODEL = genai.GenerativeModel('gemini-1.5-flash') 
else:
    MODEL = None
    logging.warning("未偵測到 GEMINI_API_KEY，AI 將採用預設隨機決策。")

# 個人狀態隔離 (Session State)
if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

# 伺服器全域記憶體 (Global State)
@st.cache_resource
def get_global_rooms():
    return {}

GLOBAL_ROOMS = get_global_rooms()

VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🗄️ 靜態遊戲資料與 AI 性格設定
# ==========================================
AI_PERSONALITIES = {
    "【神算子】": "優雅、從容、預判。說話語氣需展現高度智慧，對玩家保持禮貌但自信。請根據你手上的武將，挑選數值最平均、總和較高的3人。",
    "【霸道梟雄】": "狂傲、霸氣、壓制。說話語氣需狂妄、具備壓迫感，偶爾帶點挑釁，展現征服欲。請優先挑選你手上武力或統帥極高的3人。",
    "【守護之盾】": "謙遜、堅毅、溫厚。說話語氣需充滿正氣與堅韌感，對玩家表達敬意，強調防守與希望。請優先挑選政治、魅力或運氣較高的3人。"
}

FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇", "郭嘉", "典韋", "許褚", "荀彧", "夏侯淵", "曹丕", "曹仁", "賈詡", "徐晃", "張郃", "龐德"],
    "蜀": ["劉備", "關羽", "諸葛亮", "張飛", "趙雲", "馬超", "黃忠", "魏延", "龐統", "姜維", "法正", "黃月英", "馬岱", "關平", "劉禪"],
    "吳": ["孫權", "周瑜", "太史慈", "孫策", "陸遜", "呂蒙", "甘寧", "黃蓋", "凌統", "周泰", "魯肅", "孫尚香", "大喬", "小喬", "程普"],
    "其他": ["呂布", "張角", "董卓", "袁紹", "左慈", "賈詡", "陳宮", "馬騰", "貂蟬", "華佗", "孟獲", "祝融", "公孫瓚", "盧植", "皇甫嵩"]
}

GENERALS_STATS = {
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
    "劉備": {"武力": 75, "智力": 78, "統帥": 88, "政治": 85, "魅力": 99, "運氣": 95},
    "關羽": {"武力": 97, "智力": 75, "統帥": 95, "政治": 62, "魅力": 93, "運氣": 80},
    "諸葛亮": {"武力": 45, "智力": 100, "統帥": 98, "政治": 98, "魅力": 95, "運氣": 85},
    "張飛": {"武力": 98, "智力": 50, "統帥": 90, "政治": 35, "魅力": 65, "運氣": 65},
    "趙雲": {"武力": 96, "智力": 76, "統帥": 91, "政治": 65, "魅力": 90, "運氣": 85},
    "馬超": {"武力": 97, "智力": 52, "統帥": 91, "政治": 35, "魅力": 85, "運氣": 65},
    "黃忠": {"武力": 93, "智力": 60, "統帥": 86, "政治": 52, "魅力": 75, "運氣": 65},
    "魏延": {"武力": 94, "智力": 72, "統帥": 89, "政治": 50, "魅力": 55, "運氣": 50},
    "龐統": {"武力": 34, "智力": 97, "統帥": 86, "政治": 85, "魅力": 69, "運氣": 30},
    "姜維": {"武力": 91, "智力": 92, "統帥": 94, "政治": 80, "魅力": 85, "運氣": 65},
    "法正": {"武力": 52, "智力": 95, "統帥": 88, "政治": 82, "魅力": 60, "運氣": 75},
    "黃月英": {"武力": 35, "智力": 95, "統帥": 65, "政治": 88, "魅力": 75, "運氣": 70},
    "馬岱": {"武力": 85, "智力": 62, "統帥": 80, "政治": 50, "魅力": 72, "運氣": 80},
    "關平": {"武力": 84, "智力": 75, "統帥": 82, "政治": 65, "魅力": 80, "運氣": 70},
    "劉禪": {"武力": 25, "智力": 45, "統帥": 35, "政治": 55, "魅力": 75, "運氣": 100},
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
    "呂布": {"武力": 100, "智力": 38, "統帥": 94, "政治": 25, "魅力": 65, "運氣": 45},
    "張角": {"武力": 35, "智力": 92, "統帥": 91, "政治": 88, "魅力": 98, "運氣": 65},
    "董卓": {"武力": 87, "智力": 74, "統帥": 90, "政治": 68, "魅力": 45, "運氣": 50},
    "袁紹": {"武力": 72, "智力": 82, "統帥": 93, "政治": 88, "魅力": 92, "運氣": 70},
    "左慈": {"武力": 45, "智力": 98, "統帥": 60, "政治": 55, "魅力": 85, "運氣": 99},
    "陳宮": {"武力": 55, "智力": 92, "統帥": 85, "政治": 83, "魅力": 72, "運氣": 50},
    "馬騰": {"武力": 82, "智力": 65, "統帥": 84, "政治": 70, "魅力": 85, "運氣": 75},
    "貂蟬": {"武力": 30, "智力": 85, "統帥": 45, "政治": 82, "魅力": 100, "運氣": 80},
    "華佗": {"武力": 20, "智力": 90, "統帥": 35, "政治": 65, "魅力": 95, "運氣": 85},
    "孟獲": {"武力": 88, "智力": 55, "統帥": 82, "政治": 58, "魅力": 80, "運氣": 75},
    "祝融": {"武力": 87, "智力": 52, "統帥": 75, "政治": 45, "魅力": 85, "運氣": 65},
    "公孫瓚": {"武力": 86, "智力": 68, "統帥": 86, "政治": 60, "魅力": 78, "運氣": 65},
    "盧植": {"武力": 70, "智力": 85, "統帥": 90, "政治": 88, "魅力": 88, "運氣": 75},
    "皇甫嵩": {"武力": 75, "智力": 78, "統帥": 95, "政治": 75, "魅力": 82, "運氣": 80},
    "賈詡": {"武力": 48, "智力": 97, "統帥": 88, "政治": 85, "魅力": 60, "運氣": 90}
}

def get_general_stats(name: str):
    return GENERALS_STATS.get(name, {"武力": 50, "智力": 50, "統帥": 50, "政治": 50, "魅力": 50, "運氣": 50})

# ==========================================
# 📡 系統偵錯：API 連線測試
# ==========================================
def check_api_status():
    """發送最輕量的請求，用以診斷 Gemini API 是否連線成功"""
    if not MODEL:
        return False, "API 金鑰未設定 (API_KEY is missing or undefined)。請檢查 Secrets 設定。"
    try:
        # 發送極短 prompt 以測試通訊
        response = MODEL.generate_content("這是一個連線測試，請直接回覆『OK』。")
        if response.text:
            return True, f"連線成功！Gemini API 回應正常。(回應內容: {response.text.strip()})"
    except Exception as e:
        return False, f"連線失敗，錯誤代碼或原因：{str(e)}"

# ==========================================
# 🧠 AI 決策引擎 (Gemini API 整合)
# ==========================================
def get_ai_decision(ai_id: str, available_cards: list, round_num: int, personality_name: str) -> tuple:
    fallback_cards = random.sample(available_cards, 3)
    fallback_quote = f"吾乃{personality_name}，且看我這回合的排兵布陣！"

    if not MODEL:
        return fallback_cards, fallback_quote

    personality_desc = AI_PERSONALITIES.get(personality_name, "")
    prompt = f"""
    你是一個三國卡牌對戰遊戲的AI玩家。
    你的性格設定是：{personality_name} - {personality_desc}
    目前是遊戲的第 {round_num}/5 回合。
    你目前手上剩餘可用的武將牌庫為（共{len(available_cards)}名）：{available_cards}。
    
    任務：
    1. 從上述牌庫中，挑選出「剛好 3 名」武將出戰。
    2. 根據你的性格，說出一句出牌時的霸氣台詞或謀略之語（限 30 字以內）。
    
    警告：你必須嚴格以純 JSON 格式回傳，不可包含 Markdown 標記 (如 ```json)，格式必須完全一致：
    {{"selected_cards": ["武將A", "武將B", "武將C"], "quote": "你的台詞"}}
    """

    try:
        response = MODEL.generate_content(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3].strip()

        data = json.loads(raw_text)
        selected = data.get("selected_cards", [])
        quote = data.get("quote", fallback_quote)

        if len(selected) == 3 and all(card in available_cards for card in selected):
            return selected, quote
        else:
            logging.warning(f"[Security/Logic] AI {ai_id} 選牌無效: {selected}。觸發回退機制。")
            return fallback_cards, fallback_quote + "（哼，看我隨機應變！）"
    except Exception as e:
        logging.error(f"[System] AI {ai_id} API 呼叫失敗: {e}。觸發回退機制。")
        return fallback_cards, fallback_quote + "（訊號干擾，但我等絕不退縮！）"

# ==========================================
# ⚙️ 核心系統功能 (大廳、房間、戰鬥)
# ==========================================
def validate_id(raw_id: str) -> str:
    if not raw_id: return ""
    if not re.match(r"^[a-zA-Z0-9_]{3,12}$", raw_id): raise ValueError("ID 限 3~12 碼英數字")
    return html.escape(raw_id)

def init_room(code: str):
    if code not in GLOBAL_ROOMS:
        GLOBAL_ROOMS[code] = {
            "players": {}, "ai_factions": [], "status": "lobby", "round": 1,
            "decks": {}, "locked_cards": {}, "scores": {}, "last_attr": "", "results": {},
            "ai_personalities": {}, "ai_quotes": {}
        }

def assign_faction(code: str, pid: str, faction: str):
    room = GLOBAL_ROOMS.get(code)
    taken = list(room["players"].values()) + room["ai_factions"]
    if faction not in taken: room["players"][pid] = faction

def start_game(code: str):
    room = GLOBAL_ROOMS.get(code)
    taken = list(room["players"].values())
    room["ai_factions"] = [f for f in VALID_FACTIONS if f not in taken]
    for pid, f in room["players"].items():
        room["decks"][pid], room["scores"][pid] = list(FACTION_ROSTERS[f]), 0
    available_personalities = list(AI_PERSONALITIES.keys())
    for af in room["ai_factions"]:
        ai_id = f"AI_{af}"
        room["decks"][ai_id], room["scores"][ai_id] = list(FACTION_ROSTERS[af]), 0
        room["ai_personalities"][ai_id] = random.choice(available_personalities)
    room["status"] = "playing"

def lock_cards(code: str, pid: str, cards: list):
    room = GLOBAL_ROOMS.get(code)
    room["locked_cards"][pid] = cards
    for af in room["ai_factions"]:
        ai_id = f"AI_{af}"
        if ai_id not in room["locked_cards"]:
            ai_deck = room["decks"][ai_id]
            personality = room["ai_personalities"][ai_id]
            sel_cards, quote = get_ai_decision(ai_id, ai_deck, room["round"], personality)
            room["locked_cards"][ai_id] = sel_cards
            room["ai_quotes"][ai_id] = quote
    if len(room["locked_cards"]) == 4: 
        room["status"] = "resolution_pending"

def resolve_round(code: str):
    room = GLOBAL_ROOMS.get(code)
    attr = secrets.SystemRandom().choice(["武力", "智力", "統帥", "政治", "魅力", "運氣"])
    totals = {pid: sum(get_general_stats(c)[attr] for c in cards) for pid, cards in room["locked_cards"].items()}
    sorted_p = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    ranks, cur_r = {}, 0
    for i, (pid, tot) in enumerate(sorted_p):
        if i > 0 and tot < sorted_p[i-1][1]: cur_r = i
        pts = {0:5, 1:3, 2:2, 3:1}.get(cur_r, 0)
        room["scores"][pid] += pts
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]
        faction_name = room["players"].get(pid, pid.replace("AI_",""))
        ranks[pid] = {
            "faction": faction_name, "cards": room["locked_cards"][pid], 
            "total": tot, "pts": pts, "rank": cur_r+1, "is_ai": pid.startswith("AI_"),
            "personality": room["ai_personalities"].get(pid, ""),
            "quote": room["ai_quotes"].get(pid, "")
        }
    room.update({"last_attr": attr, "results": ranks, "status": "resolution_result"})

def next_round_or_finish(code: str):
    room = GLOBAL_ROOMS.get(code)
    room["locked_cards"], room["ai_quotes"] = {}, {}
    if room["round"] >= 5: room["status"] = "finished"
    else:
        room["round"] += 1
        room["status"] = "playing"

# ==========================================
# 🖥️ Streamlit 渲染視圖
# ==========================================
def render_lobby():
    st.title("⚔️ 三國之巔：大廳")
    
    pid_input = st.text_input("👤 主公名號：", key="pid_in")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️ 建立戰局"):
            try:
                st.session_state.player_id = validate_id(pid_input)
                code = secrets.token_hex(3).upper()
                init_room(code); st.session_state.current_room = code; st.rerun()
            except ValueError as e: st.error(e)
            
    st.divider()
    st.subheader("🟢 公開招募板")
    rooms = {c: d for c, d in GLOBAL_ROOMS.items() if d["status"] == "lobby"}
    if not rooms: st.info("目前無戰局")
    for c, d in rooms.items():
        if st.button(f"⚔️ 加入房間 {c} ({len(d['players'])}/4)", key=c):
            try:
                st.session_state.player_id = validate_id(pid_input)
                st.session_state.current_room = c; d["players"][st.session_state.player_id] = ""; st.rerun()
            except ValueError as e: st.error(e)
            
    st.divider()
    # 📡 新增：API 連線狀態診斷區塊
    with st.expander("📡 系統與 API 連線診斷 (開發者工具)"):
        st.write("點擊下方按鈕測試 Gemini API 是否能正常通訊。如果對戰中出現「訊號干擾」，可在此確認連線狀態。")
        if st.button("🔌 測試 API 連線狀態", type="secondary"):
            with st.spinner("正在呼叫 Gemini API..."):
                is_ok, msg = check_api_status()
                if is_ok:
                    st.success(msg)
                else:
                    st.error(msg)
                    st.info("💡 提示：請檢查 Streamlit Cloud 的 Advanced Settings -> Secrets 是否正確設定了 `GEMINI_API_KEY`。")

def render_room():
    code, pid = st.session_state.current_room, st.session_state.player_id
    room = GLOBAL_ROOMS.get(code)
    
    if not room:
        st.error("房間狀態異常，請重新加入。"); st.session_state.current_room = None; st.rerun()
        return

    st.title(f"🏰 房間：{code} | 第 {room['round']}/5 回合")

    if room["status"] == "lobby":
        st.write("🚩 請選擇陣營：")
        cols = st.columns(4)
        for i, f in enumerate(VALID_FACTIONS):
            taken = f in room["players"].values() or f in room["ai_factions"]
            if cols[i].button(f"{f}" + (" (已選)" if taken else ""), disabled=taken):
                assign_faction(code, pid, f); st.rerun()
        if st.button("🚀 開始遊戲", type="primary"): start_game(code); st.rerun()

    elif room["status"] == "playing":
        if pid in room["locked_cards"]: 
            st.info("🔒 已鎖定陣容，等待對手中..."); st.button("🔄 刷新")
        else:
            deck = room["decks"][pid]
            df = pd.DataFrame([{"名": n, **get_general_stats(n)} for n in deck])
            st.write("📊 **軍情處：請直接勾選下方表格，點選 3 名出戰武將**")
            event = st.dataframe(df, on_select="rerun", selection_mode="multi-row", hide_index=True, use_container_width=True)
            sel_idx = event.selection.rows
            
            if len(sel_idx) == 3:
                selected_names = df.iloc[sel_idx]["名"].tolist()
                st.success(f"⚔️ 已選定出戰：{', '.join(selected_names)}")
                if st.button("🔐 鎖定出戰 (AI 將同步進行決策)", type="primary"):
                    with st.spinner("傳令兵正在通知其他陣營..."):
                        lock_cards(code, pid, selected_names)
                    st.rerun()
            elif len(sel_idx) > 3: 
                st.error(f"⚠️ 只能選擇 3 名武將！您目前選擇了 {len(sel_idx)} 名。")
            else: 
                st.warning(f"請在上方表格精確勾選 3 位武將 (目前 {len(sel_idx)}/3)")

    elif room["status"] == "resolution_pending":
        if st.button("🎲 擲骰子結算", type="primary"): resolve_round(code); st.rerun()

    elif room["status"] == "resolution_result":
        st.header(f"🎲 比拼屬性：【{room['last_attr']}】")
        
        st.subheader("📌 本回合戰果與謀士語錄")
        for p, r in sorted(room["results"].items(), key=lambda x: x[1]['rank']):
            bg_color = "🟢" if p == pid else "⚪"
            st.write(f"#### {bg_color} 第 {r['rank']} 名: {r['faction']}陣營 (+{r['pts']}分)")
            if r["is_ai"]: st.info(f"🎭 **{r['personality']}**：「{r['quote']}」")
            st.write(f"出戰武將：{', '.join(r['cards'])} ➔ **總和 {r['total']}**")
            st.divider()

        st.subheader("📊 目前累積總分排名")
        current_scores = sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)
        score_data = []
        for rank, (player_key, score) in enumerate(current_scores):
            faction = room["players"].get(player_key, player_key.replace("AI_", ""))
            medal = "🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "🎖️"
            is_me = (player_key == pid)
            marker = "🟢 (你)" if is_me else ""
            score_data.append({"排名": f"{medal} 第 {rank + 1} 名", "陣營": f"{faction}陣營 {marker}", "總分": int(score)})
            
        st.dataframe(pd.DataFrame(score_data), hide_index=True, use_container_width=True)
        st.divider()

        if st.button("⏭️ 下一回合", use_container_width=True, type="primary"):
            next_round_or_finish(code); st.rerun()

    elif room["status"] == "finished":
        st.balloons(); st.header("🏆 戰局結束！天下大勢底定")
        for i, (p, s) in enumerate(sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)):
            faction = room['players'].get(p, p.replace("AI_", ""))
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🎖️"
            st.subheader(f"{medal} {faction}陣營：{s} 分")
        if st.button("🚪 離開房間並返回大廳"): st.session_state.current_room = None; st.rerun()

# 路由
if st.session_state.current_room: render_room()
else: render_lobby()
