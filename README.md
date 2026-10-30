# 福大晚点名 · 自动签到

福州大学「智汇福大」晚点名自动签到，跑在 GitHub 的服务器上。

**不需要电脑开机，不需要手机常亮，不需要连校园网。** 配好一次，之后每天自动完成。

每天北京时间 **21:00 / 21:20 / 21:40 / 22:00 / 22:15** 各触发一次，先查当天状态，已签到就直接跳过，不重复提交。22:30 是迟到线，多次触发是为了抵消 GitHub 定时任务的延迟。

---

## 怎么用（三步）

### 1. 复制这个仓库

点右上角绿色的 **Use this template** → **Create a new repository**，起个名字，建议选 **Private**，创建。

### 2. 生成你的配置

打开 **配置生成器**，填学号、密码、你宿舍的经纬度，点生成，复制那段文本。

> 坐标查询：打开 [高德坐标拾取器](https://lbs.amap.com/tools/picker)，搜索你住的楼，在地图上点你宿舍的位置，右上角显示的「经度,纬度」就是要的两个数字。**必须落在你所在校区范围内**，否则签到会因定位校验失败。

### 3. 存成 Secret

在你自己的仓库里：**Settings → Secrets and variables → Actions → New repository secret**

- Name：`CONFIG_YAML`
- Secret：粘贴上一步复制的整段文本

保存后进入 **Actions** 标签页启用 workflows，选「晚点名自动签到」→ **Run workflow** → 勾上 `force` → 运行。绿勾即成功。

之后不用管了，每天自动跑。

---

## 配置长什么样

```yaml
user:
  username: '你的学号'
  password: '你的密码'

checkin:
  longitude: '118.587849'
  latitude: '24.559165'
  actual_location: '福州大学晋江校区G栋'

notify:
  type: "none"
```

注意缩进是两个空格，不要用 Tab。不想手写就用配置生成器。

也可以拆成四个 Secret：`FZU_USERNAME`、`FZU_PASSWORD`、`FZU_LON`、`FZU_LAT`，效果一样。

---

## 目录

```
cloud_run.py              云端入口：读 Secret → 登录 → 查状态 → 签到 → 回查确认
src/login.py              SSO 登录，换取 token 与会话 Cookie
src/checkin.py            晚点名接口客户端（参数 AES-CBC 加密）
.github/workflows/        定时签到 / 保活
docs/配置生成器.html       填表生成配置，避免手写 YAML 出错
docs/同学使用指南.md       带截图的完整走查和常见问题
```

---

## 几个说明

**密码安全**：学号密码只存在 GitHub 的加密 Secret 里，连仓库主人也无法在网页上回看。代码中不含任何个人信息。

**免费额度**：私有仓库每月 2000 分钟免费额度，本脚本每月约消耗 150 分钟。公开仓库则完全不限。

**定时被停用**：仓库连续 60 天没有提交，GitHub 会自动停用定时任务。`keepalive.yml` 每月自动提交一次时间戳来避免。

**接口变更**：这是对学校 App 接口的自动化封装，不是官方功能。接口改版会导致失效，需要相应更新代码。

---

## 使用前提

只在本人**确实在校**时使用。请假、离校、不在校区的日子请照常用 App 走正常流程。代签若被发现，按校规处理，风险自负。

另外，用的人多了接口可能有风控，建议小范围使用。

---

MIT License
