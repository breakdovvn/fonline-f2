---
name: fonline-build
description: "Сборка и архитектура FOnline: The Life After — границы Engine/ vs Scripts/ vs SourceExt/, запекание ресурсов и компиляция сервер/клиент. Использовать перед тестом любых изменений: запечь ресурсы и собрать затронутые таргеты."
---

# Навык: Сборка и архитектура FOnline Engine

## Контекст репозитория
- `Engine/` — это submodule движка (C++20, CMake). Его код менять НЕЛЬЗЯ.
- `Scripts/*.fos` — игровая логика на AngelScript (клиент/сервер).
- `SourceExt/` — нативные C++ расширения для конкретно нашей игры.

## Команды сборки (Baking & Compile)
Перед тестированием изменений всегда запускай:
1. Запекание ресурсов (Baker): `FO_BakeResources` или через CMake-таргет.
2. Компиляция сервера: `cmake --build build --target LF_Server`
3. Компиляция клиента: `cmake --build build --target LF_ClientLib`

---

## Проверено в этом репозитории (дополнение агента, 2026-02-14)

Имена из блока выше — из шаблона и **в этом репозитории не существуют**. Фактические
значения подтверждены по `.vscode/tasks.json` и `CMakeLists.txt`:

- Проект называется `TLA` (`project(TLA)`), главный конфиг — `TLA.fomain`.
- Пресет сборки по умолчанию — `auto` → каталог `Build/Auto`, конфигурация `RelWithDebInfo`.
- Реальные таргеты: `BakeResources`, `ForceBakeResources`, `TLA_Server`,
  `TLA_ServerHeadless`, `TLA_Client`, `TLA_Mapper`, `TLA_Baker`, `TLA_ASCompiler`,
  `TLA_UnitTests`. Таргетов `FO_BakeResources`, `LF_Server`, `LF_ClientLib` нет.

Рабочие команды:

```bash
cmake --build Build/Auto --config RelWithDebInfo --target BakeResources
cmake --build Build/Auto --config RelWithDebInfo --target TLA_Server
cmake --build Build/Auto --config RelWithDebInfo --target TLA_Client
```

- `Engine/` — git-submodule (`.gitmodules`: `path = Engine`, `url = ../fonline`).
- Порядок верификации: `Bake Resources` → `TLA_Server` → `TLA_Client`. Для рантайма —
  `TLA_ServerHeadless` до строки `"Start server complete!"` в `TLA_ServerHeadless.log`.
- Новый файл в `SourceExt/` нужно подключить в соответствующем блоке
  `AddEngineSources(COMMON|SERVER|CLIENT|BAKER)` в `CMakeLists.txt`.
- Предупреждения компилятора считаются ошибками: сборка должна быть с нулём warnings.
- Авторитетный источник задач — `.vscode/tasks.json`; предпочитай его прямым командам.
