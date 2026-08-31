# coding=utf-8

import json
import os
import random
import re
import time
import webbrowser
import smtplib
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

import pytz
import requests
import yaml


VERSION = "3.0.7"  # 修改版本号


# === SMTP邮件配置 ===
SMTP_CONFIGS = {
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "encryption": "TLS"},
    "qq.com": {"server": "smtp.qq.com", "port": 465, "encryption": "SSL"},
    "outlook.com": {
        "server": "smtp-mail.outlook.com",
        "port": 587,
        "encryption": "TLS",
    },
    "hotmail.com": {
        "server": "smtp-mail.outlook.com",
        "port": 587,
        "encryption": "TLS",
    },
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    "163.com": {"server": "smtp.163.com", "port": 465, "encryption": "SSL"},
    "126.com": {"server": "smtp.126.com", "port": 465, "encryption": "SSL"},
    "sina.com": {"server": "smtp.sina.com", "port": 465, "encryption": "SSL"},
    "sohu.com": {"server": "smtp.sohu.com", "port": 465, "encryption": "SSL"},
}


# === 配置管理 ===
def load_config():
    """加载配置文件"""
    config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")

    if not Path(config_path).exists():
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    print(f"配置文件加载成功: {config_path}")

    config = {
        "VERSION_CHECK_URL": config_data["app"]["version_check_url"],
        "SHOW_VERSION_UPDATE": config_data["app"]["show_version_update"],
        "REQUEST_INTERVAL": config_data["crawler"]["request_interval"],
        "REPORT_MODE": os.environ.get("REPORT_MODE", "").strip()
        or config_data["report"]["mode"],
        "RANK_THRESHOLD": config_data["report"]["rank_threshold"],
        "USE_PROXY": config_data["crawler"]["use_proxy"],
        "DEFAULT_PROXY": config_data["crawler"]["default_proxy"],
        "ENABLE_CRAWLER": os.environ.get("ENABLE_CRAWLER", "").strip().lower()
        in ("true", "1")
        if os.environ.get("ENABLE_CRAWLER", "").strip()
        else config_data["crawler"]["enable_crawler"],
        "ENABLE_NOTIFICATION": os.environ.get("ENABLE_NOTIFICATION", "").strip().lower()
        in ("true", "1")
        if os.environ.get("ENABLE_NOTIFICATION", "").strip()
        else config_data["notification"]["enable_notification"],
        "MESSAGE_BATCH_SIZE": config_data["notification"]["message_batch_size"],
        "DINGTALK_BATCH_SIZE": config_data["notification"].get(
            "dingtalk_batch_size", 20000
        ),
        "FEISHU_BATCH_SIZE": config_data["notification"].get("feishu_batch_size", 29000),
        "BATCH_SEND_INTERVAL": config_data["notification"]["batch_send_interval"],
        "FEISHU_MESSAGE_SEPARATOR": config_data["notification"][
            "feishu_message_separator"
        ],
        "PUSH_WINDOW": {
            "ENABLED": os.environ.get("PUSH_WINDOW_ENABLED", "").strip().lower()
            in ("true", "1")
            if os.environ.get("PUSH_WINDOW_ENABLED", "").strip()
            else config_data["notification"]
            .get("push_window", {})
            .get("enabled", False),
            "TIME_RANGE": {
                "START": os.environ.get("PUSH_WINDOW_START", "").strip()
                or config_data["notification"]
                .get("push_window", {})
                .get("time_range", {})
                .get("start", "08:00"),
                "END": os.environ.get("PUSH_WINDOW_END", "").strip()
                or config_data["notification"]
                .get("push_window", {})
                .get("time_range", {})
                .get("end", "22:00"),
            },
            "ONCE_PER_DAY": os.environ.get("PUSH_WINDOW_ONCE_PER_DAY", "").strip().lower()
            in ("true", "1")
            if os.environ.get("PUSH_WINDOW_ONCE_PER_DAY", "").strip()
            else config_data["notification"]
            .get("push_window", {})
            .get("once_per_day", True),
            "RECORD_RETENTION_DAYS": int(
                os.environ.get("PUSH_WINDOW_RETENTION_DAYS", "").strip() or "0"
            )
            or config_data["notification"]
            .get("push_window", {})
            .get("push_record_retention_days", 7),
        },
        "WEIGHT_CONFIG": {
            "RANK_WEIGHT": config_data["weight"]["rank_weight"],
            "FREQUENCY_WEIGHT": config_data["weight"]["frequency_weight"],
            "HOTNESS_WEIGHT": config_data["weight"]["hotness_weight"],
        },
        "PLATFORMS": config_data["platforms"],
    }

    notification = config_data.get("notification", {})
    webhooks = notification.get("webhooks", {})

    config["FEISHU_WEBHOOK_URL"] = os.environ.get(
        "FEISHU_WEBHOOK_URL", ""
    ).strip() or webhooks.get("feishu_url", "")
    config["DINGTALK_WEBHOOK_URL"] = os.environ.get(
        "DINGTALK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("dingtalk_url", "")
    config["WEWORK_WEBHOOK_URL"] = os.environ.get(
        "WEWORK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("wework_url", "")
    config["TELEGRAM_BOT_TOKEN"] = os.environ.get(
        "TELEGRAM_BOT_TOKEN", ""
    ).strip() or webhooks.get("telegram_bot_token", "")
    config["TELEGRAM_CHAT_ID"] = os.environ.get(
        "TELEGRAM_CHAT_ID", ""
    ).strip() or webhooks.get("telegram_chat_id", "")

    config["EMAIL_FROM"] = os.environ.get("EMAIL_FROM", "").strip() or webhooks.get(
        "email_from", ""
    )
    config["EMAIL_PASSWORD"] = os.environ.get(
        "EMAIL_PASSWORD", ""
    ).strip() or webhooks.get("email_password", "")
    config["EMAIL_TO"] = os.environ.get("EMAIL_TO", "").strip() or webhooks.get(
        "email_to", ""
    )
    config["EMAIL_SMTP_SERVER"] = os.environ.get(
        "EMAIL_SMTP_SERVER", ""
    ).strip() or webhooks.get("email_smtp_server", "")
    config["EMAIL_SMTP_PORT"] = os.environ.get(
        "EMAIL_SMTP_PORT", ""
    ).strip() or webhooks.get("email_smtp_port", "")

    config["NTFY_SERVER_URL"] = os.environ.get(
        "NTFY_SERVER_URL", "https://ntfy.sh"
    ).strip() or webhooks.get("ntfy_server_url", "https://ntfy.sh")
    config["NTFY_TOPIC"] = os.environ.get("NTFY_TOPIC", "").strip() or webhooks.get(
        "ntfy_topic", ""
    )
    config["NTFY_TOKEN"] = os.environ.get("NTFY_TOKEN", "").strip() or webhooks.get(
        "ntfy_token", ""
    )

    notification_sources = []
    if config["FEISHU_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("FEISHU_WEBHOOK_URL") else "配置文件"
        notification_sources.append(f"飞书({source})")
    if config["DINGTALK_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("DINGTALK_WEBHOOK_URL") else "配置文件"
        notification_sources.append(f"钉钉({source})")
    if config["WEWORK_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("WEWORK_WEBHOOK_URL") else "配置文件"
        notification_sources.append(f"企业微信({source})")
    if config["TELEGRAM_BOT_TOKEN"] and config["TELEGRAM_CHAT_ID"]:
        token_source = (
            "环境变量" if os.environ.get("TELEGRAM_BOT_TOKEN") else "配置文件"
        )
        chat_source = "环境变量" if os.environ.get("TELEGRAM_CHAT_ID") else "配置文件"
        notification_sources.append(f"Telegram({token_source}/{chat_source})")
    if config["EMAIL_FROM"] and config["EMAIL_PASSWORD"] and config["EMAIL_TO"]:
        from_source = "环境变量" if os.environ.get("EMAIL_FROM") else "配置文件"
        notification_sources.append(f"邮件({from_source})")
    if config["NTFY_SERVER_URL"] and config["NTFY_TOPIC"]:
        server_source = "环境变量" if os.environ.get("NTFY_SERVER_URL") else "配置文件"
        notification_sources.append(f"ntfy({server_source})")

    if notification_sources:
        print(f"通知渠道配置来源: {', '.join(notification_sources)}")
    else:
        print("未配置任何通知渠道")

    return config


print("正在加载配置...")
CONFIG = load_config()
print(f"TrendRadar v{VERSION} 配置加载完成")
print(f"监控平台数量: {len(CONFIG['PLATFORMS'])}")


# === 工具函数 ===
def get_beijing_time():
    return datetime.now(pytz.timezone("Asia/Shanghai"))


def format_date_folder():
    return get_beijing_time().strftime("%Y年%m月%d日")


def format_time_filename():
    return get_beijing_time().strftime("%H时%M分")


def clean_title(title: str) -> str:
    if not isinstance(title, str):
        title = str(title)
    cleaned_title = title.replace("\n", " ").replace("\r", " ")
    cleaned_title = re.sub(r"\s+", " ", cleaned_title)
    cleaned_title = cleaned_title.strip()
    return cleaned_title


def ensure_directory_exists(directory: str):
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_output_path(subfolder: str, filename: str) -> str:
    date_folder = format_date_folder()
    output_dir = Path("output") / date_folder / subfolder
    ensure_directory_exists(str(output_dir))
    return str(output_dir / filename)


def check_version_update(
    current_version: str, version_url: str, proxy_url: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    try:
        proxies = None
        if proxy_url:
            proxies = {"http": proxy_url, "https": proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/plain, */*",
            "Cache-Control": "no-cache",
        }

        response = requests.get(
            version_url, proxies=proxies, headers=headers, timeout=10
        )
        response.raise_for_status()
        remote_version = response.text.strip()
        print(f"当前版本: {current_version}, 远程版本: {remote_version}")

        def parse_version(version_str):
            try:
                parts = version_str.strip().split(".")
                if len(parts) != 3:
                    raise ValueError("版本号格式不正确")
                return int(parts[0]), int(parts[1]), int(parts[2])
            except:
                return 0, 0, 0

        current_tuple = parse_version(current_version)
        remote_tuple = parse_version(remote_version)
        need_update = current_tuple < remote_tuple
        return need_update, remote_version if need_update else None
    except Exception as e:
        print(f"版本检查失败: {e}")
        return False, None


def is_first_crawl_today() -> bool:
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"
    if not txt_dir.exists():
        return True
    files = sorted([f for f in txt_dir.iterdir() if f.suffix == ".txt"])
    return len(files) <= 1


def html_escape(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# === 推送记录管理 ===
class PushRecordManager:
    def __init__(self):
        self.record_dir = Path("output") / ".push_records"
        self.ensure_record_dir()
        self.cleanup_old_records()

    def ensure_record_dir(self):
        self.record_dir.mkdir(parents=True, exist_ok=True)

    def get_today_record_file(self) -> Path:
        today = get_beijing_time().strftime("%Y%m%d")
        return self.record_dir / f"push_record_{today}.json"

    def cleanup_old_records(self):
        retention_days = CONFIG["PUSH_WINDOW"]["RECORD_RETENTION_DAYS"]
        current_time = get_beijing_time()
        for record_file in self.record_dir.glob("push_record_*.json"):
            try:
                date_str = record_file.stem.replace("push_record_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")
                file_date = pytz.timezone("Asia/Shanghai").localize(file_date)
                if (current_time - file_date).days > retention_days:
                    record_file.unlink()
            except Exception:
                pass

    def has_pushed_today(self) -> bool:
        record_file = self.get_today_record_file()
        if not record_file.exists():
            return False
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                record = json.load(f)
            return record.get("pushed", False)
        except Exception:
            return False

    def record_push(self, report_type: str):
        record_file = self.get_today_record_file()
        now = get_beijing_time()
        record = {
            "pushed": True,
            "push_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": report_type,
        }
        try:
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存推送记录失败: {e}")

    def is_in_time_range(self, start_time: str, end_time: str) -> bool:
        now = get_beijing_time()
        current_time = now.strftime("%H:%M")
        def normalize_time(time_str: str) -> str:
            try:
                parts = time_str.strip().split(":")
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            except:
                return time_str
        return normalize_time(start_time) <= normalize_time(current_time) <= normalize_time(end_time)


# === 数据获取 ===
class DataFetcher:
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    @staticmethod
    def _xml_text(element: Optional[ET.Element]) -> str:
        if element is None:
            return ""
        text = "".join(element.itertext()).strip()
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _xml_child(element: ET.Element, name: str) -> Optional[ET.Element]:
        for child in list(element):
            if child.tag.rsplit("}", 1)[-1] == name:
                return child
        return None

    def _fetch_rss_data(self, source: Dict, proxies: Optional[Dict], headers: Dict) -> str:
        response = requests.get(source["url"], proxies=proxies, headers=headers, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        rss_items = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "item"]
        atom_entries = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "entry"]
        feed_items = rss_items or atom_entries
        items = []
        for entry in feed_items[: int(source.get("max_items", 30))]:
            title = self._xml_text(self._xml_child(entry, "title"))
            link_element = self._xml_child(entry, "link")
            link = self._xml_text(link_element)
            if not link and link_element is not None:
                link = link_element.get("href", "")
            if title:
                items.append({"title": title, "url": link, "mobileUrl": link})
        if not items:
            raise ValueError("RSS feed contains no readable items")
        return json.dumps({"status": "success", "items": items}, ensure_ascii=False)

    def fetch_data(self, id_info: Union[str, Tuple[str, str]], max_retries: int = 2, min_retry_wait: int = 3, max_retry_wait: int = 5) -> Tuple[Optional[str], str, str]:
        source = id_info if isinstance(id_info, dict) else None
        if source:
            id_value = source["id"]
            alias = source.get("name", id_value)
        elif isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value
        url = f"https://newsnow.busiyi.world/api/s?id={id_value}&latest"
        proxies = {"http": self.proxy_url, "https": self.proxy_url} if self.proxy_url else None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
        }
        retries = 0
        while retries <= max_retries:
            try:
                if source and source.get("type") == "rss":
                    return self._fetch_rss_data(source, proxies, headers), id_value, alias
                response = requests.get(url, proxies=proxies, headers=headers, timeout=10)
                response.raise_for_status()
                data_json = response.json()
                if data_json.get("status") in ["success", "cache"]:
                    return response.text, id_value, alias
                raise ValueError(f"Status: {data_json.get('status')}")
            except Exception as e:
                retries += 1
                time.sleep(random.uniform(min_retry_wait, max_retry_wait))
        return None, id_value, alias

    def crawl_websites(self, ids_list: List, request_interval: int = CONFIG["REQUEST_INTERVAL"]) -> Tuple[Dict, Dict, List]:
        results = {}
        id_to_name = {}
        failed_ids = []
        for i, id_info in enumerate(ids_list):
            if isinstance(id_info, dict):
                id_value = id_info["id"]
                name = id_info.get("name", id_value)
            else:
                id_value = id_info[0] if isinstance(id_info, tuple) else id_info
                name = id_info[1] if isinstance(id_info, tuple) else id_value
            id_to_name[id_value] = name
            resp, _, _ = self.fetch_data(id_info)
            if resp:
                try:
                    data = json.loads(resp)
                    results[id_value] = {}
                    for idx, item in enumerate(data.get("items", []), 1):
                        title = item["title"]
                        if title in results[id_value]:
                            results[id_value][title]["ranks"].append(idx)
                        else:
                            results[id_value][title] = {
                                "ranks": [idx],
                                "url": item.get("url", ""),
                                "mobileUrl": item.get("mobileUrl", "")
                            }
                except:
                    failed_ids.append(id_value)
            else:
                failed_ids.append(id_value)
            if i < len(ids_list) - 1:
                time.sleep(request_interval / 1000)
        return results, id_to_name, failed_ids


# === 数据处理 ===
def save_titles_to_file(results: Dict, id_to_name: Dict, failed_ids: List) -> str:
    file_path = get_output_path("txt", f"{format_time_filename()}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        for id_value, title_data in results.items():
            name = id_to_name.get(id_value, id_value)
            f.write(f"{id_value} | {name}\n")
            sorted_titles = []
            for title, info in title_data.items():
                ranks = info.get("ranks", []) if isinstance(info, dict) else (info if isinstance(info, list) else [])
                rank = ranks[0] if ranks else 1
                sorted_titles.append((rank, clean_title(title), info.get("url","") if isinstance(info,dict) else "", info.get("mobileUrl","") if isinstance(info,dict) else ""))
            sorted_titles.sort(key=lambda x: x[0])
            for rank, t, u, m in sorted_titles:
                line = f"{rank}. {t}"
                if u: line += f" [URL:{u}]"
                if m: line += f" [MOBILE:{m}]"
                f.write(line + "\n")
            f.write("\n")
        if failed_ids:
            f.write("==== 以下ID请求失败 ====\n")
            for id_value in failed_ids:
                f.write(f"{id_value}\n")
    return file_path

def load_frequency_words(frequency_file: Optional[str] = None) -> Tuple[List[Dict], List[str]]:
    if frequency_file is None:
        frequency_file = os.environ.get("FREQUENCY_WORDS_PATH", "config/frequency_words.txt")
    if not Path(frequency_file).exists():
        return [], []
    with open(frequency_file, "r", encoding="utf-8") as f:
        content = f.read()
    groups, filters = [], []
    for g in content.split("\n\n"):
        if not g.strip(): continue
        req, norm = [], []
        for w in g.split("\n"):
            w = w.strip()
            if not w: continue
            if w.startswith("!"): filters.append(w[1:])
            elif w.startswith("+"): req.append(w[1:])
            else: norm.append(w)
        if req or norm:
            groups.append({"required": req, "normal": norm, "group_key": " ".join(norm) if norm else " ".join(req)})
    return groups, filters

def parse_file_titles(file_path: Path) -> Tuple[Dict, Dict]:
    titles_by_id = {}
    id_to_name = {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    for section in content.split("\n\n"):
        if not section.strip() or "失败" in section: continue
        lines = section.strip().split("\n")
        if len(lines) < 2: continue
        header = lines[0].split(" | ")
        sid = header[0].strip()
        id_to_name[sid] = header[1].strip() if len(header) > 1 else sid
        titles_by_id[sid] = {}
        for line in lines[1:]:
            if not line.strip(): continue
            try:
                parts = line.split(". ", 1)
                rank = int(parts[0]) if parts[0].isdigit() else 1
                rest = parts[1]
                url, mobile = "", ""
                if " [URL:" in rest:
                    rest, url = rest.split(" [URL:", 1)
                    url = url.rstrip("]")
                if " [MOBILE:" in rest:
                    rest, mobile = rest.split(" [MOBILE:", 1)
                    mobile = mobile.rstrip("]")
                titles_by_id[sid][clean_title(rest)] = {"ranks": [rank], "url": url, "mobileUrl": mobile}
            except: pass
    return titles_by_id, id_to_name

def read_all_today_titles(current_platform_ids: Optional[List[str]] = None) -> Tuple[Dict, Dict, Dict]:
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"
    if not txt_dir.exists(): return {}, {}, {}
    all_results, final_id_to_name, title_info = {}, {}, {}
    for f in sorted(txt_dir.glob("*.txt")):
        titles, names = parse_file_titles(f)
        if current_platform_ids:
            titles = {k: v for k, v in titles.items() if k in current_platform_ids}
            names = {k: v for k, v in names.items() if k in current_platform_ids}
        final_id_to_name.update(names)
        for sid, tdata in titles.items():
            process_source_data(sid, tdata, f.stem, all_results, title_info)
    return all_results, final_id_to_name, title_info

def process_source_data(source_id, title_data, time_info, all_results, title_info):
    if source_id not in all_results:
        all_results[source_id] = title_data
        if source_id not in title_info: title_info[source_id] = {}
        for t, d in title_data.items():
            title_info[source_id][t] = {"first_time": time_info, "last_time": time_info, "count": 1, **d}
    else:
        for t, d in title_data.items():
            if t not in all_results[source_id]:
                all_results[source_id][t] = d
                title_info[source_id][t] = {"first_time": time_info, "last_time": time_info, "count": 1, **d}
            else:
                exist = all_results[source_id][t]
                merged = list(set(exist["ranks"] + d["ranks"]))
                all_results[source_id][t] = {"ranks": merged, "url": exist["url"] or d["url"], "mobileUrl": exist["mobileUrl"] or d["mobileUrl"]}
                title_info[source_id][t].update({"last_time": time_info, "ranks": merged})
                title_info[source_id][t]["count"] += 1
                if not title_info[source_id][t]["url"]: title_info[source_id][t]["url"] = d["url"]

def detect_latest_new_titles(current_platform_ids: Optional[List[str]] = None) -> Dict:
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"
    if not txt_dir.exists() or len(list(txt_dir.glob("*.txt"))) < 2: return {}
    files = sorted(txt_dir.glob("*.txt"))
    latest, _ = parse_file_titles(files[-1])
    if current_platform_ids: latest = {k: v for k, v in latest.items() if k in current_platform_ids}
    history = set()
    for f in files[:-1]:
        h_data, _ = parse_file_titles(f)
        if current_platform_ids: h_data = {k: v for k, v in h_data.items() if k in current_platform_ids}
        for sid, tdata in h_data.items():
            for t in tdata: history.add(f"{sid}_{t}")
    new_titles = {}
    for sid, tdata in latest.items():
        for t, info in tdata.items():
            if f"{sid}_{t}" not in history:
                if sid not in new_titles: new_titles[sid] = {}
                new_titles[sid][t] = info
    return new_titles


# === 统计和分析 ===
def calculate_news_weight(title_data: Dict, rank_threshold: int = CONFIG["RANK_THRESHOLD"]) -> float:
    ranks = title_data.get("ranks", [])
    if not ranks: return 0.0
    count = title_data.get("count", len(ranks))
    wc = CONFIG["WEIGHT_CONFIG"]
    rank_score = sum(11 - min(r, 10) for r in ranks) / len(ranks)
    freq_score = min(count, 10) * 10
    hot_score = (sum(1 for r in ranks if r <= rank_threshold) / len(ranks)) * 100
    return rank_score * wc["RANK_WEIGHT"] + freq_score * wc["FREQUENCY_WEIGHT"] + hot_score * wc["HOTNESS_WEIGHT"]

def matches_word_groups(title: str, word_groups: List[Dict], filter_words: List[str]) -> bool:
    if not word_groups: return True
    t_lower = title.lower()
    if any(fw.lower() in t_lower for fw in filter_words): return False
    for g in word_groups:
        req, norm = g["required"], g["normal"]
        if req and not all(w.lower() in t_lower for w in req): continue
        if norm and not any(w.lower() in t_lower for w in norm): continue
        return True
    return False

def format_time_display(first, last):
    if not first: return ""
    return first if first == last or not last else f"[{first} ~ {last}]"

def format_rank_display(ranks, threshold, ftype):
    if not ranks: return ""
    ur = sorted(set(ranks))
    mn, mx = ur[0], ur[-1]
    if mn == mx: return f"[{mn}]"
    return f"[{mn} - {mx}]"

def count_word_frequency(
    results: Dict,
    word_groups: List[Dict],
    filter_words: List[str],
    id_to_name: Dict,
    title_info: Optional[Dict] = None,
    rank_threshold: int = CONFIG["RANK_THRESHOLD"],
    new_titles: Optional[Dict] = None,
    mode: str = "daily",
) -> Tuple[List[Dict], int]:
    """
    统计词频
    【需求1】随机推荐总量不超过 35 条
    【需求2】每组关键词热点：每个平台不超过 3 条
    """
    if not word_groups:
        word_groups = [{"required": [], "normal": [], "group_key": "全部新闻"}]
        filter_words = []

    is_first = is_first_crawl_today()
    if mode == "incremental":
        results_to_process = results if is_first else (new_titles or {})
        all_news_are_new = True
    elif mode == "current" and title_info:
         results_to_process = results 
         all_news_are_new = False
    else:
        results_to_process = results
        all_news_are_new = False

    word_stats = {g["group_key"]: {"count": 0, "titles": {}} for g in word_groups}
    total_titles = 0
    processed = {}
    
    # 用于记录每个平台是否匹配到了新闻，用于随机推荐逻辑
    platform_matched_counts = {sid: 0 for sid in results.keys()}

    # 第一步：收集所有匹配的新闻
    for source_id, titles_data in results_to_process.items():
        total_titles += len(titles_data)
        if source_id not in processed: processed[source_id] = {}

        for title, title_data in titles_data.items():
            if title in processed[source_id]: continue
            
            if not matches_word_groups(title, word_groups, filter_words): continue
            
            # 匹配成功
            platform_matched_counts[source_id] += 1
            
            # 归类
            group_key = word_groups[0]["group_key"]
            t_lower = title.lower()
            for g in word_groups:
                req, norm = g["required"], g["normal"]
                if req and not all(w.lower() in t_lower for w in req): continue
                if norm and not any(w.lower() in t_lower for w in norm): continue
                group_key = g["group_key"]
                break
            
            # 构建数据对象
            info = title_info.get(source_id, {}).get(title, {}) if title_info else {}
            ranks = info.get("ranks", title_data.get("ranks", [99]))
            url = info.get("url", title_data.get("url", ""))
            murl = info.get("mobileUrl", title_data.get("mobileUrl", ""))
            first = info.get("first_time", "")
            last = info.get("last_time", "")
            
            is_new = True if all_news_are_new else (new_titles and source_id in new_titles and title in new_titles[source_id])
            
            # 先存入字典，后续再根据平台限制过滤
            word_stats[group_key]["count"] += 1
            if source_id not in word_stats[group_key]["titles"]: word_stats[group_key]["titles"][source_id] = []
            
            word_stats[group_key]["titles"][source_id].append({
                "title": title, "source_name": id_to_name.get(source_id, source_id),
                "time_display": format_time_display(first, last), "count": info.get("count", 1),
                "ranks": ranks, "rank_threshold": rank_threshold,
                "url": url, "mobileUrl": murl, "is_new": is_new
            })
            processed[source_id][title] = True

    # 第二步：处理关键词分组，实施【需求2】每个平台不超过3条
    final_stats = []
    for k, v in word_stats.items():
        if v["count"] == 0: continue
        
        group_all_titles = []
        
        # 遍历该组下的每个平台
        for source_id, s_titles in v["titles"].items():
            # 先按权重排序该平台的新闻
            s_titles.sort(key=lambda x: (-calculate_news_weight(x, rank_threshold), min(x["ranks"]), -x["count"]))
            
            # 【需求2】截取前 3 条
            top_titles = s_titles[:3]
            
            group_all_titles.extend(top_titles)
            
        # 对所有平台汇总后的新闻再次按权重排序
        group_all_titles.sort(key=lambda x: (-calculate_news_weight(x, rank_threshold), min(x["ranks"]), -x["count"]))
        
        final_stats.append({"word": k, "count": len(group_all_titles), "titles": group_all_titles})

    # 第三步：处理随机推荐，实施【需求1】总量不超过35条
    random_candidates = []
    if mode != "incremental" or is_first:
        for source_id, count in platform_matched_counts.items():
            if count == 0 and source_id in results:
                all_items = list(results[source_id].items())
                # 从该平台提取候选
                for title, title_data in all_items:
                    random_candidates.append({
                        "title": title, "source_name": id_to_name.get(source_id, source_id),
                        "time_display": "", "count": 1, "ranks": title_data.get("ranks", [99]),
                        "rank_threshold": rank_threshold, "url": title_data.get("url", ""),
                        "mobileUrl": title_data.get("mobileUrl", ""), "is_new": False
                    })
        
        # 【需求1】从所有候选池中随机抽取至多 35 条
        final_random_count = min(len(random_candidates), 35)
        if final_random_count > 0:
            final_randoms = random.sample(random_candidates, final_random_count)
            # 为了展示美观，将随机结果简单排序（如按排名）
            final_randoms.sort(key=lambda x: min(x["ranks"]) if x["ranks"] else 99)
            
            final_stats.append({"word": "🎲 随机推荐 (猜你喜欢)", "count": len(final_randoms), "titles": final_randoms})

    # 最后按新闻总数排序分组
    final_stats.sort(key=lambda x: x["count"], reverse=True)
    return final_stats, total_titles


# === 报告生成 ===
def prepare_report_data(stats, failed_ids, new_titles, id_to_name, mode):
    processed_new = []
    if mode != "incremental" and new_titles:
        wg, fw = load_frequency_words()
        for sid, tdata in new_titles.items():
            sname = id_to_name.get(sid, sid)
            stitles = []
            for t, info in tdata.items():
                if matches_word_groups(t, wg, fw):
                    stitles.append({
                        "title": t, "source_name": sname, "url": info.get("url"), 
                        "ranks": info.get("ranks", []), "mobile_url": info.get("mobileUrl"),
                        "is_new": True, "time_display": "", "count": 1, "rank_threshold": CONFIG["RANK_THRESHOLD"]
                    })
            if stitles:
                processed_new.append({"source_name": sname, "titles": stitles})
    
    processed_stats = []
    for s in stats:
        if s["count"] <= 0: continue
        ptitles = []
        for t in s["titles"]:
            ptitles.append({"title": t["title"], "source_name": t["source_name"], "time_display": t["time_display"],
                            "count": t["count"], "ranks": t["ranks"], "rank_threshold": t["rank_threshold"],
                            "url": t.get("url",""), "mobile_url": t.get("mobileUrl",""), "is_new": t.get("is_new", False)})
        processed_stats.append({"word": s["word"], "count": s["count"], "titles": ptitles})
        
    return {"stats": processed_stats, "new_titles": processed_new, "failed_ids": failed_ids or [], "total_new_count": sum(len(s["titles"]) for s in processed_new)}

def format_title_for_platform(platform, title_data, show_source=True):
    # 简化的格式化函数，保留完整逻辑需引用原代码
    return title_data["title"] 

def generate_html_report(
    stats: List[Dict],
    total_titles: int,
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
    is_daily_summary: bool = False,
    update_info: Optional[Dict] = None,
    raw_data: Optional[Dict] = None,
) -> str:
    filename = "当日汇总.html" if is_daily_summary and mode == "daily" else f"{format_time_filename()}.html"
    if is_daily_summary and mode == "current": filename = "当前榜单汇总.html"
    file_path = get_output_path("html", filename)
    report_data = prepare_report_data(stats, failed_ids, new_titles, id_to_name, mode)
    
    html_content = render_html_content(report_data, total_titles, is_daily_summary, mode, update_info, raw_data, id_to_name)
    
    with open(file_path, "w", encoding="utf-8") as f: f.write(html_content)
    if is_daily_summary:
        with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)
    return file_path

def render_html_content(
    report_data: Dict,
    total_titles: int,
    is_daily_summary: bool = False,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    raw_data: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None
) -> str:
    """
    渲染 HTML，集成【需求1: 置顶新增】、【需求4: 全局搜索】、【新需求: 随机推荐沉底】
    """
    # 准备搜索数据
    search_list = []
    if raw_data:
        for sid, tdata in raw_data.items():
            sname = id_to_name.get(sid, sid) if id_to_name else sid
            for t, info in tdata.items():
                u = info.get("url") or info.get("mobileUrl") or ""
                search_list.append({"t": t, "u": u, "s": sname})
    search_json = json.dumps(search_list, ensure_ascii=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TrendRadar 热点追踪</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 16px; background: #fafafa; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 16px rgba(0,0,0,0.06); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .word-group {{ margin-bottom: 30px; }}
            .word-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 12px; }}
            .word-name {{ font-weight: 600; font-size: 18px; }}
            .news-item {{ display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; align-items: center; }}
            .news-num {{ min-width: 20px; color: #999; text-align: center; }}
            .news-link {{ color: #2563eb; text-decoration: none; }}
            .new-section {{ margin-bottom: 30px; padding: 15px; background: #fffbeb; border-radius: 8px; border: 1px solid #fcd34d; }}
            .new-title {{ color: #92400e; font-weight: bold; margin-bottom: 10px; }}
            .search-box {{ margin-bottom: 20px; position: relative; }}
            #search-input {{ width: 100%; padding: 10px; border: 2px solid #eee; border-radius: 8px; box-sizing: border-box; font-size: 14px; }}
            #search-results {{ display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #eee; border-radius: 8px; max-height: 300px; overflow-y: auto; z-index: 100; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .search-item {{ padding: 10px; border-bottom: 1px solid #f5f5f5; font-size: 13px; }}
            .search-item a {{ color: #333; text-decoration: none; display: block; }}
            .search-source {{ font-size: 12px; color: #999; margin-top: 2px; }}
            
            /* 随机推荐分隔样式 */
            .random-divider {{ margin: 40px 0 20px 0; border-top: 2px dashed #eee; text-align: center; position: relative; }}
            .random-divider span {{ background: #fff; padding: 0 15px; color: #999; position: relative; top: -10px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>TrendRadar 热点分析</h2>
                <div style="font-size:12px; opacity:0.8;">{get_beijing_time().strftime('%Y-%m-%d %H:%M')} · {total_titles} 条资讯</div>
            </div>
            <div class="content">
                <div class="search-box">
                    <input type="text" id="search-input" placeholder="🔍 搜索全网热点...">
                    <div id="search-results"></div>
                </div>

    """

    # 1. 新增热点 (置顶)
    if report_data["new_titles"]:
        html += f"""
                <div class="new-section">
                    <div class="new-title">🆕 本次新增热点 ({report_data['total_new_count']} 条)</div>
        """
        for source in report_data["new_titles"]:
            html += f"""<div style="margin-top:8px; font-weight:600; font-size:13px; color:#b45309;">{source['source_name']}</div>"""
            for idx, item in enumerate(source["titles"], 1):
                u = item.get('url') or item.get('mobile_url')
                link = f"<a href='{u}' target='_blank' style='color:#333;'>{item['title']}</a>" if u else item['title']
                html += f"""<div style="font-size:13px; margin-top:4px; padding-left:10px;">{idx}. {link}</div>"""
        html += "</div>"

    # --- 分离【普通热点】和【随机推荐】 ---
    normal_stats = []
    random_stats = []
    
    if report_data["stats"]:
        for stat in report_data["stats"]:
            if "随机" in stat["word"]:
                random_stats.append(stat)
            else:
                normal_stats.append(stat)

    # 2. 渲染普通热点
    for stat in normal_stats:
        word = html_escape(stat["word"])
        html += f"""
            <div class="word-group">
                <div class="word-header">
                    <div class="word-name">{word}</div>
                    <div style="font-size:12px; color:#666;">{stat['count']} 条</div>
                </div>
        """
        for idx, item in enumerate(stat["titles"], 1):
            u = item.get('url') or item.get('mobile_url')
            title_html = f"<a href='{u}' target='_blank' class='news-link'>{item['title']}</a>" if u else item['title']
            html += f"""
                <div class="news-item">
                    <div class="news-num">{idx}</div>
                    <div style="flex:1;">
                        <span style="color:#999; font-size:12px;">[{item['source_name']}]</span>
                        {title_html}
                    </div>
                </div>
            """
        html += "</div>"
        
    # 3. 渲染随机推荐 (沉底)
    if random_stats:
        html += """
            <div class="random-divider">
                <span>以下为随机推荐内容</span>
            </div>
        """
        for stat in random_stats:
            word = html_escape(stat["word"])
            html += f"""
                <div class="word-group">
                    <div class="word-header">
                        <div class="word-name" style="color:#059669;">{word}</div>
                        <div style="font-size:12px; color:#666;">{stat['count']} 条</div>
                    </div>
            """
            for idx, item in enumerate(stat["titles"], 1):
                u = item.get('url') or item.get('mobile_url')
                title_html = f"<a href='{u}' target='_blank' class='news-link'>{item['title']}</a>" if u else item['title']
                html += f"""
                    <div class="news-item">
                        <div class="news-num">{idx}</div>
                        <div style="flex:1;">
                            <span style="color:#999; font-size:12px;">[{item['source_name']}]</span>
                            {title_html}
                        </div>
                    </div>
                """
            html += "</div>"

    if report_data["failed_ids"]:
         html += f"<div style='color:red; font-size:12px; margin-top:20px; padding:10px; background:#fff1f2; border-radius:8px;'>⚠️ 获取失败: {', '.join(report_data['failed_ids'])}</div>"

    html += f"""
            </div>
            <div style="text-align:center; padding:20px; color:#999; font-size:12px; background:#f8f9fa;">
                Powered by TrendRadar v{VERSION}
            </div>
        </div>
        
        <script>
            const allData = {search_json};
            const input = document.getElementById('search-input');
            const results = document.getElementById('search-results');
            input.addEventListener('input', (e) => {{
                const val = e.target.value.trim().toLowerCase();
                if (!val) {{ results.style.display = 'none'; return; }}
                const filtered = allData.filter(i => i.t.toLowerCase().includes(val)).slice(0, 50);
                if (filtered.length > 0) {{
                    results.innerHTML = filtered.map(i => `
                        <div class="search-item">
                            <a href="${{i.u}}" target="_blank">${{i.t}}</a>
                            <div class="search-source">${{i.s}}</div>
                        </div>
                    `).join('');
                }} else {{ results.innerHTML = '<div style="padding:10px; text-align:center; color:#999;">无结果</div>'; }}
                results.style.display = 'block';
            }});
            document.addEventListener('click', (e) => {{
                if (!e.target.closest('.search-box')) results.style.display = 'none';
            }});
        </script>
    </body>
    </html>
    """
    return html

# === 主分析器 ===
class NewsAnalyzer:
    MODE_STRATEGIES = {
        "incremental": {"mode_name": "增量", "summary_mode": "daily", "should_send_realtime": True, "should_generate_summary": True, "realtime_report_type": "实时增量", "summary_report_type": "当日汇总", "description": "增量模式"},
        "current": {"mode_name": "当前榜单", "summary_mode": "current", "should_send_realtime": True, "should_generate_summary": True, "realtime_report_type": "实时榜单", "summary_report_type": "当前汇总", "description": "当前榜单模式"},
        "daily": {"mode_name": "当日汇总", "summary_mode": "daily", "should_send_realtime": False, "should_generate_summary": True, "realtime_report_type": "", "summary_report_type": "当日汇总", "description": "当日汇总模式"},
    }

    def __init__(self):
        self.request_interval = CONFIG["REQUEST_INTERVAL"]
        self.report_mode = CONFIG["REPORT_MODE"]
        self.rank_threshold = CONFIG["RANK_THRESHOLD"]
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        self.update_info = None
        self.proxy_url = CONFIG["DEFAULT_PROXY"] if CONFIG["USE_PROXY"] else None
        self.data_fetcher = DataFetcher(self.proxy_url)

    def _load_analysis_data(self):
        current_ids = [p["id"] for p in CONFIG["PLATFORMS"]]
        all_res, id_map, t_info = read_all_today_titles(current_ids)
        if not all_res: return None
        new_t = detect_latest_new_titles(current_ids)
        wg, fw = load_frequency_words()
        return all_res, id_map, t_info, new_t, wg, fw

    def _run_analysis_pipeline(self, data_source, mode, title_info, new_titles, wg, fw, id_to_name, failed_ids=None, is_daily_summary=False):
        stats, total_titles = count_word_frequency(
            data_source, wg, fw, id_to_name, title_info, self.rank_threshold, new_titles, mode=mode
        )
        html_file = generate_html_report(
            stats, total_titles, failed_ids, new_titles, id_to_name, mode, is_daily_summary, self.update_info,
            raw_data=data_source 
        )
        return stats, html_file

    # 省略通知发送逻辑，请确保原代码中的 send_to_notifications 等函数存在
    def _send_notification_if_needed(self, stats, report_type, mode, failed_ids, new_titles, id_to_name, html_file_path):
         # 这里假设 send_to_notifications 函数在外部定义或已存在
         pass

    def run(self):
        print(f"开始执行... 模式: {self.report_mode}")
        results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(CONFIG["PLATFORMS"])
        save_titles_to_file(results, id_to_name, failed_ids)
        
        data = self._load_analysis_data()
        if not data: return
        all_res, id_map, t_info, new_t, wg, fw = data
        
        strategy = self.MODE_STRATEGIES.get(self.report_mode, self.MODE_STRATEGIES["daily"])
        
        target_data = all_res if self.report_mode == "current" else results
        stats, html_file = self._run_analysis_pipeline(target_data, self.report_mode, t_info, new_t, wg, fw, id_map, failed_ids)
        print(f"HTML生成: {html_file}")
        
        if strategy["should_generate_summary"]:
             self._run_analysis_pipeline(all_res, strategy["summary_mode"], t_info, new_t, wg, fw, id_map, failed_ids, is_daily_summary=True)

def main():
    try:
        analyzer = NewsAnalyzer()
        analyzer.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
