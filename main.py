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

if 'current_room' not in st.session_state: st.session_state.current_room = None
if 'player_id' not in st.session_state: st.session_state.player_id = None

@st.cache_resource
def get_global_rooms(): return {}
GLOBAL_ROOMS = get_global_rooms()
VALID_FACTIONS = ["魏", "蜀", "吳", "其他"]

# ==========================================
# 🎨 Q版動態頭像映射
# ==========================================
AVATAR_FILES = {
    "【神算子】": {1: "avatars/strategist_1.png", 2: "avatars/strategist_2.png", 3: "avatars/strategist_3.png", 4: "avatars/strategist_4.png"},
    "【霸道梟雄】": {1: "avatars/warlord_1.png", 2: "avatars/warlord_2.png", 3: "avatars/warlord_3.png", 4: "avatars/warlord_4.png"},
    "【守護之盾】": {1: "avatars/shield_1.png", 2: "avatars/shield_2.png", 3: "avatars/shield_3.png", 4: "avatars/shield_4.png"}
}

# ==========================================
# 🤖 終極跨雲端動態調度 (Gemini -> Groq -> Grok)
# ==========================================
def call_ai_with_fallback(prompt: str) -> tuple:
    last_error = None
    # 1. Gemini
    if gemini_client:
        for model in ["gemini-3.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]:
            try:
                res = gemini_client.models.generate_content(model=model, contents=prompt)
                if res.text: return res.text, f"Google {model}"
            except Exception as e: last_error = e; continue
    # 2. Groq
    if groq_client:
        try:
            res = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return res.choices[0].message.content, "Groq Llama-3.3"
        except Exception as e: last_error = e
    # 3. Grok
    if grok_client:
        try:
            res = grok_client.chat.completions.create(model="grok-2-latest", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
            return res.choices[0].message.content, "xAI Grok-2"
        except Exception as e: last_error = e
    raise RuntimeError(f"AI 服務不可用: {last_error}")

# ==========================================
# 🗄️ 武將數據
# ==========================================
GENERALS_STATS = {
    "曹操": {"武力": 72, "智力": 91, "統帥": 96, "政治": 94, "魅力": 96, "運氣": 85},
    "張遼": {"武力": 92, "智力": 78, "統帥": 93, "政治": 58, "魅力": 77, "運氣": 80},
    "司馬懿": {"武力": 63, "智力": 96, "統帥": 98, "政治": 93, "魅力": 87, "運氣": 75},
    "劉備": {"武力": 75, "智力": 78, "統帥": 88, "政治": 85, "魅力": 99, "運氣": 95},
    "關羽": {"武力": 97, "智力": 75, "統帥": 95, "政治": 62, "魅力": 93, "運氣": 80},
    "諸葛亮": {"武力": 45, "智力": 100, "統帥": 98, "政治": 98, "魅力": 95, "運氣": 85},
    "孫權": {"武力": 67, "智力": 80, "統帥": 76, "政治": 89, "魅力": 95, "運氣": 88},
    "周瑜": {"武力": 71, "智力": 96, "統帥": 97, "政治": 86, "魅力": 93, "運氣": 75},
    "呂布": {"武力": 100, "智力": 38, "統帥": 94, "政治": 25, "魅力": 65, "運氣": 45},
    "張角": {"武力": 35, "智力": 92, "統帥": 91, "政治": 88, "魅力": 98, "運氣": 65},
    "袁紹": {"武力": 72, "智力": 82, "統帥": 93, "政治": 88, "魅力": 92, "運氣": 70},
    "董卓": {"武力": 87, "智力": 74, "統帥": 90, "政治": 68, "魅力": 45, "運氣": 50},
    # 增加更多隨機武將
    "夏侯惇": {"武力": 90, "智力": 60, "統帥": 85, "政治": 70, "魅力": 80, "運氣": 65},
    "趙雲": {"武力": 96, "智力": 76, "統帥": 91, "政治": 65, "魅力": 90, "運氣": 85},
    "陸遜": {"武力": 69, "智力": 95, "統帥": 96, "政治": 87, "魅力": 85, "運氣": 80}
}
FACTION_ROSTERS = {
    "魏": ["曹操", "張遼", "司馬懿", "夏侯惇"],
    "蜀": ["劉備", "關羽", "諸葛亮", "趙雲"],
    "吳": ["孫權", "周瑜", "陸遜", "甘寧"],
    "其他": ["呂布", "張角", "袁紹", "董卓"]
}
def get_general_stats(n): return GENERALS_STATS.get(n, {"武力": 60, "智力": 60, "統帥": 60, "政治": 60, "魅力": 60, "運氣": 60})

# ==========================================
# 🧠 AI 邏輯與積分判定
# ==========================================
def get_ai_cards_local(available, personality):
    card_stats = [(name, get_general_stats(name)) for name in available]
    if "神算子" in personality: card_stats.sort(key=lambda x: sum(x[1].values()), reverse=True)
    elif "霸道梟雄" in personality: card_stats.sort(key=lambda x: x[1]["武力"] + x[1]["統帥"], reverse=True)
    else: card_stats.sort(key=lambda x: x[1]["政治"] + x[1]["魅力"] + x[1]["運氣"], reverse=True)
    return [c[0] for c in card_stats[:3]]

def generate_dialogue_vault(personalities):
    if not personalities: return {}
    prompt = f"你是三國編劇。為性格：{personalities}。針對 6 種屬性寫出 4 種名次台詞(1-4)。第1名要極囂張，第4名要極崩潰。15-35字。JSON格式輸出。"
    try:
        raw, _ = call_ai_with_fallback(prompt)
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw: raw = raw.split("```")[1].strip()
        return json.loads(raw)
    except: return {}

def resolve_round(code):
    room = GLOBAL_ROOMS.get(code)
    attr = secrets.SystemRandom().choice(["武力", "智力", "統帥", "政治", "魅力", "運氣"])
    totals = {pid: sum(get_general_stats(c)[attr] for c in cards) for pid, cards in room["locked_cards"].items()}
    sorted_p = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    
    # 🔍 積分變數計算
    diff_1_2 = sorted_p[0][1] - sorted_p[1][1]
    diff_1_4 = sorted_p[0][1] - sorted_p[3][1]
    
    status_msg = ""
    pts_map = {0: 5, 1: 3, 2: 2, 3: 1}
    
    if diff_1_2 > 30: pts_map[0], status_msg = 8, "💥 爆擊：碾壓獲勝！"
    elif diff_1_2 < 5: pts_map[0], status_msg = 4, "😅 險勝：慘勝如敗..."
    
    is_total_defeat = diff_1_4 > 60
    if is_total_defeat: pts_map[3] = 0

    ranks = {}
    vault = room.get("dialogue_vault", {})
    for i, (pid, tot) in enumerate(sorted_p):
        rank_num = i + 1
        pts = pts_map.get(i, 0)
        room["scores"][pid] += pts
        room["decks"][pid] = [c for c in room["decks"][pid] if c not in room["locked_cards"][pid]]
        is_ai = pid.startswith("AI_")
        pers = room["ai_personalities"].get(pid, "")
        final_quote = vault.get(pers, {}).get(attr, {}).get(str(rank_num), "局勢難料...") if is_ai else ""
        
        tag = status_msg if rank_num == 1 else ("💀 完敗：軍心崩潰！" if rank_num == 4 and is_total_defeat else "")
        ranks[pid] = {
            "faction": room["players"].get(pid, pid.replace("AI_","")),
            "cards": room["locked_cards"][pid], "total": tot, "pts": pts, 
            "rank": rank_num, "is_ai": is_ai, "personality": pers, "quote": final_quote, "tag": tag
        }
    room.update({"last_attr": attr, "results": ranks, "status": "resolution_result"})

# ==========================================
# 🖥️ Streamlit 介面渲染
# ==========================================
def validate_id(raw):
    if not raw or not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{2,12}$", raw): raise ValueError("名號限 2~12 碼")
    return html.escape(raw)

def render_lobby():
    st.title("⚔️ 三國之巔：大廳")
    pid_in = st.text_input("👤 主公名號：", key="pid_input_box")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️ 建立戰局"):
            try:
                st.session_state.player_id = validate_id(pid_in)
                code = secrets.token_hex(3).upper()
                GLOBAL_ROOMS[code] = {"players": {}, "ai_factions": [], "status": "lobby", "round": 1, "decks": {}, "locked_cards": {}, "scores": {}, "ai_personalities": {}, "dialogue_vault": {}}
                st.session_state.current_room = code; st.rerun()
            except ValueError as e: st.error(e)

    st.divider()
    st.subheader("🟢 公開招募板")
    rooms = {c: d for c, d in GLOBAL_ROOMS.items() if d["status"] == "lobby"}
    if not rooms: st.info("目前無戰局")
    for c, d in rooms.items():
        if st.button(f"⚔️ 加入房間 {c} ({len(d['players'])}/4)", key=f"join_{c}"):
            try:
                st.session_state.player_id = validate_id(pid_in)
                st.session_state.current_room = c; st.rerun()
            except ValueError as e: st.error(e)

    with st.expander("📡 三雲端 AI 引擎診斷"):
        if st.button("🔌 測試動態路由"):
            with st.spinner("測試中..."):
                try:
                    res, model = call_ai_with_fallback("PING")
                    st.success(f"連線成功！當前大腦：{model}")
                except Exception as e: st.error(f"連線失敗：{e}")

def render_room():
    code, pid = st.session_state.current_room, st.session_state.player_id
    room = GLOBAL_ROOMS.get(code)
    if not room: st.session_state.current_room = None; st.rerun()

    st.title(f"🏰 房間：{code} | 第 {room['round']}/5 回合")

    if room["status"] == "lobby":
        st.write("🚩 請選定陣營：")
        cols = st.columns(4)
        for i, f in enumerate(VALID_FACTIONS):
            taken = f in room["players"].values()
            if cols[i].button(f"{f}" + (" (已選)" if taken else ""), disabled=taken, key=f"sel_{f}"):
                room["players"][pid] = f; st.rerun()
        
        if pid in room["players"] and st.button("🚀 開始遊戲", type="primary", use_container_width=True):
            with st.spinner("🔮 撰寫劇本中..."):
                taken_f = list(room["players"].values())
                room["ai_factions"] = [f for f in VALID_FACTIONS if f not in taken_f]
                for p_id, faction in room["players"].items():
                    room["decks"][p_id], room["scores"][p_id] = list(FACTION_ROSTERS.get(faction, ["曹操"])), 0
                pers_pool = list(AI_PERSONALITIES.keys()); random.shuffle(pers_pool)
                ai_pers = []
                for af in room["ai_factions"]:
                    ai_id = f"AI_{af}"
                    p_name = pers_pool.pop()
                    room["ai_personalities"][ai_id], room["decks"][ai_id], room["scores"][ai_id] = p_name, list(FACTION_ROSTERS.get(af, ["曹操"])), 0
                    ai_pers.append(p_name)
                room["dialogue_vault"] = generate_dialogue_vault(ai_pers)
                room["status"] = "playing"; st.rerun()

    elif room["status"] == "playing":
        if pid not in room["decks"]: st.warning("👀 觀戰模式"); st.button("刷新")
        elif pid in room["locked_cards"]: st.info("🔒 鎖定中..."); st.button("刷新")
        else:
            df = pd.DataFrame([{"武將": n, **get_general_stats(n)} for n in room["decks"][pid]])
            ev = st.dataframe(df, on_select="rerun", selection_mode="multi-row", hide_index=True)
            if len(ev.selection.rows) == 3:
                names = df.iloc[ev.selection.rows]["武將"].tolist()
                if st.button(f"🔐 鎖定：{', '.join(names)}", type="primary", use_container_width=True):
                    room["locked_cards"][pid] = names
                    for af in room["ai_factions"]:
                        ai_key = f"AI_{af}"
                        room["locked_cards"][ai_key] = get_ai_cards_local(room["decks"][ai_key], room["ai_personalities"][ai_key])
                    if len(room["locked_cards"]) == 4: room["status"] = "resolution_pending"
                    st.rerun()

    elif room["status"] == "resolution_pending":
        if st.button("🎲 擲骰子結算", type="primary", use_container_width=True): resolve_round(code); st.rerun()

    elif room["status"] == "resolution_result":
        st.header(f"🎲 比拼屬性：【{room['last_attr']}】")
        for p, r in sorted(room["results"].items(), key=lambda x: x[1]['rank']):
            bg = "🟢" if p == pid else "⚪"
            name = f"{r['personality']} ({r['faction']})" if r["is_ai"] else f"主公 {p} ({r['faction']})"
            st.write(f"#### {bg} 第 {r['rank']} 名: {name} (+{r['pts']}分) **{r['tag']}**")
            
            if r["is_ai"]:
                avatar = AVATAR_FILES.get(r['personality'], {}).get(r['rank'], "")
                c1, c2 = st.columns([1, 6])
                with c1:
                    if os.path.exists(avatar): st.image(avatar, use_container_width=True)
                    else: st.write("🎭")
                with c2: st.info(f"「{r['quote']}」")
            st.write(f"出戰：{', '.join(r['cards'])} (總和 {r['total']})")
            st.divider()

        # 📊 恢復顯示總分排名
        st.subheader("📊 目前累積功勳榜")
        score_data = []
        for rank, (p_id, s) in enumerate(sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)):
            is_ai = p_id.startswith("AI_")
            display_name = f"{room['ai_personalities'].get(p_id)} ({room['players'].get(p_id, p_id.replace('AI_',''))})" if is_ai else f"主公 {p_id}"
            score_data.append({"排名": f"第 {rank+1} 名", "名號 (陣營)": display_name, "累積總分": int(s)})
        st.table(score_data)

        if pid in room["decks"] and st.button("⏭️ 下一回合", type="primary", use_container_width=True):
            room["locked_cards"] = {}
            if room["round"] >= 5: room["status"] = "finished"
            else: room["round"] += 1; room["status"] = "playing"
            st.rerun()

    elif room["status"] == "finished":
        st.balloons(); st.header("🏆 戰局結束")
        for p, s in sorted(room["scores"].items(), key=lambda x: x[1], reverse=True):
            st.subheader(f"{p}: {s} 分")
        if st.button("🚪 返回大廳"): st.session_state.current_room = None; st.rerun()

if st.session_state.current_room: render_room()
else: render_lobby()
