"""
单词提取：
从单元pdf中提取 txt 文档
转成 json, csv, (添加id)
最终输出三种文件: txt, json, csv
"""



import re
import json
import csv
from pathlib import Path
import fitz  # pymupdf


# ========= 配置 =========

PDF_PATH = "data/raw/unit1.pdf"
UNIT = "u1"
OUTPUT_TXT = "unit1_raw_text.txt"
OUTPUT_JSON = "unit1_parsed.json"
OUTPUT_CSV = "unit1_parsed.csv"

LABEL_EXAMPLE = "情景例句"
LABEL_VISUAL = "视觉音节"
LABEL_PHONETIC = "音素拆分"
LABEL_COLLOC = "常见组合"

ALL_LABELS = {LABEL_EXAMPLE, LABEL_VISUAL, LABEL_PHONETIC, LABEL_COLLOC}


# ========= PDF -> TXT =========
def extract_pdf_to_txt(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        text = normalize_text(text)
        pages.append(f"===== PAGE {i} =====\n{text}")

    return "\n\n".join(pages)


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ========= 切块 =========
def clean(line: str) -> str:
    return line.strip()


def is_entry_start(line: str) -> bool:
    line = clean(line)

    if not line:
        return False

    if line.startswith("===== PAGE"):
        return False

    if line in {"情景例句", "视觉音节", "音素拆分", "常见组合"}:
        return False

    if line.startswith("/") and line.endswith("/"):
        return False

    # 含中文排除
    if re.search(r"[\u4e00-\u9fff]", line):
        return False

    # ⭐ 核心规则：emoji + 英文
    return bool(re.match(r"^[^A-Za-z\s]+ ?[A-Za-z][A-Za-z \-']*[A-Za-z]?$", line))


def normalize_word(line: str) -> str:
    m = re.search(r"([A-Za-z][A-Za-z \-']*[A-Za-z]?)$", line)
    return m.group(1).strip() if m else line


def split_entries(text: str):
    lines = text.splitlines()

    entries = []
    current = []

    for raw in lines:
        line = clean(raw)
        if not line:
            continue

        if is_entry_start(line):
            if current:
                entries.append(current)
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        entries.append(current)

    return entries


# ========= 解析 =========
def collect(lines, start):
    result = []
    i = start

    while i < len(lines):
        line = lines[i]

        # ⭐ 新增：遇到新页面，停止
        if line.startswith("===== PAGE"):
            break

        # 原有：遇到标签，停止
        if line in ALL_LABELS:
            break

        result.append(line)
        i += 1

    return result, i


def parse_entry(block):
    lines = [clean(x) for x in block if clean(x)]

    data = {
        "id": "",
        "word": "",
        "ipa": "",
        "pos": "",
        "cn": "",
        "example_en": "",
        "example_zh": "",
        "visual_syllables": [],
        "phonetic_parts": "",
        "collocations": [],
    }

    if not lines:
        return data

    data["word"] = normalize_word(lines[0])

    # ipa
    for l in lines[:5]:
        if l.startswith("/") and "/" in l[1:]:
            data["ipa"] = l
            break

    # pos + cn
    for l in lines:
        m = re.match(r"^(n\.|v\.|adj\.|adv\.|phr\.|phrase\.)\s*(.*)", l)
        if m:
            data["pos"] = m.group(1)
            data["cn"] = m.group(2)
            break

    i = 0
    while i < len(lines):
        l = lines[i]

        if l == LABEL_EXAMPLE:
            j = i + 1
            en_lines = []
            zh_lines = []

            # 先收集情景例句区域，直到下一个标签
            vals, new_i = collect(lines, j)

            # 英文在前，中文在后
            in_zh = False
            for val in vals:
                if re.search(r"[\u4e00-\u9fff]", val):
                    in_zh = True

                if in_zh:
                    zh_lines.append(val)
                else:
                    en_lines.append(val)

            data["example_en"] = " ".join(en_lines).strip()
            data["example_zh"] = "".join(zh_lines).strip()

            i = new_i
            continue

        if l == LABEL_VISUAL:
            vals, i = collect(lines, i + 1)
            data["visual_syllables"] = vals
            continue

        if l == LABEL_PHONETIC:
            if i + 1 < len(lines):
                data["phonetic_parts"] = lines[i + 1]
            i += 2
            continue

        if l == LABEL_COLLOC:
            vals, i = collect(lines, i + 1)
            text = " ".join(vals)
            text = re.sub(r"\s+", " ", text)
            data["collocations"] = [
                x.strip() for x in re.split(r"[;；]", text) if x.strip()
            ]
            continue

        i += 1

    return data


# ========= 加 ID =========
def add_ids(data):
    for i, item in enumerate(data, start=1):
        item["id"] = f"{UNIT}_{i:03d}"
    return data


# ========= 保存 =========
def save_json(data):
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(data):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            "id",
            "word",
            "ipa",
            "pos",
            "cn",
            "example_en",
            "example_zh",
            "visual_syllables",
            "phonetic_parts",
            "collocations",
        ])

        for d in data:
            writer.writerow([
                d["id"],
                d["word"],
                d["ipa"],
                d["pos"],
                d["cn"],
                d["example_en"],
                d["example_zh"],
                "|".join(d["visual_syllables"]),
                d["phonetic_parts"],
                "|".join(d["collocations"]),
            ])


# ========= 主函数 =========
def main():
    print("📄 Step 1: PDF -> TXT")
    text = extract_pdf_to_txt(PDF_PATH)

    Path(OUTPUT_TXT).write_text(text, encoding="utf-8")

    print("📦 Step 2: 解析词条")
    blocks = split_entries(text)
    data = [parse_entry(b) for b in blocks]

    data = [d for d in data if d["word"]]
    data = add_ids(data)

    print("💾 Step 3: 保存 JSON + CSV")
    save_json(data)
    save_csv(data)

    print("\n✅ 完成！生成文件：")
    print(f"- {OUTPUT_TXT}")
    print(f"- {OUTPUT_JSON}")
    print(f"- {OUTPUT_CSV}")

    print("\n🔍 前3条预览：")
    for d in data[:3]:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        print("-" * 50)


if __name__ == "__main__":
    main()