import streamlit as st
import secrets
import html
import logging
import re
import pandas as pd
import random
import json
import os
# 🚀 引入 Google 與 OpenAI(相容 Grok/Groq) SDK
from google import genai
from openai import OpenAI

# ==========================================
# 🛡️ 資安配置與系統初始化
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SECURE_LOG] - %(message)s')

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    GROK_API_KEY = os.getenv("GROK_API_KEY") or st.secrets.get("GROK_API_KEY")
except Exception:
    GEMINI_API_KEY, GROQ_API_KEY, GROK_API_KEY = None, None, None

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
if not gemini_client: logging.warning("未偵測到 GEMINI_API_KEY。")

if GROQ_API_KEY:
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
else:
    groq_client = None
    logging.warning("未偵測到 GROQ_API_KEY。")

if GROK_API_KEY:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.xai.com/v1")
else:
    grok_client = None
    logging.warning("未偵測到 GROK_API_KEY。")

if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

@st.cache_resource
def get_global_rooms(): return {}
GLOBAL_ROOMS = get_global_rooms()
VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🎨 動態頭像映射表 (Avatar Mapping)
# ==========================================
AVATAR_FILES = {
    "【神算子】": {
        1: "avatars/strategist_1.png", 2: "avatars/strategist_2.png",
        3: "avatars/strategist_3.png", 4: "avatars/strategist_4.png"
    },
    "【霸道梟雄】": {
        1: "avatars/warlord_1.png", 2: "avatars/warlord_2.png",
        3: "avatars/warlord_3.png", 4: "avatars/warlord_4.png"
    },
    "【守護之盾】": {
        1: "avatars/shield_1.png", 2: "avatars/shield_2.png",
        3: "avatars/shield_3.png", 4: "avatars/shield_4.png"
    }
}

# ==========================================
# 🤖 跨三雲端動態模型備援機制
# ==========================================
GEMINI_MODELS = ["gemini-3.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]

def call_ai_with_fallback(prompt: str) -> tuple:
    last_error = None
    
    if gemini_client:
        for model_name in GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(model=model_name, contents=prompt)
                if response.text: return response.text, f"Google {model_name}"
            except Exception as e:
                last_error = e
                continue 

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[
                    {"role": "system", "content": "你是一個嚴格輸出純JSON格式的三國遊戲對話生成引擎。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} 
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content, "Groq Llama-3.3-70B"
        except Exception as e:
            last_error = e

    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                model="grok-2-latest",
                messages=[
                    {"role": "system", "content": "你是一個嚴格輸出純JSON格式的三國遊戲對話生成引擎。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} 
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content, "xAI Grok-2"
        except Exception as e:
            last_error = e

    raise RuntimeError(f"所有三雲端 AI 援軍皆已陣亡！最後錯誤: {last_error}")

# ==========================================
# 🗄️ 靜態遊戲資料與 AI 性格設定
# ==========================================
AI_PERSONALITIES = {
    "【神算子】": "優雅、從容、預判。對玩家保持禮貌但極度自信，喜歡嘲笑別人智商低。",
    "【霸道梟雄】": "狂傲、霸氣、壓制。充滿壓迫感與征服欲，動不動就喊打喊殺。",
    "【守護之盾】": "謙遜、堅毅、死板。滿口仁義道德，就算輸了也要說些大道理。"
}

FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇", "郭嘉", "典韋", "許褚", "荀彧", "夏侯淵", "曹丕", "曹仁", "賈詡", "徐晃", "張郃", "龐德"],
    "蜀": ["劉備", "關羽", "諸葛亮", "張飛", "趙雲", "馬超", "黃忠", "魏延", "龐統", "姜維", "法正", "黃月英", "馬岱", "關平", "劉禪"],
    "吳": ["孫權", "周瑜", "太史慈", "孫策", "陸遜", "呂蒙", "甘寧", "黃蓋", "凌統", "周泰", "魯肅", "孫尚香", "大喬", "小喬", "程普"],
    "其他": ["呂布", "張角", "董卓", "袁紹", "左慈", "賈詡", "陳宮", "馬騰", "貂蟬", "華佗", "孟獲", "祝融", "公孫瓚", "盧植", "皇甫嵩"]
}

GENERALS_STATS = {
    "曹操": {"武力": 72, "智力": 91, "統帥": 96, "政治": 94, "魅力": 96, "運氣": 85}, "張遼": {"武力": 92, "智力": 78, "統帥": 93, "政治": 58, "魅力": 77, "運氣": 80},
    "司馬懿": {"武力": 63, "智力": 96, "統帥": 98, "政治": 93, "魅力": 87, "運氣": 75}, "夏侯惇": {"武力": 90, "智力": 60, "統帥": 85, "政治": 70, "魅力": 80, "運氣": 65},
    "郭嘉": {"武力": 15, "智力": 98, "統帥": 80, "政治": 85, "魅力": 75, "運氣": 40}, "典韋": {"武力": 95, "智力": 35, "統帥": 55, "政治": 29, "魅力": 58, "運氣": 45},
    "許褚": {"武力": 96, "智力": 36, "統帥": 65, "政治": 20, "魅力": 60, "運氣": 60}, "荀彧": {"武力": 14, "智力": 95, "統帥": 52, "政治": 98, "魅力": 89, "運氣": 70},
    "夏侯淵": {"武力": 91, "智力": 55, "統帥": 84, "政治": 61, "魅力": 78, "運氣": 50}, "曹丕": {"武力": 71, "智力": 83, "統帥": 75, "政治": 86, "魅力": 85, "運氣": 80},
    "曹仁": {"武力": 86, "智力": 62, "統帥": 89, "政治": 52, "魅力": 76, "運氣": 70}, "賈詡": {"武力": 48, "智力": 97, "統帥": 86, "政治": 85, "魅力": 53, "運氣": 88},
    "徐晃": {"武力": 90, "智力": 74, "統帥": 88, "政治": 48, "魅力": 71, "運氣": 70}, "張郃": {"武力": 89, "智力": 69, "統帥": 90, "政治": 57, "魅力": 71, "運氣": 60},
    "龐德": {"武力": 94, "智力": 68, "統帥": 80, "政治": 42, "魅力": 70, "運氣": 40}, "劉備": {"武力": 75, "智力": 78, "統帥": 88, "政治": 85, "魅力": 99, "運氣": 95},
    "關羽": {"武力": 97, "智力": 75, "統帥": 95, "政治": 62, "魅力": 93, "運氣": 80}, "諸葛亮": {"武力": 45, "智力": 100, "統帥": 98, "政治": 98, "魅力": 95, "運氣": 85},
    "張飛": {"武力": 98, "智力": 50, "統帥": 90, "政治": 35, "魅力": 65, "運氣": 65}, "趙雲": {"武力": 96, "智力": 76, "統帥": 91, "政治": 65, "魅力": 90, "運氣": 85},
    "馬超": {"武力": 97, "智力": 52, "統帥": 91, "政治": 35, "魅力": 85, "運氣": 65}, "黃忠": {"武力": 93, "智力": 60, "統帥": 86, "政治": 52, "魅力": 75, "運氣": 65},
    "魏延": {"武力": 94, "智力": 72, "統帥": 89, "政治": 50, "魅力": 55, "運氣": 50}, "龐統": {"武力": 34, "智力": 97, "統帥": 86, "政治": 85, "魅力": 69, "運氣": 30},
    "姜維": {"武力": 91, "智力": 92, "統帥": 94, "政治": 80, "魅力": 85, "運氣": 65}, "法正": {"武力": 52, "智力": 95, "統帥": 88, "政治": 82, "魅力": 60, "運氣": 75},
    "黃月英": {"武力": 35, "智力": 95, "統帥": 65, "政治": 88, "魅力": 75, "運氣": 70}, "馬岱": {"武力": 85, "智力": 62, "統帥": 80, "政治": 50, "魅力": 72, "運氣": 80},
    "關平": {"武力": 84, "智力": 75, "統帥": 82, "政治": 65, "魅力": 80, "運氣": 70}, "劉禪": {"武力": 25, "智力": 45, "統帥": 35, "政治": 55, "魅力": 75, "運氣": 100},
    "孫權": {"武力": 67, "智力": 80, "統帥": 76, "政治": 89, "魅力": 95, "運氣": 88}, "周瑜": {"武力": 71, "智力": 96, "統帥": 97, "政治": 86, "魅力": 93, "運氣": 75},
    "太史慈": {"武力": 93, "智力": 66, "統帥": 82, "政治": 58, "魅力": 79, "運氣": 60}, "孫策": {"武力": 92, "智力": 69, "統帥": 90, "政治": 70, "魅力": 90, "運氣": 50},
    "陸遜": {"武力": 69, "智力": 95, "統帥": 96, "政治": 87, "魅力": 85, "運氣": 80}, "呂蒙": {"武力": 81, "智力": 89, "統帥": 91, "政治": 78, "魅力": 82, "運氣": 70},
    "甘寧": {"武力": 94, "智力": 76, "統帥": 86, "政治": 18, "魅力": 58, "運氣": 65}, "黃蓋": {"武力": 83, "智力": 65, "統帥": 79, "政治": 50, "魅力": 75, "運氣": 70},
    "凌統": {"武力": 89, "智力": 60, "統帥": 77, "政治": 42, "魅力": 71, "運氣": 60}, "周泰": {"武力": 91, "智力": 48, "統帥": 76, "政治": 38, "魅力": 61, "運氣": 80},
    "魯肅": {"武力": 43, "智力": 92, "統帥": 80, "政治": 93, "魅力": 89, "運氣": 85}, "孫尚香": {"武力": 86, "智力": 70, "統帥": 72, "政治": 63, "魅力": 85, "運氣": 75},
    "大喬": {"武力": 11, "智力": 73, "統帥": 26, "政治": 60, "魅力": 92, "運氣": 60}, "小喬": {"武力": 12, "智力": 74, "統帥": 28, "政治": 62, "魅力": 93, "運氣": 60},
    "程普": {"武力": 79, "智力": 74, "統帥": 84, "政治": 65, "魅力": 75, "運氣": 70},
    "呂布": {"武力": 100, "智力": 38, "統帥": 94, "政治": 25, "魅力": 65, "運氣": 45}, "張角": {"武力": 35, "智力": 92, "統帥": 91, "政治": 88, "魅力": 98, "運氣": 65},
    "董卓": {"武力": 87, "智力": 74, "統帥": 90, "政治": 68, "魅力": 45, "運氣": 50}, "袁紹": {"武力": 72, "智力": 82, "統帥": 93, "政治": 88, "魅力": 92, "運氣": 70},
    "左慈": {"武力": 45, "智力": 98, "統帥": 60, "政治": 55, "魅力": 85, "運氣": 99}, "陳宮": {"武力": 55, "智力": 92, "統帥": 85, "政治": 83, "魅力": 72, "運氣": 50},
    "馬騰": {"武力": 82, "智力": 65, "統帥": 84, "政治": 70, "魅力": 85, "運氣": 75}, "貂蟬": {"武力": 30, "智力": 85, "統帥": 45, "政治": 82, "魅力": 100, "運氣": 80},
    "華佗": {"武力": 20, "智力": 90, "統帥": 35, "政治": 65, "魅力": 95, "運氣": 85}, "孟獲": {"武力": 88, "智力": 55, "統帥": 82, "政治": 58, "魅力": 80, "運氣": 75},
    "祝融": {"武力": 87, "智力": 52, "統帥": 75, "政治": 45, "魅力": 85, "運氣": 65}, "公孫瓚": {"武力": 86, "智力": 68, "統帥": 86, "政治": 60, "魅力": 78, "運氣": 65},
    "盧植": {"武力": 70, "智力": 85, "統帥": 90, "政治": 88, "魅力": 88, "運氣": 75}, "皇甫嵩": {"武力": 75, "智力": 78, "統帥": 95, "政治": 75, "魅力": 82, "運氣": 80},
    "賈詡": {"武力": 48, "智力": 97, "統帥": 88, "政治": 85, "魅力": 60, "運氣": 90}
}

def get_general_stats(name: str):
    return GENERALS_STATS.get(name, {"武力": 50, "智力": 50, "統帥": 50, "政治": 50, "魅力": 50, "運氣": 50})

def check_api_status():
    try:
        raw_text, used_model = call_ai_with_fallback("這是一個連線測試，請直接回覆包含 JSON 的字串：{\"test\":\"OK\"}。")
        return True, f"連線成功！當前值班大腦：`{used_model}`"
    except Exception as e:
        return False, f"連線失敗，三大雲端皆無法使用。錯誤：{str(e)}"

# ==========================================
# 🧠 AI 本地演算法
# ==========================================
def get_ai_cards_local(available_cards: list, personality_name: str) -> list:
    card_stats = [(name, get_general_stats(name)) for name in available_cards]
    if "神算子" in personality_name: card_stats.sort(key=lambda x: sum(x[1].values()), reverse=True)
    elif "霸道梟雄" in personality_name: card_stats.sort(key=lambda x: x[1]["武力"] + x[1]["統帥"], reverse=True)
    elif "守護之盾" in personality_name: card_stats.sort(key=lambda x: x[1]["政治"] + x[1]["魅力"] + x[1]["運氣"], reverse=True)
    else: random.shuffle(card_stats)
    return [card[0] for card in card_stats[:3]]

# ==========================================
# 🧠 劇本金庫生成器
# ==========================================
def generate_dialogue_vault(personalities: list) -> dict:
    if not (gemini_client or groq_client or grok_client): return {}
    
    personalities_str = ", ".join(personalities)
    prompt = f"""
    你是頂尖的三國遊戲編劇，特別擅長寫「極具戲劇張力與嘲諷感的三國垃圾話」。
    請為參與本局遊戲的 AI 性格：【{personalities_str}】 預先寫好一份完整的台詞劇本金庫。
    
    情境要求：
    包含 6 種比拼屬性：武力(單挑衝鋒)、智力(計謀看破)、統帥(排兵布陣)、政治(朝堂後勤)、魅力(激勵人心)、運氣(天象變換)。
    請為該性格在各種屬性下，寫出 4 種名次反應。務必展現出濃烈的情緒、強烈嘲諷與三國韻味（每句字數嚴格控制在 15 到 35 字之間）：
    
    "1": 第 1 名的反應（極度囂張、無情嘲諷對手）
    "2": 第 2 名的反應（極不甘心、咬牙切齒放狠話）
    "3": 第 3 名的反應（死要面子、瘋狂找藉口）
    "4": 第 4 名的反應（徹底崩潰、仰天長嘆或哀嚎）
    
    請嚴格回傳 JSON，格式如下：
    {{
      "{personalities[0]}": {{
         "武力": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
         ...
      }}
    }}
    請確保包含所有輸入的性格，且不要給出單純的四字成語，要寫出有靈魂的句子！
    """
    try:
        raw_text, used_model = call_ai_with_fallback(prompt)
        logging.info(f"[Dialogue Vault] 劇本生成成功，歸功於：{used_model}")
        if "```json" in raw_text: raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text: raw_text = raw_text.split("```")[1].strip()
        return json.loads(raw_text)
    except Exception as e:
        logging.error(f"[Dialogue Vault] 劇本生成失敗: {e}")
        return {}

# ==========================================
# ⚙️ 核心系統功能
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
            "ai_personalities": {}, "dialogue_vault": {}
        }

def assign_faction(code: str, pid: str, faction: str):
    room = GLOBAL_ROOMS.get(code)
    taken = list(room["players"].values()) + room["ai_factions"]
    if faction not in taken: room["players"][pid] = faction

def start_game(code: str):
    room = GLOBAL_ROOMS.get(code)
    
    # 🛡️ 防呆機制：清除已加入但未選擇陣營的幽靈玩家
    unassigned = [p for p, f in room["players"].items() if f not in VALID_FACTIONS]
    for p in unassigned:
        del room["players"][p]
        
    taken = list(room["players"].values())
    room["ai_factions"] = [f for f in VALID_FACTIONS if f not in taken]
    
    for p_id, f in room["players"].items():
        room["decks"][p_id], room["scores"][p_id] = list(FACTION_ROSTERS[f]), 0
        
    available_personalities = list(AI_PERSONALITIES.keys())
    random.shuffle(available_personalities)
    
    ai_personality_list = []
    for af in room["ai_factions"]:
        ai_id = f"AI_{af}"
        room["decks"][ai_id], room["scores"][ai_id] = list(FACTION_ROSTERS[af]), 0
        pers = available_personalities.pop() if available_personalities else "【神算子】"
        room["ai_personalities"][ai_id] = pers
        ai_personality_list.append(pers)
        
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
    if len(room["locked_cards"]) == 4: room["status"] = "resolution_pending"

def resolve_round(code: str):
    room = GLOBAL_ROOMS.get(code)
    attr = secrets.SystemRandom().choice(["武力", "智力", "統帥", "政治", "魅力", "運氣"])
    totals = {pid: sum(get_general_stats(c)[attr] for c in cards) for pid, cards in room["locked_cards"].items()}
    sorted_p = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    ranks, cur_r = {}, 0
    vault = room.get("dialogue_vault", {})
    
    for i, (pid, tot) in enumerate(sorted_p):
        if i > 0 and tot < sorted_p[i-1][1]: cur_r = i
        rank_num = cur_r + 1
        pts = {0:5, 1:3, 2:2, 3:1}.get(cur_r, 0)
        room["scores"][pid] += pts
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]
        
        faction_name = room["players"].get(pid, pid.replace("AI_",""))
        is_ai = pid.startswith("AI_")
        personality = room["ai_personalities"].get(pid, "")
        
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
    with st.expander("📡 三雲端 AI 引擎診斷 (Gemini / Groq / Grok)"):
        if st.button("🔌 測試跨雲端動態路由", type="secondary"):
            with st.spinner("正在呼叫三雲端 AI 系統..."):
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
        
        # 🛡️ 防呆判斷：必須選好陣營才能開始遊戲
        has_faction = pid in room["players"] and room["players"][pid] in VALID_FACTIONS
        if not has_faction:
            st.info("👆 主公，請先在上方選擇您的專屬陣營，才能發兵出征！")
        else:
            if st.button("🚀 開始遊戲", type="primary"): 
                with st.spinner("🔮 三雲端 AI 正在推演天下大局 (正在撰寫全場專屬垃圾話劇本，請稍候)..."):
                    start_game(code)
                st.rerun()

    elif room["status"] == "playing":
        # 🛡️ 觀戰模式保護：若沒選陣營就開局，降級為觀戰模式
        if pid not in room["decks"]:
            st.warning("👀 您本局並未選擇陣營，目前處於觀戰模式。請等待場上玩家完成決策。")
            if st.button("🔄 刷新戰況"): st.rerun()
        elif pid in room["locked_cards"]: 
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
                if st.button("🔐 鎖定出戰", type="primary"):
                    lock_cards(code, pid, selected_names)
                    st.rerun()
            elif len(sel_idx) > 3: st.error(f"⚠️ 只能選擇 3 名武將！您目前選擇了 {len(sel_idx)} 名。")
            else: st.warning(f"請在上方表格精確勾選 3 位武將 (目前 {len(sel_idx)}/3)")

    elif room["status"] == "resolution_pending":
        if pid not in room["decks"]:
            st.info("👀 觀戰中：各路諸侯皆已佈陣完畢！等待場上主公結算。")
            if st.button("🔄 刷新等待結算"): st.rerun()
        else:
            st.success("各路諸侯皆已佈陣完畢！")
            if st.button("🎲 擲骰子並揭曉戰場實況", type="primary", use_container_width=True):
                resolve_round(code)
                st.rerun()

    elif room["status"] == "resolution_result":
        st.header(f"🎲 比拼屬性：【{room['last_attr']}】")
        st.subheader("📌 本回合戰果與謀士語錄")
        
        for p, r in sorted(room["results"].items(), key=lambda x: x[1]['rank']):
            bg_color = "🟢" if p == pid else "⚪"
            display_name = f"{r['personality']} ({r['faction']})" if r["is_ai"] else f"主公 {p} ({r['faction']})"
            st.write(f"#### {bg_color} 第 {r['rank']} 名: {display_name} (+{r['pts']}分)")
            
            if r["is_ai"]:
                pers = r['personality']
                rank_num = r['rank']
                avatar_file = AVATAR_FILES.get(pers, {}).get(rank_num, "")
                
                with st.container():
                    col_img, col_txt = st.columns([1, 6])
                    with col_img:
                        if os.path.exists(avatar_file):
                            st.image(avatar_file, use_container_width=True)
                        else:
                            st.markdown(f"**{pers}**<br>*(待放置頭像)*", unsafe_allow_html=True)
                    with col_txt:
                        st.info(f"「{r['quote']}」")
            
            st.write(f"出戰武將：{', '.join(r['cards'])} ➔ **總和 {r['total']}**")
            st.divider()

        st.subheader("📊 目前累積總分排名")
        current_scores = sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)
        score_data = []
        for rank, (player_key, score) in enumerate(current_scores):
            faction = room["players"].get(player_key, player_key.replace("AI_", ""))
            is_ai = player_key.startswith("AI_")
            
            if is_ai:
                pers = room["ai_personalities"].get(player_key, "")
                display_name = f"{pers} ({faction})"
            else:
                display_name = f"主公 {player_key} ({faction})"
                
            medal = "🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "🎖️"
            is_me = (player_key == pid)
            marker = " 🟢(你)" if is_me else ""
            score_data.append({"排名": f"{medal} 第 {rank + 1} 名", "名號 (陣營)": f"{display_name}{marker}", "總分": int(score)})
            
        st.dataframe(pd.DataFrame(score_data), hide_index=True, use_container_width=True)
        st.divider()

        # 🛡️ 觀戰者防護
        if pid not in room["decks"]:
            if st.button("🔄 刷新看下一回合", use_container_width=True): st.rerun()
        else:
            if st.button("⏭️ 下一回合", use_container_width=True, type="primary"):
                next_round_or_finish(code); st.rerun()

    elif room["status"] == "finished":
        st.balloons(); st.header("🏆 戰局結束！天下大勢底定")
        for i, (p, s) in enumerate(sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)):
            faction = room['players'].get(p, p.replace("AI_", ""))
            is_ai = p.startswith("AI_")
            
            if is_ai:
                pers = room["ai_personalities"].get(p, "")
                display_name = f"{pers} ({faction})"
            else:
                display_name = f"主公 {p} ({faction})"
                
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🎖️"
            st.subheader(f"{medal} {display_name}：{s} 分")
            
        if st.button("🚪 離開房間並返回大廳"): st.session_state.current_room = None; st.rerun()

if st.session_state.current_room: render_room()
else: render_lobby()
