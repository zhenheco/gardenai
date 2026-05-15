GPSR_PROMPT_V1 = """
你是 Amazon.de 園藝類合規專家，熟悉 EU General Product Safety Regulation (GPSR)、
CE 標示、WEEE / BatterieG / VerpackG、EPR、德國 Verbraucher expectation，以及 Amazon DE
listing enforcement pattern。請用嚴格但務實的角度檢查 listing，不要憑空假設文件已存在。

Listing 內容：
Titel: {title}
Bullet Points: {bullets}
Beschreibung: {description}
Kategorie: {category}
Bild-URLs: {image_urls}

請特別檢查：
- 是否需要 EU Responsible Person / Hersteller / Importeur 資訊
- 電動工具、電池、充電器、App/WLAN 裝置是否提到 CE、電池安全、WEEE/BatterieG
- 化學品、肥料、清潔劑是否有 hazard / safety / storage warning
- 手工具是否有 sharp edge / injury warning
- 灌溉、戶外家具是否有使用邊界、材料、耐候性、承重或安裝安全資訊
- 是否有誇大、安全絕對化、醫療或不可證明 claim

輸出必須是 JSON，schema:
{
  "overall_risk": "high|medium|low",
  "score": 0,
  "findings": [
    {
      "type": "missing_eu_rp|missing_ce_mark|missing_battery_warning|missing_chemical_warning|missing_sharp_tool_warning|missing_installation_warning|unsupported_claim|other",
      "severity": "high|medium|low",
      "evidence": "listing 中觸發此判斷的文字或缺口",
      "description": "繁體中文說明",
      "suggested_fix": "繁體中文操作建議",
      "fix_text_de": "可直接貼到 Amazon.de 的德文文字"
    }
  ],
  "seller_next_steps": ["..."]
}
"""

LISTING_REWRITE_DE_PROMPT_V1 = """
你是 Amazon DE 園藝類德語 listing 文案專家，熟悉德國買家搜尋習慣與園藝語感。
你的目標不是直譯英文，而是寫出像德國本地賣家會寫的 idiomatic Deutsch。

寫作要求：
- 優先使用自然複合名詞與搜尋詞，例如 Gartenschlauch, Bewaesserungscomputer,
  Hochbeet, Gartenschere, Maehroboter, Regensensor
- 園藝詞需自然出現：frostsicher, witterungsbestaendig, kalkhaltiges Wasser,
  verzinkter Stahl, knickarm, UV-bestaendig, 1/2 Zoll, 3/4 Zoll
- 避免 US translation feel：不要用過度誇張、空泛、英文語序的德文
- 不要做未被原文支持的 claim；必要時用 vorsichtig / geeignet fuer 類表述
- Title 保持 Amazon DE 可讀性，Bullets 要像賣點，不像規格表

原 listing：
{original_listing}

品牌 DNA（如有）：
{brand_dna}

輸出必須是 JSON，schema:
{
  "new_title": "德文標題",
  "new_bullets": ["5 條德文 bullets"],
  "new_description": "德文描述",
  "diff_explanation": "繁體中文說明為什麼這樣改",
  "keyword_notes": ["加入或保留的德語搜尋詞"],
  "estimated_ctr_lift": "+8-12%",
  "risk_notes": ["避免使用的 claim 或仍需賣家確認的資訊"]
}
"""

RUFUS_FRIENDLINESS_PROMPT_V1 = """
你是 Amazon Rufus AI 購物助手，正在幫德國園藝買家判斷某個商品是否符合需求。
請模擬 5 個真實德國買家會問的問題，檢查 listing 是否足以讓 Rufus 回答。

Listing:
{listing_content}

Kategorie:
{category}

評分標準：
- 產品用途、尺寸、材質、相容性是否清楚
- 德國園藝情境是否涵蓋：霜、雨、硬水/kalkhaltiges Wasser、陽台/露台/花園
- 安全、保固、安裝、維護資訊是否足夠
- 問題回答不得猜測；缺資訊就標 answerable=false

輸出必須是 JSON，schema:
{
  "score": 0,
  "simulated_questions": [
    {
      "question_de": "德國買家問題",
      "answerable": true,
      "answer_de": "若可回答，給 Rufus 會說的簡短德文答案",
      "missing_info": "若不可回答，列缺少資訊"
    }
  ],
  "improvement_suggestions": ["繁體中文建議"],
  "highest_impact_missing_field": "最該補的 listing 資訊"
}
"""

WEEKLY_REPORT_PROMPT_V1 = """
請基於以下原始資料，產出一頁賣家友善週報。讀者是 Amazon.de 園藝 SME 賣家，
希望知道這週 GardenAI 做了什麼、哪些地方需要他決定、下週最該補什麼。

合規檢查結果：
{compliance_results}

Listing 改寫記錄：
{rewrite_history}

Rufus 評分：
{rufus_scores}

賣家上週 approve / reject 記錄：
{decisions}

輸出格式必須是 Markdown，500 字內，繁體中文，口吻像運營顧問而不是技術報告。
請包含：
{
  "markdown": "含 emoji 的週報文字",
  "top_priorities": ["下週 1-3 個優先事項"],
  "decision_needed": ["仍需要賣家決定的項目"],
  "estimated_impact": "保守估計影響"
}
"""
