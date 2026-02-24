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
groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None
grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.xai.com/v1") if GROK_API_KEY else None

if 'current_room' not in st.session_state:
    st.session_state.current_room = None
if 'player_id' not in st.session_state:
    st.session_state.player_id = None

@st.cache_resource
def get_global_rooms(): return {}
GLOBAL_ROOMS = get_global_rooms()
VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🎨 動態頭像映射表
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
                messages=[{"role": "system", "content": "你是一個三國遊戲編劇。"},{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} 
            )
            return response.choices[0].message.content, "Groq Llama-3.3"
        except Exception as e: last_error = e
    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                model="grok-2-latest",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} 
            )
            return response.choices[0].message.content, "xAI Grok-2"
        except Exception as e: last_error = e
    raise RuntimeError(f"援軍耗盡: {last_error}")

# ==========================================
# 🗄️ 靜態遊戲資料
# ==========================================
AI_PERSONALITIES = {
    "【神算子】": "優雅、從容、預判。對玩家保持禮貌但極度自信，嘲笑別人智商低。",
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

# ==========================================
# 🧠 AI 核心邏輯
# ==========================================
def get_ai_cards_local(available_cards: list, personality_name: str) -> list:
    card_stats = [(name, get_general_stats(name)) for name in available_cards]
    if "神算子" in personality_name: card_stats.sort(key=lambda x: sum(x[1].values()), reverse=True)
    elif "霸道梟雄" in personality_name: card_stats.sort(key=lambda x: x[1]["武力"] + x[1]["統帥"], reverse=True)
    else: card_stats.sort(key=lambda x: x[1]["政治"] + x[1]["魅力"] + x[1]["運氣"], reverse=True)
    return [card[0] for card in card_stats[:3]]

def generate_dialogue_vault(personalities: list) -> dict:
    if not personalities: return {}
    prompt = f"""
    你是三國遊戲編劇。請為性格：【{', '.join(personalities)}】 預先寫好劇本。
    要求：針對 6 種屬性（武力, 智力, 統帥, 政治, 魅力, 運氣），寫出 4 種名次反應。
    每句 15-35 字，展現極度嘲諷或極度崩潰。特別是在「爆擊」或「完敗」時，語氣要加倍強烈。
    
    格式：
    {{
      "性格": {{
         "屬性": {{"1": "台詞", "2": "台詞", "3": "台詞", "4": "台詞"}}
      }}
    }}
    """
    try:
        raw_text, _ = call_ai_with_fallback(prompt)
        if "```json" in raw_text: raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text: raw_text = raw_text.split("```")[1].strip()
        return json.loads(raw_text)
    except: return {}

# ==========================================
# ⚙️ 核心系統功能 (含爆擊/險勝/完敗邏輯)
# ==========================================
def resolve_round(code: str):
    room = GLOBAL_ROOMS.get(code)
    attr = secrets.SystemRandom().choice(["武力", "智力", "統帥", "政治", "魅力", "運氣"])
    totals = {pid: sum(get_general_stats(c)[attr] for c in cards) for pid, cards in room["locked_cards"].items()}
    sorted_p = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    # 🔍 計算戰場變數
    diff_1_2 = sorted_p[0][1] - sorted_p[1][1]
    diff_1_4 = sorted_p[0][1] - sorted_p[3][1]
    
    status_msg = ""
    pts_map = {0: 5, 1: 3, 2: 2, 3: 1}
    
    # ⚡ 觸發爆擊
    if diff_1_2 > 30:
        pts_map[0] = 8
        status_msg = "💥 爆擊：碾壓獲勝！"
    # ⚡ 觸發險勝
    elif diff_1_2 < 5 and diff_1_2 >= 0:
        pts_map[0] = 4
        status_msg = "😅 險勝：慘勝如敗..."
        
    # 💀 觸發完敗
    is_total_defeat = diff_1_4 > 60
    if is_total_defeat:
        pts_map[3] = 0
    
    ranks = {}
    vault = room.get("dialogue_vault", {})
    for i, (pid, tot) in enumerate(sorted_p):
        rank_num = i + 1
        pts = pts_map.get(i, 0)
        room["scores"][pid] += pts
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]
        
        is_ai = pid.startswith("AI_")
        pers = room["ai_personalities"].get(pid, "")
        final_quote = vault.get(pers, {}).get(attr, {}).get(str(rank_num), "勝敗乃常事。") if is_ai else ""
        
        # 標記特殊狀態
        special_tag = ""
        if rank_num == 1: special_tag = status_msg
        if rank_num == 4 and is_total_defeat: special_tag = "💀 完敗：軍心崩潰！"

        ranks[pid] = {
            "faction": room["players"].get(pid, pid.replace("AI_","")),
            "cards": room["locked_cards"][pid], "total": tot, "pts": pts, 
            "rank": rank_num, "is_ai": is_ai, "personality": pers, "quote": final_quote,
            "tag": special_tag
        }
    room.update({"last_attr": attr, "results": ranks, "status": "resolution_result"})

# ==========================================
# 🖥️ Streamlit 渲染
# ==========================================
def render_lobby():
    st.title("⚔️ 三國之巔：大廳")
    pid_input = st.text_input("👤 主公名號：", key="pid_in")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️ 建立戰局"):
            code = secrets.token_hex(3).upper()
            GLOBAL_ROOMS[code] = {"players": {}, "ai_factions": [], "status": "lobby", "round": 1, "decks": {}, "locked_cards": {}, "scores": {}, "ai_personalities": {}, "dialogue_vault": {}}
            st.session_state.current_room = code; st.rerun()
    st.divider()
    rooms = {c: d for c, d in GLOBAL_ROOMS.items() if d["status"] == "lobby"}
    for c, d in rooms.items():
        if st.button(f"⚔️ 加入房間 {c} ({len(d['players'])}/4)", key=c):
            st.session_state.current_room = c; st.rerun()

def render_room():
    code, pid = st.session_state.current_room, st.session_state.player_id
    room = GLOBAL_ROOMS.get(code)
    if not room: st.session_state.current_room = None; st.rerun()

    st.title(f"🏰 房間：{code} | 第 {room['round']}/5 回合")

    if room["status"] == "lobby":
        cols = st.columns(4)
        for i, f in enumerate(VALID_FACTIONS):
            taken = f in room["players"].values() or f in room["ai_factions"]
            if cols[i].button(f"{f}" + (" (已選)" if taken else ""), disabled=taken):
                room["players"][pid] = f; st.rerun()
        
        if pid in room["players"]:
            if st.button("🚀 開始遊戲", type="primary"):
                with st.spinner("🔮 撰寫垃圾話劇本中..."):
                    taken = list(room["players"].values())
                    room["ai_factions"] = [f for f in VALID_FACTIONS if f not in taken]
                    for p, f in room["players"].items(): room["decks"][p], room["scores"][p] = list(FACTION_ROSTERS[f]), 0
                    pers_list = list(AI_PERSONALITIES.keys()); random.shuffle(pers_list)
                    ai_pers = []
                    for af in room["ai_factions"]:
                        ai_id = f"AI_{af}"
                        room["decks"][ai_id], room["scores"][ai_id] = list(FACTION_ROSTERS[af]), 0
                        p_name = pers_list.pop(); room["ai_personalities"][ai_id] = p_name; ai_pers.append(p_name)
                    room["dialogue_vault"] = generate_dialogue_vault(ai_pers)
                    room["status"] = "playing"; st.rerun()

    elif room["status"] == "playing":
        if pid not in room["decks"]: st.warning("👀 觀戰模式"); st.button("🔄 刷新")
        elif pid in room["locked_cards"]: st.info("🔒 陣容已鎖定"); st.button("🔄 刷新")
        else:
            df = pd.DataFrame([{"名": n, **get_general_stats(n)} for n in room["decks"][pid]])
            event = st.dataframe(df, on_select="rerun", selection_mode="multi-row", hide_index=True)
            if len(event.selection.rows) == 3:
                sel_names = df.iloc[event.selection.rows]["名"].tolist()
                if st.button("🔐 鎖定出戰", type="primary"):
                    room["locked_cards"][pid] = sel_names
                    for af in room["ai_factions"]: room["locked_cards"][f"AI_{af}"] = get_ai_cards_local(room["decks"][f"AI_{af}"], room["ai_personalities"][f"AI_{af}"])
                    if len(room["locked_cards"]) == 4: room["status"] = "resolution_pending"
                    st.rerun()

    elif room["status"] == "resolution_pending":
        if st.button("🎲 擲骰子結算", type="primary", use_container_width=True): resolve_round(code); st.rerun()

    elif room["status"] == "resolution_result":
        st.header(f"🎲 比拼屬性：【{room['last_attr']}】")
        for p, r in sorted(room["results"].items(), key=lambda x: x[1]['rank']):
            # 🎨 特殊視覺效果
            tag = r['tag']
            color_prefix = "🔥" if "爆擊" in tag else "😰" if "險勝" in tag else "💀" if "完敗" in tag else ""
            
            display_name = f"{r['personality']} ({r['faction']})" if r["is_ai"] else f"主公 {p} ({r['faction']})"
            st.write(f"#### 第 {r['rank']} 名: {display_name} (+{r['pts']}分) {tag}")
            
            if r["is_ai"]:
                avatar = AVATAR_FILES.get(r['personality'], {}).get(r['rank'], "")
                c1, c2 = st.columns([1, 5])
                with c1: 
                    if os.path.exists(avatar): st.image(avatar)
                    else: st.write("🎭")
                with c2: st.info(f"「{r['quote']}」")
            st.write(f"出戰：{', '.join(r['cards'])} (總和 {r['total']})")
            st.divider()
        if st.button("⏭️ 下一回合", type="primary"):
            room["locked_cards"] = {}
            if room["round"] >= 5: room["status"] = "finished"
            else: room["round"] += 1; room["status"] = "playing"
            st.rerun()

    elif room["status"] == "finished":
        st.balloons(); st.header("🏆 戰局結束")
        for p, s in sorted(room["scores"].items(), key=lambda x: x[1], reverse=True): st.subheader(f"{p}: {s} 分")
        if st.button("🚪 離開"): st.session_state.current_room = None; st.rerun()

if st.session_state.current_room: render_room()
else: render_lobby()
