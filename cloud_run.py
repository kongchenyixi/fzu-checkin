"""云端签到入口（GitHub Actions）。

与本地 run.py 的区别：
- 不做 WiFi 重连、不抢文件锁、不缓存 token（每次全新登录，环境干净）
- 凭证与坐标全部从环境变量读取，仓库里不存任何敏感信息
- 单次运行内短间隔重试，失败即返回非 0 退出码（GitHub 会发失败邮件）

凭证读取（优先级从高到低）：
  1. CONFIG_YAML   —— 把本地 config.yaml 全文粘进这一个 Secret 即可（推荐，最省事）
  2. FZU_USERNAME / FZU_PASSWORD / FZU_LON / FZU_LAT —— 分开设置
可选：
  FZU_FORCE=1     忽略时间窗口（手动触发调试用）
"""

import datetime as dt
import os
import sys
import time

import requests
import yaml

from src.checkin import AttnClient, beijing_now, do_checkin

# 北京时间窗口：21:00 开窗，22:30 迟到线，23:30 之后不再尝试
WIN_START = dt.time(20, 50)
LATE_LINE = dt.time(22, 30)
WIN_END = dt.time(23, 30)

MAX_TRIES = 4      # 单次运行内的登录/查询重试次数
RETRY_GAP = 45     # 重试间隔（秒）


def log(msg: str):
    line = f"[{beijing_now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(line + "\n\n")
        except Exception:
            pass


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def main() -> int:
    force = _env("FZU_FORCE").lower() in ("1", "true", "yes") or "--force" in sys.argv

    username = password = lon = lat = actual_location = ""

    raw_cfg = os.environ.get("CONFIG_YAML") or ""
    if raw_cfg.strip():
        try:
            conf = yaml.safe_load(raw_cfg) or {}
            user_conf = conf.get("user") or {}
            ck_conf = conf.get("checkin") or {}
            username = str(user_conf.get("username") or "").strip()
            password = str(user_conf.get("password") or "")
            lon = str(ck_conf.get("longitude") or "").strip()
            lat = str(ck_conf.get("latitude") or "").strip()
            actual_location = str(ck_conf.get("actual_location") or "")
            log("已读取 CONFIG_YAML")
        except Exception as e:
            log(f"CONFIG_YAML 解析失败：{type(e).__name__}: {e}")
            return 2

    # 单项环境变量兜底（两者都配时以 CONFIG_YAML 为准）
    username = username or _env("FZU_USERNAME")
    password = password or (os.environ.get("FZU_PASSWORD") or "")
    lon = lon or _env("FZU_LON")
    lat = lat or _env("FZU_LAT")
    actual_location = actual_location or (os.environ.get("FZU_ACTUAL_LOCATION") or "")

    missing = [
        name for name, value in (
            ("FZU_USERNAME", username),
            ("FZU_PASSWORD", password),
            ("FZU_LON", lon),
            ("FZU_LAT", lat),
        ) if not value
    ]
    if missing:
        log("配置缺失：" + "、".join(missing)
            + "。请在仓库 Settings → Secrets and variables → Actions 里设置 CONFIG_YAML（推荐），"
              "或分别设置这四个 Secret。")
        return 2

    now = beijing_now()
    today = now.time()
    if not force:
        if today < WIN_START:
            log(f"北京时间 {now:%H:%M} 还没到签到时间（{WIN_START:%H:%M} 开窗），跳过")
            return 0
        if today > WIN_END:
            log(f"北京时间 {now:%H:%M} 已过最晚尝试时间（{WIN_END:%H:%M}），跳过")
            return 0

    log(f"开始签到｜北京时间 {now:%Y-%m-%d %H:%M:%S}｜账号 {username}")

    cfg = {
        "user": {"username": username, "password": password},
        "checkin": {
            "longitude": lon,
            "latitude": lat,
            "actual_location": actual_location,
        },
    }

    # ---- 登录 + 查询今日计划（网络抖动时重试） ----
    client = None
    data = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            from src.login import login as sso_login

            token, cookies = sso_login(username, password)
            client = AttnClient(token, cookies)
            data = client.init()
            log("登录成功，已获取今日考勤计划")
            break
        except requests.HTTPError as e:
            log(f"第 {attempt}/{MAX_TRIES} 次失败（HTTP）：{e}")
        except Exception as e:
            log(f"第 {attempt}/{MAX_TRIES} 次失败：{type(e).__name__}: {e}")
        if attempt < MAX_TRIES:
            time.sleep(RETRY_GAP)

    if data is None or client is None:
        log("多次重试仍失败 ❌ 请手动打开 App 签到")
        return 1

    user_data = data.get("userData") or {}
    state = (user_data.get("FState") or "").strip()
    log(f"当前状态：{state or '未知'}｜签到时间：{user_data.get('FCheckInTime') or '—'}")

    if state in ("SUCCESS", "已签到"):
        log("今天已经签过了，本次无需操作")
        return 0

    if not data.get("schoolData"):
        log("今日无考勤计划（可能今天不点名），跳过")
        return 0

    if today > LATE_LINE:
        log(f"注意：已过迟到线 {LATE_LINE:%H:%M}，本次签到可能被记为迟到")

    # ---- 定位校验 + 提交 ----
    try:
        ok = do_checkin(client, cfg, data)
    except Exception as e:
        log(f"提交签到失败 ❌ {type(e).__name__}: {e}")
        return 1

    if not ok:
        log("定位校验未命中任何校区 ❌ 坐标可能不在签到范围内")
        return 1

    # ---- 回查确认（不只看接口返回，要看服务器状态） ----
    time.sleep(3)
    try:
        after = client.init()
        after_user = after.get("userData") or {}
        after_state = (after_user.get("FState") or "").strip()
        log(f"提交后状态：{after_state}｜签到时间：{after_user.get('FCheckInTime') or '—'}")
        if after_state in ("SUCCESS", "已签到"):
            log("签到成功 ✅")
            return 0
        log("提交已发送，但状态未变为已签到，请打开 App 确认 ⚠️")
        return 0
    except Exception as e:
        log(f"回查失败（提交可能已成功）：{type(e).__name__}: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
