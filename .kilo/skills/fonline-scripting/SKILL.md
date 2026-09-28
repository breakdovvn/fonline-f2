---
name: fonline-scripting
description: "Написание AngelScript (.fos) для FOnline: TLA — nullable-контракты, namespace по имени файла, CritterProperty и запрет const &. Использовать при правке или добавлении логики в Scripts/*.fos."
---

# Навык: Написание скриптов AngelScript для FOnline

## Основные правила языка
- Типы данных: `uint`, `uint16`, `uint8`, `int`, `string`.
- Ссылки на объекты движка передаются через `@` (например, `Critter@ cr`, `Map@ map`).
- Проверка на null: `if (not valid(cr))` или `if (cr is null)`.

## Глобальные сущности движка
- `Critter`: методы `cr.Say(...)`, `cr.AddItem(...)`, `cr.Stat[...]`.
- `Map`: методы `map.GetCritter(...)`, `map.SetHex(...)`.

---

## Проверено в этом репозитории (дополнение агента, 2026-02-14)

- Синтаксис `Critter@` в `Scripts/*.fos` не встречается ни разу. Здесь принято:
  non-nullable `Critter cr`, nullable `Critter? cr`; для компонентов — флаги `Has<Component>`.
- Функции `valid(...)` и `is null` в скриптах не используются. Актуальный контракт —
  «strong nullable»: сужай `T?` через `if (x == null) return;`, `if (x != null)`,
  тернарник или `&&`/`||`; для даункаста — `cast<T?>(x)`. Полные правила: `Nullability.md`.
- Аргументы **не** передаются по `const &`. Обычный `&` — только для настоящих in/out
  value-параметров.
- `cr.Stat[...]` в репозитории не найдено. Статы и прочие свойства криттера идут через
  enum `CritterProperty` / `CritterPropertyGroup::SpecialBase` (пример: `Scripts/AiControl.fos`,
  `Scripts/Behemoth.fos`).
- `cr.AddItem(pid, count)` и `map.AddItem(hex, pid, count)` подтверждены. `cr.Say(...)`
  используется, но редко (7 вхождений) — для текста чаще служат текстовые паки.
- Каждый файл объявляет `namespace` по своему имени (`AiPattern.fos` → `namespace AiPattern`)
  и **не** содержит `#include`; кросс-модульные вызовы — `Namespace::Function()`.
- Сторона размечается `#if SERVER` / `#if CLIENT` / `#if MAPPER`. Авторитетное состояние —
  только на сервере.
- Точки входа помечаются `[[ModuleInit]]`; воркер-колбэки — `[[Async]]` с
  `Sync::LockCritterWithMap(cr)` перед доступом к видимым на карте данным.
- Комментарии в `.fos` пишутся по-русски (`AGENTS.md`, `Docs/ScriptStyle.md`); сериализуемые
  имена (`///@ Property/Enum/Setting/Event/RemoteCall`, id прототипов, ключи текстов) — английские.
- Проверка перед сдачей: `Compile AngelScript`, при необходимости
  `Tools/ScriptQuality/validate_scripts.py` и `Tools/NullableEstimate/validate_nullable.py`.
- Каждый файл заканчивается ровно одним пустым переводом строки.
