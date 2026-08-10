# Unified Device + Pool Data Model & Frictionless Migration

**Goal:** One query-friendly schema for all miner makes **and** pool sources. Collectors normalize vendor APIs into standard snapshots, then persist via shared writers. Existing installs upgrade with **Django data migrations** that copy all history with zero loss. **Heavy automated tests** gate the rollout.

**After approval:** implement in the repo; commit this plan as `docs/plans/unified-device-schema.md`.

---

## 1. Current state

### Devices (split by make)

| Concern | Bitaxe | Avalon |
|---------|--------|--------|
| Registry | `bitaxe_devices` | `avalon_devices` |
| Mining | `bitaxe_mining_stats` | `avalon_mining_stats` |
| Hardware | `bitaxe_hardware_logs` | `avalon_hardware_logs` |
| System | `bitaxe_system_info` | `avalon_system_info` |

### Pools (misnamed, multi-source already)

| Concern | Storage today |
|---------|----------------|
| CKPool + PublicPool rows | **`bitaxe_pool_stats`** only (name is Bitaxe-branded; both collectors write here) |
| Settings | `collector_settings.pool_type` = `ckpool` \| `publicpool` |

Problems:

- Table name implies Bitaxe-only; PublicPool already shoehorns fields (`authorised` reused for total miners).
- Raw string hashrates + dual GH/s columns are awkward; not all windows exist for every pool.
- Future pools (Ocean, Braiins pool, etc.) would stretch the same CKPool-shaped columns further.

---

## 2. Cross-vendor device metrics (standard model)

Home/prosumer ASICs share a monitoring core (cgminer/bmminer, AxeOS, Whatsminer, Braiins-class, Foreman-style fleet views).

### Canonical units (adapters only convert)

| Quantity | Store as |
|----------|----------|
| Hashrate | `hashrate_ghs` (float); MH÷1000, TH×1000 |
| Power | watts |
| Temperature | °C; primary = max useful sensor |
| Voltage | volts |
| Frequency | MHz |
| Efficiency | J/TH = W / (GH/s / 1000) when HR > 0 |
| Best share / difficulty | float |
| Time | UTC timestamptz |

### Query columns vs JSON

- **Typed columns:** anything used in charts, KPIs, filters, alerts.
- **`details` JSON:** vendor-only extras (Bitaxe display/heap, Avalon MM blob, Antminer chains, …).

---

## 3. Target schema

### 3.1 `devices`

```text
devices
  id                    BIGSERIAL PK
  device_id             VARCHAR(64)
  name                  VARCHAR(100)          -- was device_name
  make                  VARCHAR(32)           -- bitaxe | avalon | antminer | whatsminer | braiins | goldshell | iceriver | other
  model                 VARCHAR(100) NULL
  protocol              VARCHAR(32)           -- http_axeos | cgminer_tcp | whatsminer_api | braiins | custom
  ip_address            INET
  port                  INT NULL
  is_active             BOOL DEFAULT TRUE
  last_seen_at          TIMESTAMPTZ NULL
  error_message         TEXT NULL
  connection_config     JSONB DEFAULT '{}'
  created_at            TIMESTAMPTZ
  UNIQUE (make, device_id)
  INDEX (is_active), INDEX (make), INDEX (last_seen_at)
```

### 3.2 `device_mining_stats`

```text
  device_id FK, recorded_at
  hashrate_ghs, hashrate_avg_ghs NULL
  shares_accepted, shares_rejected, hardware_errors NULL
  blocks_found, uptime_seconds
  best_difficulty NULL, best_session_difficulty NULL
  pool_url NULL, pool_user NULL
  INDEX (device_id, recorded_at DESC), INDEX (recorded_at)
```

Legacy map: Avalon `difficulty` → `best_difficulty`.

### 3.3 `device_hardware_stats`

```text
  device_id FK, recorded_at
  temperature_c, temperature_board_c NULL, temperature_chip_c NULL
  power_watts, efficiency_j_per_th
  fan_speed_rpm, fan_speed_percent
  voltage, frequency_mhz
  INDEX (device_id, recorded_at DESC)
```

### 3.4 `device_system_info`

Common inventory columns + `details JSONB` for vendor extras (see full field list in previous plan revision).

### 3.5 Unified pool tables

Rename away from Bitaxe branding. Support multiple pool **types** and optional multi-address history in one place.

#### `pool_stats` (time series — user/client view at the pool)

```text
pool_stats
  id                    BIGSERIAL PK
  pool_type             VARCHAR(32) NOT NULL   -- ckpool | publicpool | ocean | other
  pool_address          VARCHAR(255) NOT NULL  -- BTC address / username
  pool_url              VARCHAR(255) NULL      -- API base used for this sample
  recorded_at           TIMESTAMPTZ NOT NULL

  -- Canonical numeric hashrates (GH/s) for easy SQL charts
  hashrate_1m_ghs       DOUBLE PRECISION NULL
  hashrate_5m_ghs       DOUBLE PRECISION NULL
  hashrate_1h_ghs       DOUBLE PRECISION NULL
  hashrate_1d_ghs       DOUBLE PRECISION NULL
  hashrate_7d_ghs       DOUBLE PRECISION NULL

  -- Optional display strings as returned by API (preserve UX parity)
  hashrate_1m_display   VARCHAR(32) NULL
  hashrate_5m_display   VARCHAR(32) NULL
  hashrate_1h_display   VARCHAR(32) NULL
  hashrate_1d_display   VARCHAR(32) NULL
  hashrate_7d_display   VARCHAR(32) NULL

  workers               INT NULL
  shares                BIGINT NULL
  best_share            DOUBLE PRECISION NULL
  best_ever             DOUBLE PRECISION NULL
  last_share_at         TIMESTAMPTZ NULL      -- prefer real time over raw unix where possible
  last_share_unix       BIGINT NULL           -- raw from CKPool if needed
  authorised_unix       BIGINT NULL           -- CKPool authorised timestamp

  -- Pool-wide extras when API provides them (PublicPool totalMiners, etc.)
  pool_total_miners     INT NULL
  pool_total_hashrate_ghs DOUBLE PRECISION NULL

  details               JSONB NOT NULL DEFAULT '{}'  -- workers list, raw payload keys
  created_at            TIMESTAMPTZ

  INDEX (pool_type, pool_address, recorded_at DESC)
  INDEX (recorded_at)
  INDEX (pool_type, recorded_at DESC)
```

**Why this shape:**

- Charts always use `*_ghs` floats (no string parse in SQL).
- Windows that a pool does not provide stay `NULL` (PublicPool today duplicates one value into all windows — after normalize, set only windows that are real, or set `hashrate_1m_ghs` only).
- `pool_type` + `pool_address` replaces “everything is Bitaxe pool stats.”
- `details` holds PublicPool worker arrays, future Ocean fields, etc.

#### Django model

`PoolStats` → table `pool_stats`.

#### Legacy map from `bitaxe_pool_stats`

| New | Old |
|-----|-----|
| `pool_type` | Infer from `collector_settings.pool_type` at migrate time **or** leave `'unknown'` / default `'ckpool'` if settings say ckpool — better: copy all rows with `pool_type` from current settings singleton if only one type was ever used; if mixed history possible, default `ckpool` for old rows (PublicPool reuses same table so historical rows may be mixed — store `pool_type='migrated'` or use settings history if none: **`pool_type = current settings or 'ckpool'`** and document; optional `details.migration_note`) |
| `pool_address` | `pool_address` |
| `hashrate_*_ghs` | existing `hashrate_1m_ghs` / `hashrate_1d_ghs`; convert other windows from display strings during migrate |
| `hashrate_*_display` | `hashrate_1m` … `hashrate_7d` |
| `best_share` / `best_ever` | `bestshare` / `bestever` |
| `last_share_unix` | `lastshare` |
| `authorised_unix` | `authorised` |
| `workers`, `shares` | same |
| `pool_total_miners` | PublicPool abused `authorised` — only fill when we can detect; else leave null for migrated rows |
| `details` | `{}` for migrate |

**Safer pool_type backfill:** set every migrated row to the **current** `collector_settings.pool_type` (single active source for the app today). Historical accuracy of type if user switched pools is imperfect; acceptable for v1 (address+timestamps remain correct).

### 3.6 Collector settings

Keep `collector_settings` as-is (`pool_type`, URLs, addresses). No schema change required for unification beyond optional later multi-pool support.

---

## 4. Collector architecture

```
                    devices + collector_settings
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
        DeviceAdapters   PoolAdapters     AlertEngine
        (bitaxe/avalon)  (ckpool/public)
              │               │
              ▼               ▼
     NormalizedDevice    NormalizedPool
         Snapshot           Snapshot
              │               │
              ▼               ▼
        DeviceDataWriter  PoolDataWriter  → unified tables
```

### 4.1 Device snapshot (as before)

`NormalizedSnapshot` with `MiningMetrics`, `HardwareMetrics`, `SystemMetrics` in **canonical units**.

### 4.2 Pool snapshot

```python
@dataclass
class NormalizedPoolSnapshot:
    pool_type: str                 # ckpool | publicpool | ...
    pool_address: str
    pool_url: str | None
    recorded_at: datetime
    hashrate_1m_ghs: float | None
    hashrate_5m_ghs: float | None
    hashrate_1h_ghs: float | None
    hashrate_1d_ghs: float | None
    hashrate_7d_ghs: float | None
    hashrate_1m_display: str | None
    # ... other display windows optional
    workers: int | None
    shares: int | None
    best_share: float | None
    best_ever: float | None
    last_share_unix: int | None
    authorised_unix: int | None
    pool_total_miners: int | None
    pool_total_hashrate_ghs: float | None
    details: dict
```

CKPool adapter: parse string rates → ghs + keep display strings.  
PublicPool adapter: H/s → ghs; set only windows that exist (e.g. current as 1m); workers from `workersCount`; best difficulty; optional pool-wide totals; put worker list in `details`.

`PoolDataWriter` inserts into `pool_stats` only (plus dual-write to `bitaxe_pool_stats` during first release if chosen).

---

## 5. Migration strategy (Django only)

### 5.1 Migration files

```text
0011_unified_device_and_pool_schema.py
  - Create devices, device_mining_stats, device_hardware_stats,
    device_system_info, pool_stats

0012_migrate_legacy_device_and_pool_data.py
  - RunPython: copy devices + all time series + pool_stats
  - End-of-migration count verification (raise on mismatch)

# Later release
00xx_drop_legacy_device_and_pool_tables.py
```

All via `python manage.py migrate` (Umbrel/backend start already runs this).

### 5.2 Expand → dual-write → switch → contract

| Release | Devices | Pools | Legacy tables |
|---------|---------|-------|---------------|
| **A (first ship)** | Create + backfill + dual-write | Create + backfill + dual-write | Kept |
| **B** | Single-write unified; API shims | Single-write `pool_stats`; `/api/bitaxe/pool/` reads `pool_stats` | Kept read-only |
| **C** | Drop `bitaxe_*` / `avalon_*` device tables | Drop `bitaxe_pool_stats` | Gone |

**Safest for many Umbrel users:** dual-write devices **and** pools in release A.

### 5.3 Data migration checks

```text
devices == bitaxe_devices + avalon_devices
device_mining_stats == bitaxe_mining_stats + avalon_mining_stats
device_hardware_stats == bitaxe_hardware_logs + avalon_hardware_logs
device_system_info == bitaxe_system_info + avalon_system_info
pool_stats == bitaxe_pool_stats
```

Idempotent: skip or upsert if target already populated.

### 5.4 Reverse

Delete only new-table rows; never touch legacy data.

---

## 6. API strategy

| Area | New | Shim |
|------|-----|------|
| Devices | `/api/devices/` | `/api/bitaxe/devices/`, `/api/avalon/devices/` → filter `make` |
| Mining/hardware/system | `/api/mining/`, `/api/hardware/`, … | Brand paths filter by make |
| Pool | `/api/pool/` | `/api/bitaxe/pool/` reads `pool_stats`, same serializer field aliases (`bestshare` etc. if needed) |
| Analytics | rewrite internals to unified tables | response shape stable |

---

## 7. Implementation phases

1. **Schema + Django migrations** (devices + pool) + verify command  
2. **Collectors** — normalize device + pool; dual-write  
3. **API shims** + analytics rewrite  
4. **Frontend** cleanup (optional follow-up)  
5. **Contract** drop legacy tables (later release)

---

## 8. Testing plan (extensive)

Testing is a first-class deliverable, not an afterthought. Cover **migration correctness**, **normalization**, **writers**, **API shims**, and **regression** of dashboards/analytics.

### 8.1 Test environments

| Layer | How |
|-------|-----|
| Backend unit/API | Django + pytest (existing `settings_test`) |
| **Migration tests** | Dedicated settings **with migrations enabled** (today `MIGRATION_MODULES` is disabled in `settings_test` — add `settings_migration_test` or pytest mark that uses real Postgres/SQLite migrations) |
| Data-service unit | pytest + mocked HTTP/socket + optional SQLite/Postgres |
| Integration (optional CI job) | docker-compose: migrate → collect fixture → API asserts |

Prefer **Postgres** for migration tests if available in CI (JSON/INET closer to prod); SQLite acceptable for pure ORM unit tests.

### 8.2 Backend — models & constraints

| Test | Asserts |
|------|---------|
| `test_device_unique_make_device_id` | Same `device_id` allowed for bitaxe + avalon; duplicate `(make, device_id)` rejected |
| `test_device_required_fields` | make, protocol, ip validation |
| `test_mining_stats_fk_cascade` | Deleting device removes stats |
| `test_hardware_stats_indexes_usable` | create sample series ordered by recorded_at |
| `test_pool_stats_indexes` | filter by pool_type + address + time range |
| `test_system_info_details_json` | round-trip arbitrary details dict |

### 8.3 Backend — Django data migration

Use `django.db.migrations.executor` or `migrator` fixture pattern:

| Test | Asserts |
|------|---------|
| `test_migrate_empty_db` | 0011+0012 apply cleanly; counts 0 |
| `test_migrate_bitaxe_only_history` | N devices, M mining/hardware/system rows copied 1:1 |
| `test_migrate_avalon_only_history` | difficulty → best_difficulty; session null |
| `test_migrate_mixed_fleet` | both makes; totals sum |
| `test_migrate_colliding_device_ids` | bitaxe and avalon both `miner-1` → 2 device rows |
| `test_migrate_preserves_recorded_at` | exact timestamps (no timezone rewrite) |
| `test_migrate_preserves_hashrate_values` | float equality within epsilon |
| `test_migrate_system_details_contains_vendor_keys` | e.g. `asic_model` or `serial` in details |
| `test_migrate_pool_stats_all_rows` | count match; ghs fields populated from old columns |
| `test_migrate_pool_type_from_settings` | settings.pool_type=publicpool → migrated rows typed |
| `test_migrate_idempotent` | run forward logic twice → no duplicate explosion |
| `test_migrate_verification_fails_on_mismatch` | force bad state → migration raises |
| `test_legacy_tables_still_exist_after_0012` | bitaxe_* / avalon_* present |
| `test_rollback_0012` | reverse clears new tables only |

**Fixture factories:** build realistic multi-day series (e.g. 100 points/device) not just one row.

### 8.4 Backend — management command

| Test | Asserts |
|------|---------|
| `test_verify_device_unification_ok` | exit 0 after good migrate |
| `test_verify_device_unification_detects_count_drift` | exit non-zero |

### 8.5 Backend — API (unified + shims)

| Test | Asserts |
|------|---------|
| Device CRUD via `/api/devices/` | create bitaxe + avalon; list filter `?make=` |
| Shim `GET /api/bitaxe/devices/` | only bitaxe rows; shape matches old serializer fields (`device_name` alias if needed) |
| Shim `GET /api/avalon/devices/` | only avalon |
| `GET /api/bitaxe/mining/latest/` | data from unified tables |
| Avalon mining/hardware list endpoints | same |
| `GET /api/bitaxe/pool/latest/` | reads `pool_stats`; fields frontend expects |
| `GET /api/pool/` (new) if added | filters by pool_type |
| Overview analytics | fleet hashrate = sum of both makes |
| Detailed analytics | best shares from both makes; pool section works |
| Settings collector still works | pool_type switch |
| Auth still required | 401 unauthenticated |

Update existing `test_api.py` fixtures to create unified models (or dual-create during dual-write era).

### 8.6 Data-service — unit normalization

**Shared fixtures** under `data-service/tests/fixtures/`:

- `bitaxe_system_info.json` (sample AxeOS `/api/system/info`)
- `avalon_version.json`, `avalon_summary.json`, `avalon_estats.json`, `avalon_pools.json`
- `ckpool_user.json`
- `publicpool_client.json`, `publicpool_pool.json`

| Test | Asserts |
|------|---------|
| `test_bitaxe_adapter_hashrate_units` | GH/s not re-scaled wrongly |
| `test_bitaxe_adapter_difficulty_suffixes` | `22.3 M` → 2.23e7 |
| `test_bitaxe_adapter_best_session` | session vs all-time mapped |
| `test_bitaxe_adapter_efficiency` | J/TH formula |
| `test_bitaxe_adapter_system_details_keys` | extras in details, common columns filled |
| `test_avalon_adapter_mhs_to_ghs` | MHS 5s / 1000 |
| `test_avalon_adapter_temp_otemp` | OTemp parsing |
| `test_avalon_adapter_power_mpo` | MPO preferred |
| `test_avalon_adapter_power_rejects_bogus_high` | guard path still sensible |
| `test_avalon_adapter_difficulty_to_best` | Best Share → best_difficulty |
| `test_ckpool_adapter_string_hashrates` | 466G → 466.0 ghs; display preserved |
| `test_publicpool_adapter_hs_to_ghs` | raw H/s / 1e9 |
| `test_publicpool_adapter_null_missing_windows` | only real windows set (policy under test) |
| `test_publicpool_workers_in_details` | workers array retained |
| Offline / HTTP 500 | `online=False`, mining metrics None; writer updates status only |
| Socket timeout Avalon | same |

### 8.7 Data-service — writers

| Test | Asserts |
|------|---------|
| `test_device_writer_inserts_three_series` | mining + hardware + system rows |
| `test_device_writer_updates_last_seen` | last_seen_at set when online |
| `test_device_writer_offline_sets_error` | error_message stored |
| `test_device_writer_dual_write` (release A) | legacy + unified row counts +1 |
| `test_pool_writer_insert` | pool_stats row with ghs |
| `test_pool_writer_dual_write` | also bitaxe_pool_stats when enabled |
| `test_writer_unknown_device_id` | no crash; log error |

Use transactional Postgres or SQLite schema created from Django SQL / simplified DDL in conftest.

### 8.8 Data-service — alerts

| Test | Asserts |
|------|---------|
| Hashrate stagnation reads unified mining table | alert called after 3 equal samples |
| Best difficulty improvement | threshold 5% |
| Online/offline transition | telegram/discord mocks |

### 8.9 Frontend (keep existing + small additions)

| Test | Asserts |
|------|---------|
| Existing Overview/Mining tests | still green with shimmed API mocks |
| Settings device list | still loads bitaxe + avalon endpoints (or unified when switched) |
| New: mock `pool_stats` latest shape | Mining dashboard pool card does not break |

### 8.10 End-to-end / upgrade simulation (CI or manual script)

Documented script or pytest-docker:

1. Start DB; apply migrations **through 0010** only.  
2. Seed legacy tables (SQL or ORM old models).  
3. Apply 0011–0012.  
4. Run `verify_device_unification`.  
5. Assert API analytics numbers match pre-computed golden values.  
6. Run one mocked collect cycle writing unified (+ dual).  
7. Assert new row counts increased only on expected tables.

### 8.11 Coverage targets (guidelines)

| Area | Target |
|------|--------|
| Migration `RunPython` helpers | 100% of mapping branches |
| Adapters normalize paths | high (all parse helpers) |
| Writers | all insert/update paths |
| Analytics views post-rewrite | critical KPI paths |
| Overall new code | aim ≥ 80% line coverage on touched modules |

### 8.12 Test file layout (proposed)

```text
backend/api/tests/
  test_api.py                    # update
  test_unified_models.py         # new
  test_unified_migration.py      # new (real migrations)
  test_verify_unification.py     # new
  test_pool_api.py               # new or extend test_api
  fixtures/legacy_seed.py        # builders for old tables

data-service/tests/
  test_normalized_bitaxe.py
  test_normalized_avalon.py
  test_normalized_ckpool.py
  test_normalized_publicpool.py
  test_device_writer.py
  test_pool_writer.py
  test_alerts_unified.py
  fixtures/*.json
```

### 8.13 CI checklist

- [ ] `pytest backend` including migration tests  
- [ ] `pytest data-service` unit suite  
- [ ] Frontend unit tests  
- [ ] Optional: compose upgrade smoke job  

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Long migrate on Umbrel | Batched copy + logs |
| Pool type wrong on old mixed history | Document; type from current settings |
| PublicPool null windows change charts | Keep dual-write + shim field aliases; frontend uses `hashrate_1m_ghs` |
| settings_test disables migrations | Separate migration test settings |
| Version skew backend vs data-service | depends_on + dual-write release A |
| Early drop of legacy | Release C only |

---

## 10. Success criteria

- [ ] Unified `devices` + mining/hardware/system time series for all makes  
- [ ] Unified `pool_stats` for all pool types (no `bitaxe_pool_*` writes after dual-write ends)  
- [ ] Collectors normalize then write; canonical units  
- [ ] Django migrate alone copies all device **and** pool history with verification  
- [ ] Zero loss for existing users  
- [ ] Extensive tests: migration, adapters, writers, API shims, analytics, alerts  
- [ ] New make/pool = adapter + enum value, not new tables  

---

## 11. Out of scope

- New hardware adapters (Antminer, Whatsminer, …) beyond schema readiness  
- Multi-pool concurrent polling product UI (schema allows multiple addresses/types)  
- TimescaleDB  

---

## 12. Implementation status

| Phase | Status |
|-------|--------|
| 1 Schema + Django migrate 0011/0012 + verify command | **Done** |
| 2 Collectors normalize + write (Release A dual-write → **B single-write**) | **Done** |
| 3 API shims + analytics on unified tables | **Done** (legacy URLs, unified reads) |
| 4 Frontend simplification | Optional follow-up (shims keep current UI working) |
| 5 Drop legacy tables | Later release only |

### Release B notes

- Collectors default `dual_write=False` → inserts only into `devices` time series + `pool_stats`.
- Registry create/update/delete still dual-writes `BitAxeDevice`/`AvalonDevice` ↔ `Device`.
- `/api/bitaxe/*` and `/api/avalon/*` read mining/hardware/system/pool from unified tables with legacy JSON field aliases.
- `overview_analytics` / `detailed_analytics` live in `api/analytics_unified.py`.  
