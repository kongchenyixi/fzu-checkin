# fzu-checkin

福州大学「智汇福大」晚点名自动签到，跑在 GitHub Actions 上，不需要任何一台电脑开机。

## 它做什么

每天北京时间 21:00 / 21:20 / 21:40 / 22:00 / 22:15 各触发一次：

1. 用学号密码自动登录学校 SSO，换取晚点名 token
2. 查询当天考勤计划与自己的签到状态
3. 已签到 → 直接退出，不重复提交
4. 未签到 → 定位校验通过后提交签到，再回查服务器状态确认

22:30 是迟到线。GitHub 的定时任务会有几分钟到十几分钟延迟，所以留了 5 次机会，前一次成功后面自动跳过。

## 配置

只需要在仓库 **Settings → Secrets and variables → Actions** 添加一个 Secret：

| 名称 | 值 |
|---|---|
| `CONFIG_YAML` | 本地 `config.yaml` 的全文（含学号、密码、经纬度） |

也可以拆成 4 个 Secret：`FZU_USERNAME`、`FZU_PASSWORD`、`FZU_LON`、`FZU_LAT`。

## 手动跑一次

仓库 **Actions** 页 → 左侧「晚点名自动签到」→ 右上「Run workflow」。
勾选 `force` 可忽略时间窗口立即执行。

## 目录

```
cloud_run.py              云端入口（读 Secret → 登录 → 查状态 → 签到 → 回查）
src/checkin.py            晚点名接口客户端（AES-CBC 参数加密）
src/login.py              SSO 登录，换取 token + 会话 Cookie
.github/workflows/        定时任务 / 保活任务
requirements.txt          依赖
```

## 注意

- 定时任务在仓库 60 天无提交后会被 GitHub 自动停用，`keepalive.yml` 每月提交一次时间戳避免这种情况。
- 每次运行约 20–40 秒，私有仓库免费额度（2000 分钟/月）完全够用。
- 本工具只在本人确实在校时使用，不代替请假流程。
