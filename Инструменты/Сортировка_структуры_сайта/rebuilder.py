import os
import shutil
import json
import requests
from bs4 import BeautifulSoup

# Загружаем конфиг
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

INPUT_DIR = CONFIG["input_dir"]
OUTPUT_DIR = CONFIG["output_dir"]

def clean_html(html_content):
    """Удаляем баннеры Wayback и лишние <script>, переписываем пути"""
    soup = BeautifulSoup(html_content, "html.parser")

    if CONFIG.get("remove_wayback_banner", True):
        for banner in soup.select("#wm-ipp, .wayback-toolbar"):
            banner.decompose()

    if CONFIG.get("remove_scripts", True):
        for script in soup.find_all("script"):
            if "wombat" in str(script) or "archive.org" in str(script):
                script.decompose()

    # Переписываем пути
    for tag in soup.find_all(["link", "script", "img", "a"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        if tag.has_attr(attr):
            val = tag[attr]
            fname = os.path.basename(val)
            if val.endswith(".css"):
                tag[attr] = f"/{CONFIG['css_dir']}/{fname}"
            elif val.endswith(".js"):
                tag[attr] = f"/{CONFIG['js_dir']}/{fname}"
            elif val.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                tag[attr] = f"/{CONFIG['img_dir']}/{fname}"
            elif val.lower().endswith(("index.html", "index.htm")):
                tag[attr] = "/index.html"
            elif val.lower().endswith((".html", ".htm", ".php", ".asp")):
                tag[attr] = f"/{CONFIG['html_dir']}/{fname}"

    return str(soup)

def validate_links(soup):
    """Проверяем внешние ссылки"""
    broken = []
    for tag in soup.find_all(["a", "img", "link", "script"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        url = tag.get(attr)
        if url and url.startswith("http"):
            try:
                r = requests.head(url, timeout=5)
                if r.status_code >= 400:
                    broken.append(url)
            except Exception:
                broken.append(url)
    return broken

def process_html_file(src_path, dst_path):
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    cleaned = clean_html(html)
    soup = BeautifulSoup(cleaned, "html.parser")

    if CONFIG.get("validate_links", False):
        broken = validate_links(soup)
        if broken:
            print(f"[!] Broken links in {src_path}:")
            for b in broken:
                print("   -", b)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

def rebuild_site():
    # Очищаем выходную папку
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Создаём структуру
    html_dir = os.path.join(OUTPUT_DIR, CONFIG["html_dir"])
    css_dir  = os.path.join(OUTPUT_DIR, CONFIG["css_dir"])
    js_dir   = os.path.join(OUTPUT_DIR, CONFIG["js_dir"])
    img_dir  = os.path.join(OUTPUT_DIR, CONFIG["img_dir"])

    os.makedirs(html_dir)
    os.makedirs(css_dir)
    os.makedirs(js_dir)
    os.makedirs(img_dir)

    # Рекурсивный обход всего архива
    for root, _, files in os.walk(INPUT_DIR):
        for file in files:
            src_path = os.path.join(root, file)
            print("Нашёл:", src_path)

            if file.lower() == "index.html":
                # Главный индекс в корень
                dst_path = os.path.join(OUTPUT_DIR, "index.html")
                process_html_file(src_path, dst_path)

            elif file.lower().endswith((".html", ".htm", ".php", ".asp")):
                dst_path = os.path.join(html_dir, file)
                process_html_file(src_path, dst_path)

            elif file.lower().endswith(".css"):
                shutil.copy2(src_path, os.path.join(css_dir, file))

            elif file.lower().endswith(".js"):
                shutil.copy2(src_path, os.path.join(js_dir, file))

            elif file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                shutil.copy2(src_path, os.path.join(img_dir, file))

    print(f"✅ Сайт пересобран в {OUTPUT_DIR}")

if __name__ == "__main__":
    rebuild_site()
