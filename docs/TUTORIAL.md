# MinerSentinel tutorial

A complete walkthrough for running MinerSentinel on your LAN: install, add miners, configure a solo pool, set up alerts, use Activity / Advisor / Controls, and keep the fleet healthy.

**Audience:** home Bitcoin miners with Bitaxe / NerdQAxe / Avalon (and NMAxe / NerdNOS) on the same network as the host.

**Related docs:** [README](../README.md) · [Umbrel packaging](../umbrel/README.md)

---

## Table of contents

1. [What you get](#1-what-you-get)
2. [Prerequisites](#2-prerequisites)
3. [Install with Docker](#3-install-with-docker)
4. [First login](#4-first-login)
5. [Add devices](#5-add-devices)
6. [Configure your pool](#6-configure-your-pool)
7. [Notifications](#7-notifications)
8. [Using the dashboards](#8-using-the-dashboards)
9. [Activity journal](#9-activity-journal)
10. [Advisor](#10-advisor)
11. [Device Controls](#11-device-controls)
12. [Collector health & retention](#12-collector-health--retention)
13. [Day-to-day checklist](#13-day-to-day-checklist)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. What you get

MinerSentinel is a **self-hosted** monitor. Data stays on your machine (Postgres). The stack polls miners and your solo pool API, stores history, and can push alerts to Telegram, Discord, ntfy, Gotify, or a generic webhook.

| Area | What it does |
|------|----------------|
| **Overview** | Fleet hashrate, temps, power, open issues vs highlights |
| **Mining** | Device cards/table, Advisor, pool history, stratum compare |
| **Analytics** | Best-diff odds, solo outlook, energy, costs |
| **Activity** | Persisted alert journal (problems vs celebrations) |
| **Settings** | Devices, collector interval, pool, notifications, theme |
| **Controls** | Per-device reboot, fan, freq/voltage (Bitaxe), Avalon workmode |

---

## 2. Prerequisites

- Docker Engine + Docker Compose
- Host can reach miners on the LAN:
  - **Bitaxe / NerdQAxe / NMAxe / NerdNOS:** HTTP (usually port 80)
  - **Avalon:** cgminer API TCP **4028**
- Optional: Telegram bot, Discord webhook, or an [ntfy](https://ntfy.sh) topic for push alerts
- Optional: Bitcoin address used on your solo pool (CKPool, Public Pool, Parasite, …)

---

## 3. Install with Docker

```bash
git clone https://github.com/dcbert/miner-sentinel.git
cd miner-sentinel
cp .env.example .env
# Edit POSTGRES_PASSWORD, SECRET_KEY, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS
docker compose up -d --build
```

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Dashboard (dev compose) |
| http://localhost:8000 | Django API / Admin |
| http://localhost:8000/admin/ | Django Admin |

**Default dev login** (override with `DEFAULT_USERNAME` / `DEFAULT_PASSWORD`):

- Username: `satoshi`
- Password: `21millionBTC!`

Apply migrations if you upgraded an existing install:

```bash
docker compose exec backend python manage.py migrate
```

Optional lab seed (idempotent upsert by make + IP):

```bash
docker compose exec backend python manage.py seed_lab_devices
```

**Umbrel:** use the app from the Umbrel store / [`umbrel/`](../umbrel/) package (UI typically on port **3080**). See [umbrel/README.md](../umbrel/README.md).

---

## 4. First login

1. Open http://localhost:3000/login
2. Sign in with the default (or your) credentials
3. You land on **Overview** — empty until devices exist and a poll completes

Tip: use the global **Range** control (1h / 24h / 7d / 30d / custom) — charts and Analytics respect it.

---

## 5. Add devices

### Manual add

1. Go to **Settings → Devices**
2. Click **Add Device**
3. Fill:

| Field | Example |
|-------|---------|
| Make | `bitaxe` or `avalon` (NerdQAxe → **bitaxe**) |
| Device ID | Unique within make, e.g. `bitaxe-gamma` |
| Name | Display name |
| IP | `192.168.1.7` |
| Port | Leave blank for Bitaxe; Avalon defaults to **4028** |
| Active | On |

4. Save. The data-service reloads the device list on its schedule (default ~5 minutes), or trigger **Settings → Data Collector → Trigger Manual Poll**.

### Discover LAN

1. **Settings → Devices → Discover LAN**
2. Review proposed AxeOS / Avalon hosts
3. Add the ones you want

### Export

**Export CSV** downloads inventory for backup or spreadsheets.

---

## 6. Configure your pool

1. **Settings → Data Collector**
2. Choose **pool type**: CKPool, Public Pool, BTC PoW Lab, or Parasite
3. Set your **Bitcoin address** and API URL if needed
4. Save, then run a **manual poll** once

On **Mining → Pool** you will see pool hashrate windows and a **Device stratum vs selected pool** table (primary/fallback URLs compared to the configured pool — not full concurrent multi-pool polling).

---

## 7. Notifications

Open **Settings → Notifications**.

### Channels

| Channel | Setup |
|---------|--------|
| **Telegram** | BotFather token + chat ID → Save → **Send test** |
| **Discord** | Channel webhook URL → Save → **Send test** |
| **ntfy** | Full topic URL (e.g. `https://ntfy.sh/your-topic`) → optional token → **Send test** |
| **Gotify** | Server URL + token |
| **Webhook** | Any HTTPS endpoint that accepts JSON POSTs |

Secrets are **write-only** after save (the UI will not show the previous token).

### Event rules

Toggle and tune events such as:

- Device offline / online  
- Hashrate stagnation (+ optional auto-restart)  
- New best difficulty (celebration / **highlight**, not a “problem”)  
- High temperature, fan dead, pool down, collector down, expected hashrate drop  

Also configure:

- **Quiet hours** — suppress non-critical chat overnight  
- **Re-alert cadence** — avoid spam for the same open issue  

Every fired alert is also written to the **Activity** journal so the UI and chat stay in sync.

---

## 8. Using the dashboards

### Overview

- Fleet KPIs (hashrate, acceptance, best share, power)
- Charts with optional **incident markers**
- **Issues needing attention** (amber/red) — real problems only  
- **Recent highlights** (green) — new best shares, recoveries, successful controls  

### Mining

- **Advisor** suggestions with one-click actions when available  
- Fleet cards/table with filters (online/offline, make)  
- **Pool** tab: history + stratum compare  

### Analytics

Tabs: Predictions · Solo · Energy · Costs · Devices  

Set your energy rate / currency under **Settings → Data Collector**.

### Device detail

`/devices/:make/:deviceId` — Performance, Hardware, Network, System, **Controls**.

---

## 9. Activity journal

**Activity** page filters:

| Filter | Meaning |
|--------|---------|
| **Needs attention** | Open warn/critical issues |
| **Highlights** | Best difficulty, recoveries, control audits |
| **All** | Full history |

For open problems: **Done** (acknowledge) or **Snooze 1h**.

New best difficulty is always a **highlight**, never counted as an open problem.

---

## 10. Advisor

On **Mining**, Advisor ranks next actions, for example:

- Raise Avalon **workmode** (Low / Mid / High)  
- Open a hot or offline device  

Buttons call the same control API as the Controls tab (with confirm for destructive actions).

---

## 11. Device Controls

Open a device → **Controls**. Only actions the firmware supports are shown.

### Bitaxe / NerdQAxe (AxeOS)

| Control | UI |
|---------|-----|
| Reboot | Confirm dialog |
| Fan | Auto toggle, or **slider** for manual % |
| Frequency | **Preset dropdown** (MHz) + Custom… |
| Voltage | **Preset dropdown** (mV) + Custom… |
| Pause / Resume | Standby without full reboot |
| Pool | Stratum URL / user / password + restart |

Frequency and voltage apply require confirmation (safety).

### Avalon (cgminer)

| Control | Notes |
|---------|--------|
| Reboot | Supported |
| Fan | Auto or slider (15–100%) |
| Workmode | Low / Mid / High one-click |
| Frequency / voltage | **Hidden** — not reliable on home Avalon Nano/Mini |

Every successful or failed control is logged in **Activity**.

---

## 12. Collector health & retention

**Settings → Data Collector:**

- Poll interval (home fleets often use **1–2 minutes**)
- Device reload interval  
- Honest status: **Healthy / Degraded / Unreachable**, last success, next run, last error  
- **Metrics retention days** — prune old mining/hardware/pool rows (`0` = keep forever)  
- **Alert retention days** — prune resolved Activity rows (`0` = keep forever; open alerts are never pruned)

Manual prune:

```bash
docker compose exec backend python manage.py prune_retention
```

---

## 13. Day-to-day checklist

1. Glance at **Overview** — red/amber strip empty? Highlights OK?  
2. **Mining → Advisor** — anything actionable?  
3. **Activity → Needs attention** — acknowledge or fix  
4. After firmware or pool changes — **Trigger Manual Poll**  
5. Periodically **Export CSV** of the device inventory  

---

## 14. Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Device always offline | Ping IP; Bitaxe open in browser; Avalon `4028` open from the Docker host |
| No charts / empty Overview | Wait for a poll or trigger manual poll; check Data Collector status |
| Alerts in chat but not in UI | Confirm migrations applied; open **Activity → All** |
| Controls disabled | Device must be **online** (recent `last_seen`) |
| Avalon freq/voltage missing | Expected — use workmode + fan instead |
| Collector Unreachable | `docker compose ps` / `docker compose logs data-service` |
| Wrong pool stats | Settings → correct pool type + address; check Mining → stratum compare |

Useful commands:

```bash
docker compose logs -f data-service
docker compose exec backend python manage.py verify_device_unification
docker compose exec data-service wget -qO- http://localhost:5000/status
```

---

## Next steps

- Tighten notification thresholds for your room’s normal temps  
- Point ntfy at your phone for away-from-home awareness  
- Read the [README](../README.md) API section if you integrate with scripts  

*Happy hashing.*
