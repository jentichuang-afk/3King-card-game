import streamlit as st
import secrets
import html
import logging
import re
import pandas as pd
import random
import json
import os
# 🚀 引入全新世代的 Google GenAI SDK
from google import genai

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

if API_KEY:
    ai_client = genai.Client(api_key=API_KEY)
else:
    ai_client = None
    logging.warning("未偵測到 GEMINI_API_KEY，AI 將採用預設隨機決策。")

if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

@st.cache_resource
def get_global_rooms():
    return {}

GLOBAL_ROOMS = get_global_rooms()
VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🤖 智慧型動態模型備援機制
# ==========================================
MODEL_HIERARCHY = [
    "gemini-3.0-flash",       
    "gemini-2.5-flash-lite",  
    "gemini-2.5-flash",       
    "gemini-1.5-flash"        
]

def call_gemini_with_fallback(prompt: str) -> tuple:
    if not ai_client: raise ValueError("API Client 未初始化")
    last_error = None
    for model_name in MODEL_HIERARCHY:
        try:
            response = ai_client.models.generate_content(model=model_name, contents=prompt)
            if response.text: return response.text, model_name
        except Exception as e:
            logging.warning(f"[AI Routing] {model_name} 失敗，切換中...")
            last_error = e
            continue 
    raise RuntimeError(f"所有備援皆耗盡。錯誤: {last_error}")

# ==========================================
# 🗄️ 靜態遊戲資料與 AI 性格設定
# ==========================================
AI_PERSONALITIES = {
    "【神算子】": "優雅、從容、預判。對玩家保持禮貌但極度自信。",
    "【霸道梟雄】": "狂傲、霸氣、壓制。充滿壓迫感與征服欲。",
    "【守護之盾】": "謙遜、堅毅、溫厚。充滿正氣，強調防守與堅守底線。"
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

def check_api_status():
    try:
        raw_text, used_model = call_gemini_with_fallback("這是一個連線測試，請直接回覆『OK』。")
        return True, f"連線成功！自動切換並使用模型：`{used_model}` (回應: {raw_text.strip()})"
    except Exception as e:
        return False, f"連線失敗，錯誤原因：{str(e)}"

# ==========================================
# 🧠 AI 本地演算法 (0 延遲，不消耗 API)
# ==========================================
def get_ai_cards_local(available_cards: list, personality_name: str) -> list:
    card_stats = [(name, get_general_stats(name)) for name in available_cards]
    if "神算子" in personality_name:
        card_stats.sort(key=lambda x: sum(x[1].values()), reverse=True)
    elif "霸道梟雄" in personality_name:
        card_stats.sort(key=lambda x: x[1]["武力"] + x[1]["統帥"], reverse=True)
    elif "守護之盾" in personality_name:
        card_stats.sort(key=lambda x: x[1]["政治"] + x[1]["魅力"] + x[1]["運氣"], reverse=True)
    else:
        random.shuffle(card_stats)
    return [card[0] for card in card_stats[:3]]

# ==========================================
# 🧠 劇本金庫生成器 (全場只消耗 1 次 API，極大化利用 TPM)
# ==========================================
def generate_dialogue_vault(personalities: list) -> dict:
    """在開局時一次性生成所有性格、屬性、名次的戰後台詞"""
    if not ai_client: return {}
    
    personalities_str = ", ".join(personalities)
    prompt = f"""
    你是頂尖的三國遊戲編劇。請為參與本局遊戲的 AI 性格：【{personalities_str}】 預先寫好一份完整的「台詞劇本金庫」。
    
    情境要求：
    包含 6 種比拼屬性：武力(單挑衝鋒)、智力(計謀看破)、統帥(排兵布陣)、政治(朝堂後勤)、魅力(激勵人心)、運氣(天象變換)。
    每種屬性下，必須為該性格寫出 4 種名次反應：
    "1": 第 1 名的囂張得意
    "2": 第 2 名的不甘示弱
    "3": 第 3 名的尋找藉口
    "4": 第 4 名的徹底崩潰與抱怨
    每句台詞限 15 字以內。
    
    請嚴格回傳 JSON，格式如下：
    {{
      "性格名稱 (例如 【神算子】)": {{
         "武力": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         "智力": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         "統帥": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         "政治": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         "魅力": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         "運氣": {{"1": "...", "2": "...", "3": "...", "4": "..."}}
      }},
      "其他性格...": {{...}}
    }}
    """
    try:
        raw_text, _ = call_gemini_with_fallback(prompt)
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3].strip()
        return json.loads(raw_text)
    except Exception as e:
        logging.error(f"[Dialogue Vault] 劇本生成失敗: {e}")
        return {}

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
            "ai_personalities": {}, "dialogue_vault": {} # ✨ 新增劇本金庫
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
    random.shuffle(available_personalities)
    
    ai_personality_list = []
    for af in room["ai_factions"]:
        ai_id = f"AI_{af}"
        room["decks"][ai_id], room["scores"][ai_id] = list(FACTION_ROSTERS[af]), 0
        pers = available_personalities.pop() if available_personalities else "【神算子】"
        room["ai_personalities"][ai_id] = pers
        ai_personality_list.append(pers)
        
    # ✨ 核心重構：開局時耗費唯一 1 次 API 額度，載滿大卡車！
    room["dialogue_vault"] = generate_dialogue_vault(ai_personality_list)
    room["status"] = "playing"

def lock_cards(code: str, pid: str, cards: list):
    room = GLOBAL_ROOMS.get(code)
    room["locked_cards"][pid] = cards
    
    for af in room["ai_factions"]:
        ai_id = f"AI_{af}"
        if ai_id not in room["locked_cards"]:
            ai_deck = room["decks"][ai_id]
            personality = room["ai_personalities"][ai_id]
            room["locked_cards"][ai_id] = get_ai_cards_local(ai_deck, personality)
            
    if len(room["locked_cards"]) == 4: 
        room["status"] = "resolution_pending"

def resolve_round(code: str):
    room = GLOBAL_ROOMS.get(code)
    attr = secrets.SystemRandom().choice(["武力", "智力", "統帥", "政治", "魅力", "運氣"])
    totals = {pid: sum(get_general_stats(c)[attr] for c in cards) for pid, cards in room["locked_cards"].items()}
    sorted_p = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    ranks, cur_r = {}, 0
    vault = room.get("dialogue_vault", {}) # 取出金庫
    
    for i, (pid, tot) in enumerate(sorted_p):
        if i > 0 and tot < sorted_p[i-1][1]: cur_r = i
        rank_num = cur_r + 1
        pts = {0:5, 1:3, 2:2, 3:1}.get(cur_r, 0)
        room["scores"][pid] += pts
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]
        
        faction_name = room["players"].get(pid, pid.replace("AI_",""))
        is_ai = pid.startswith("AI_")
        personality = room["ai_personalities"].get(pid, "")
        
        # ✨ 從金庫提取台詞 (0 API 消耗)
        final_quote = "勝敗乃兵家常事。"
        if is_ai and vault and personality in vault:
            final_quote = vault[personality].get(attr, {}).get(str(rank_num), "這局勢出乎我意料...")
            
        ranks[pid] = {
            "faction": faction_name, "cards": room["locked_cards"][pid], 
            "total": tot, "pts": pts, "rank": rank_num, "is_ai": is_ai,
            "personality": personality, "quote": final_quote
        }

    room.update({"last_attr": attr, "results": ranks, "status": "resolution_result"})

def next_round_or_finish(code: str):
    room = GLOBAL_ROOMS.get(code)
    room["locked_cards"] = {}
    if room["round"] >= 5: room["status"] = "finished"
    else: room["round"] += 1; room["status"] = "playing"

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
    with st.expander("📡 系統與 API 連線診斷 (開發者工具)"):
        st.write("目前架構：極致省流版 (每場遊戲僅消耗 1 次 API，完美利用高 TPM 額度)")
        if st.button("🔌 測試 API 動態路由", type="secondary"):
            with st.spinner("正在尋找可用之 Gemini API..."):
                is_ok, msg = check_api_status()
                if is_ok: st.success(msg)
                else: st.error(msg)

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
        
        # ✨ 將 Spinner 移至大廳，開始遊戲時生成全局劇本
        if st.button("🚀 開始遊戲", type="primary"): 
            with st.spinner("🔮 軍師正在推演天下大局 (正在產生全場 AI 專屬劇本，請稍候)..."):
                start_game(code)
            st.rerun()

    elif room["status"] == "playing":
        if pid in room["locked_cards"]: 
            st.info("🔒 陣容已鎖定。等待對手部署..."); st.button("🔄 刷新")
        else:
            deck = room["decks"][pid]
            df = pd.DataFrame([{"名": n, **get_general_stats(n)} for n in deck])
            st.write("📊 **軍情處：請直接勾選下方表格，點選 3 名出戰武將**")
            event = st.dataframe(df, on_select="rerun", selection_mode="multi-row", hide_index=True, use_container_width=True)
            sel_idx = event.selection.rows
            
            if len(sel_idx) == 3:
                selected_names = df.iloc[sel_idx]["名"].tolist()
                st.success(f"⚔️ 已選定出戰：{', '.join(selected_names)}")
                # 閃電結算，不再有任何 API 延遲
                if st.button("🔐 鎖定出戰", type="primary"):
                    lock_cards(code, pid, selected_names)
                    st.rerun()
            elif len(sel_idx) > 3: st.error(f"⚠️ 只能選擇 3 名武將！您目前選擇了 {len(sel_idx)} 名。")
            else: st.warning(f"請在上方表格精確勾選 3 位武將 (目前 {len(sel_idx)}/3)")

    elif room["status"] == "resolution_pending":
        st.success("各路諸侯皆已佈陣完畢！")
        if st.button("🎲 擲骰子並揭曉戰場實況", type="primary", use_container_width=True):
            resolve_round(code)
            st.rerun()

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
            score_data.append({"排名": f"{medal} 第 {rank + 1} 名", "陣營": f"{faction}陣營" + (" 🟢(你)" if is_me else ""), "總分": int(score)})
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

if st.session_state.current_room: render_room()
else: render_lobby()
