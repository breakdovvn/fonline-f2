# NPC Relations and Aggro

Research notes for TLA. Scope: current implementation as of 2026-11-08, plus a
roadmap for planned changes. This file is the reference for future work on NPC
hostility, dialogue, and faction behavior.

## TL;DR

TLA has **no unified relation graph** (`GetRelation`/`IsEnemy`/`OnCritterCheckAttack`).
Hostility is assembled from several independent script systems:

| System | What it is | Drives target selection? |
| --- | --- | --- |
| `EnemyStack` | Per-critter persistent `ident[]` of remembered enemies | Yes, generic AI scans it |
| `TeamId` + `TeamsTable` | Coarse team tag + "who assists whom" matrix | Only assist calls, not hostility |
| Karma / `PlayerKarma` / `Reputation*` | Player statistics for dialogs, quests, perks, UI, encounters | No |
| `NpcRevenge` | Map-wide collective hostility after enough local NPC kills | Yes, on that map |
| `FighterPattern` | Group alert broadcasts | Adds targets to `EnemyStack` |
| `Mob` | Mob group behavior, fear/fury, leash-like limits | Adds/removes `EnemyStack` |
| `Merc*` / `PetOwnerId` / `FollowLeaderId` | Ownership/follow links | Merc defense/assist only |
| `NoPvpMaps` | Safe-zone gate | Blocks PvP/stealing |

Aggro has two layers:

- **Active attack plan** — not permanent. Ends when the target dies, disappears,
  becomes unreachable, the NPC leaves the map, or the NPC dies. Plans are
  in-memory and lost on restart.
- **`EnemyStack` memory** — effectively permanent. No TTL, distance, LOS, logout,
  map-change, or restart expiry. If the player is off-map/hidden, the NPC simply
  cannot act on it; on the next visible tick on the same map it re-aggros.

## EnemyStack (the actual "aggro memory")

Properties (`Scripts/EnemyStack.fos:9-10`):

```angelscript
///@ Property Critter Server ident[] EnemyStack Mutable Persistent
///@ Property Critter Common bool IsNoEnemyStack Mutable PublicSync Persistent
```

- Server-only, persistent, not networked to clients.
- Stores only IDs; no reason, timestamp, team, or reputation.
- API:
  - `ScanEnemyStack` — first **visible, alive, same-map** enemy (`EnemyStack.fos:13-27`)
  - `AddEnemyToStack` — append, or move existing entry to tail (`:30-49`)
  - `CheckEnemyInStack` (`:52-64`)
  - `EraseEnemyFromStack` (`:67-79`)
  - `ClearEnemyStack` (`:82-87`)
  - `ClearEnemyStackNpc` — removes live non-player entries, keeps player/stale IDs (`:90-108`)
- No size cap, no cleanup scan for destroyed critters.
- `IsNoEnemyStack` is set in several scripts but **never read**; it is a no-op.

### Where entries are added

Representative call sites (there are many more):

- Generic AI "I saw a hostile player" for mobs: `Mob.fos:220-234`
- NPC death: the dying NPC gets the killer added to its own stack: `Combat.fos:2301-2308`
- Theft/guard reactions: `Caravan.fos:987-997`, `SfCommon.fos:607-608`,
  `VcGuardsman.fos:908-909`, `HubLab.fos:374-375`
- Group alerts: `FighterPattern.fos:294-314`, `GameEventReplicator.fos:716-726`
- Quests/scripted encounters: `Worldmap.fos:1137-1157`, `Purgatory.fos:376,589`,
  `SeTeleport.fos:285`, `NrWriKidnap.fos:646-647`, `TownSupply.fos:188`,
  `Hunter.fos:479`
- The generic "I was attacked" handler in `Main.fos:153-165` adds an **attack
  plan**, not an `EnemyStack` entry.

### How AI consumes it

`NpcPlanes` (`Scripts/NpcPlanes.fos`):

1. AI ticks only on maps with at least one player (`:79-171`).
2. `OnCritterIdle` runs roughly once per `NPC_AI_TICK_MS = 1000` (`:22,93-105,173-186`).
3. With no current plan, it calls `EnemyStack::ScanEnemyStack` (`:232-243`).
4. Enemy must be visible/alive/same map (`EnemyStack.fos:13-27`).
5. Attack plan is added: `REASON_FOUND_IN_ENEMY_STACK`.
6. `Mob` can veto that plan (`Mob.fos:344-396`): same team, distance > 10,
   no path, or path > 3x straight distance.
7. Attack plan ends on target death/`Attack_MinHp`, target invisible, or
   unreachable (`NpcPlanes.fos:361-659`). **The stack entry is not removed.**
8. `MainPlanes.IsCurrentEnemy` (`MainPlanes.fos:847-864`) uses stack/plan only
   for burst line-of-fire safety.

Consequences:

- Off-map/hidden/dead target: `ScanEnemyStack` returns null, no plan, stale ID
  stays; re-aggro immediately on the next visible tick.
- Unreachable target: plan ends, stack stays.
- No cross-map chase; target must be on the same map and visible.

### What removes entries

Only explicit calls:

- `EraseEnemyFromStack` / `ClearEnemyStack` / `ClearEnemyStackNpc`
- NPC kills that target: `Combat.fos:2311-2313`
- Mob's own death: `Mob.fos:200-203`
- NPC replication: `Replication.fos:382-384` (keeps player IDs)
- Mob LOS loss while `MobFury < 3`: `Mob.fos:246-256`
- Scripted stand-down: `Trigger.fos:79-89`, `Stdlib.fos:232-260`,
  `ItemV13Collar.fos:35-39`, quest scripts.

No cleanup on player logout, map change, or restart; no TTL/cooldown/leash for
generic NPCs.

### Persistence

- `EnemyStack` is `Persistent`: survives server restart for persisted critters.
- Attack plans live in `AllNpcPlanes` (`NpcPlanes.fos:747-748`), a plain dict:
  lost on restart.
- NPC replication drops plans and `ClearEnemyStackNpc` (`Replication.fos:382-384`),
  so NPC-vs-NPC aggro is forgotten but **player aggro is kept**.
- Player replication keeps the same critter ID, so surviving stack entries
  re-aggro after player respawn.
- Destroyed and re-created critter loses the property.
- Clients never see `EnemyStack`.

## Team / assist system

- `TeamId` per critter (`CritterProps.fos:79`), players set to 1 (`Main.fos:987`).
- `Teams.fos` enumerates teams.
- `TeamsTable.fos:12-27` defines `GetTeamParity` (assist behavior, not hostility):
  `Ignore`, `Anyway`, `NotBusy`, `HpLess*`, `IfDead`, `GoodPerson`.
- Used to recruit nearby helpers on attack (`Main.fos:186-250`,
  `MaxHelpers = clamp(10 - Charisma, 2, 8)`), never to attack same team
  (`Main.fos:195-197`).
- `FighterPattern.IsAlly` = same non-zero `TeamId` (`FighterPattern.fos:369-373`).
- Dialog `TeamAttack` orders same-team NPCs to attack (`Dialog.fos:1144-1163`).

## Karma / Reputation

- `Karma`, `PlayerKarma`, `KarmaVoting` (`CritterProps.fos:71,85,627`).
- 20 town/faction reputations (`CritterProps.fos:128-147`) + encounter loyalty
  counters (`:510-522`).
- `Reputation.fos` only maps numbers to UI levels (`Idolized`..`Vilified`).
- Used by dialogs, perks, quests, kill rewards, encounter spawning; **not** by
  generic AI target selection.

## NpcRevenge

- Map-level state in `Map.NpcRevengeData`, saved via `RevengeMapInfo`
  (`NpcRevenge.fos:17,199-257`).
- Modes: `MODE_NORMAL → MODE_LEADER_CALLS → MODE_MEETING → MODE_HOSTILE`.
- Enough local NPC kills → all local NPCs attack all players (`:281-311`);
  hostility ends when `DeadsCounter == 0` (`:571-577`).
- Separate from per-critter `EnemyStack`.

## FighterPattern / Mob

- `FighterPattern`: first player sighting broadcasts `MSG_KILLEM`; recipients add
  the target to their `EnemyStack` (`:235-314`). Teammate deaths trigger alarms.
- `Mob`: attack distance 10, group radius 20, go-home 30, `MAX_FURY = 3`
  (`Mob.fos:13-18`). Losing sight removes an enemy only while `MobFury < 3`
  (`:246-256`); own death clears everything (`:200-203`); panic/fear drops plans
  (`:167-191,409-416`).

## Other relation-like links

- Merc: `MercMasterId`, `MercDefendMaster`, `MercAssistMaster`
  (`CritterProps.fos:382-389`) — defend/assist master (`Merc.fos:165-193`).
- Pet: `PetOwnerId`, non-combat, `IsNoTalk = true` (`Pet.fos:39-59`).
- `FollowLeaderId` (`CritterProps.fos:107`).
- `NoPvpMaps`: `IsNoPvPMap` / `IsNoPvp` (`NoPvpMaps.fos`), blocks PvP/stealing.

## Does aggro last forever?

**Attack plan: no.** Ends on target death/invisibility/unreachable, NPC death,
map out; plans are non-persistent.

**`EnemyStack`: effectively yes.** No expiry. If the NPC holds the player ID, it
re-aggros as soon as the player is visible on the same map, including after
respawn and server restart.

Exceptions:

1. Mobile mobs forget on LOS loss while `MobFury < 3`, and on own death.
2. NPC replication strips NPC-vs-NPC entries; player entries are kept.
3. The NPC that killed the target removes it from its own stack.
4. Scripted stand-down/taming/quest cleanup removes entries.
5. Generic attacked NPCs without a scripted reaction get only a plan, not a stack
   entry, and forget after the plan ends.
6. Destroyed/re-created critters lose the stack with the object.
7. `IsNoEnemyStack` protects nothing (never read).

## Roadmap

### 1. Prevent starting dialogue while in combat (implemented 2026-11-08)

Goal: the player must **not** be able to start a dialogue while in combat,
including with the NPC they are currently fighting.

Before the change there was **no combat gate** in the dialogue start path:

- Client context menu button: `DropMenuHandler::CanDialog` checked only alive,
  non-player, `DialogId`, `IsNoTalk` (`DropMenuHandler.fos:96-101`).
- Client talk action: `ChosenActions::ChosenTalkNpc` walked into talk distance
  and called `StartDialog` (`ChosenActions.fos:1152-1190`).
- Server entry: `DropMenuHandler::StartDialog` checked alive/controlled/NoTalk,
  then called `Dialogs::RunDialog` (`DropMenuHandler.fos:251-319`).
- `Dialogs::IsCrittersCanTalk` checks alive, same map, talk distance, mutual
  visibility — no combat check (`Dialogs.fos:381-402`).

Implemented:

1. Client context menu: `DropMenuHandler::CanDialog` now also requires
   `!Time::IsTimeoutActive(Chosen.TimeoutBattle)`, so the Talk button is absent
   while the player is in combat (`DropMenuHandler.fos:96-101`).
2. Server entry: `DropMenuHandler::StartDialog` rejects the request when
   `Time::IsTimeoutActive(cr.TimeoutBattle)` (`DropMenuHandler.fos:251-319`),
   so a direct `StartDialog` call cannot bypass the client gate.
3. Dialogue-in-combat AI suspension that was briefly added was reverted:
   `NpcPlanes`, `NpcPlanes::AddPlane`, and `OnCritterTalk` are back to their
   previous behavior. The existing `Dialogs::IsTalking` check in `NpcPlanes`
   (when the NPC has no plan) remains as it was.
4. `Dialogs::IsCrittersCanTalk` stays combat-agnostic. Scripted
   `Dialogs::RunDialog` calls can still start a dialogue during combat by
   design; the UI/server gate covers player-initiated dialogue.

Verification:

- While `TimeoutBattle` is active, the context menu has no Talk button.
- A direct `StartDialog` call during combat does nothing.
- Out of combat, dialogue works as before.
- `AiControl` talk diagnostics still show the usual range/visibility/NoTalk
  statuses; a combat rejection is silent in the current implementation.

Open design questions:

- Should scripted dialogues be allowed to override the combat block?
- Should "in combat" consider the NPC's `TimeoutBattle` as well, or only the
  player's?
- Should a blocked attempt show a text message ("Нельзя говорить в бою")?


### 2. Some NPCs do not react to combat (diagnosing)

Symptom: some NPCs neither aggro nor flee when combat starts; they stand or
continue their routine.

Known gaps from the code:

- `EnemyStack` is only scanned for visible, alive, same-map targets
  (`EnemyStack.fos:13-27`); an off-screen attacker is not seen.
- `Mob.PlaneBegin` rejects an attack plan with `REASON_FOUND_IN_ENEMY_STACK`
  when the target is farther than `DISTANCE_ATTACK` (10), when there is no path,
  or when the path is more than 3x the straight distance (`Mob.fos:363-391`).
  No flee/seek plan is added on those vetoes.
- The legacy `AiSettings` fields `AiRunAway`, `AiDisposition`, `AiAttackWho`,
  `AiAggression`, `AiMinHp` are defined but unused by the modern AI; there is no
  generic flee planner outside `Mob.AddPlaneEscape` (fear only).
- Generic NPCs get an attack plan only when they are the victim
  (`Main.fos:151-165`); nearby non-team bystanders have no global
  `OnSomeCritterAttacked` subscription and do not flee or assist.

Resolution (2026-11-08):

- `TeamsTable::IfDead` never fired because `OnCritterAttacked` runs **before**
  damage, while the victim is still alive. `Main.CritterDead` now calls the
  extracted `Main.ReactToAttack(cr, killer)` after the condition is Dead, so
  same-team townsfolk get a revenge attack plan.
- Immediate helper plans are still capped by `maxHelpers` (10 - Charisma,
  clamped 2..8). To keep guards from standing around beyond the cap, every
  qualifying observer now gets the attacker in `EnemyStack`; the AI picks it up
  on the next `ScanEnemyStack` tick. The cap applies only to immediate plans.
- The temporary `NPCDIAG` instrumentation was removed after verification.

Remaining limitations:

- Only observers who see the victim / attacker react.
- Whether a team assists is still decided by `TeamsTable`; many cross-faction
  pairs are `Ignore`.
- There is still no generic flee planner for civilians: reaction is reach/attack
  or nothing. `AiRunAway`/`AiDisposition` remain unused by the modern AI.
- The `EnemyStack` entry is persistent: a bystander remembers the attacker and
  can re-aggro on a later encounter. If temporary combat-only assistance is
  desired, use a separate temporary enemy list instead of `EnemyStack`.

