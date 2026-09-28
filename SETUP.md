# Локальная установка и разработка TLA (форк)

Пошаговая инструкция, как развернуть этот форк `fonline-tla` на новом компьютере
и вести разработку с нескольких машин через Git.

- Репозиторий форка: `https://github.com/breakdovvn/fonline-f2.git`
- Апстрим (оригинал): `https://github.com/cvet/fonline-tla.git`
- Движок (сабмодуль): `https://github.com/cvet/fonline` — пинится коммитом, менять не нужно.

---

## 1. Требования

### Общие

- **Git** (с поддержкой сабмодулей) — обязательно.
- **CMake 3.22+** — обязательно.
- **Python 3** — нужен для генерации и форматирования (`Tools/...`).
- **C++ тулчейн** под вашу ОС.
- **Visual Studio Code** + расширения из `.vscode/extensions.json`:
  `ms-vscode.cmake-tools`, `ms-vscode.cpptools`, `ms-python.python`.

### Windows (основной сценарий)

- **Visual Studio 2022** с рабочей нагрузкой *Desktop development with C++*
  (компилятор MSVC, `cl.exe`, Windows SDK). Пресет по умолчанию — `auto`.
- **Python 3** установлен так, чтобы работала команда `py -3` (лаунчер Python).
- Место на диске: ~1.5–2 ГБ (пак репозитория ~650 МБ + сабмодуль движка +
  сборка `Build/` + запечённые `Baking/` + `Binaries/`).

### Linux

- GCC (или Clang) + Ninja, Python 3 (`python3`). Пресеты `gcc` / `clang`.

---

## 2. Клонирование форка

> **Важно.** В `.gitmodules` URL движка задан относительным (`../fonline`).
> При клонировании апстрима `cvet/fonline-tla` он разворачивается в
> `https://github.com/cvet/fonline` и всё работает. Но при клонировании **вашего
> форка** он развернётся в `https://github.com/breakdovvn/fonline`, которого не
> существует, и `--recursive` упадёт. Поэтому движок нужно подключать явным URL.

Рекомендуемый порядок на новой машине:

```powershell
git clone https://github.com/breakdovvn/fonline-f2.git fonline-tla
cd fonline-tla

# Переопределяем URL сабмодуля на реальный движок (только локальный конфиг)
git config submodule.Engine.url https://github.com/cvet/fonline
git submodule update --init --recursive
```

Проверка, что движок на месте:

```powershell
git submodule status
# должно начинаться с пробела и текущего SHA: " <sha> Engine (remotes/origin/...)"
```

### Необязательно: сделать клон «из коробки»

Чтобы в будущем работал обычный `git clone --recursive` вашего форка, можно один
раз зафиксировать абсолютный URL движка в своём форке:

```powershell
git submodule set-url Engine https://github.com/cvet/fonline
git add .gitmodules
git commit -m "chore: absolute engine submodule url"
git push
```

После этого на любой новой машине достаточно `git clone --recursive <ваш форк>`.

---

## 3. Настройка remotes

На каждой машине удобно договориться об одной схеме имён. Рекомендуемая:

| Remote | URL | Назначение |
| ------ | --- | ---------- |
| `origin` | `https://github.com/breakdovvn/fonline-f2.git` | ваш форк, сюда пушите |
| `upstream` | `https://github.com/cvet/fonline-tla.git` | апстрим, для синхронизации |

Если клонировали форк напрямую, `origin` уже указывает на него. Добавьте апстрим:

```powershell
git remote add upstream https://github.com/cvet/fonline-tla.git
git remote -v
```

Если клонировали апстрим (например, ради корректного автосабмодуля), переименуйте:

```powershell
git remote rename origin upstream
git remote add origin https://github.com/breakdovvn/fonline-f2.git
git fetch origin
git branch --set-upstream-to=origin/master master
```

> В текущем рабочем дереве remotes названы иначе (`origin` = апстрим,
> `fork` = ваш форк). Это не обязательная схема — просто приведите её к единому
> виду на всех машинах, чтобы не путаться.

---

## 4. Конфигурация и сборка

Каталог сборки — `Build/Auto`, конфигурация — `RelWithDebInfo`.

### Через терминал

```powershell
# 1. Конфигурация проекта (один раз, или после правок CMake-глуя)
cmake --preset auto

# 2. Запекание ресурсов (обязательно после изменений в Scripts/Dialogs/Maps/Items/Critters/Texts/Gui/TLA.fomain)
cmake --build Build/Auto --config RelWithDebInfo --target BakeResources

# 3. Сборка сервера и клиента
cmake --build Build/Auto --config RelWithDebInfo --target TLA_ServerHeadless
cmake --build Build/Auto --config RelWithDebInfo --target TLA_Client
```

### Через VS Code (предпочтительно)

Задачи лежат в `.vscode/tasks.json` и делают то же самое:

- `Bake Resources` — запечь контент.
- `Build :: TLA_ServerHeadless` / `Build :: TLA_Client` — собрать таргет.
- `Prepare :: TLA_*` — «запечь + собрать» одной задачей.
- `Launch :: TLA_Server [windows]` — собрать и запустить GUI-сервер с `LocalTest`.

Быстрая проверка скриптов без полной сборки:

```powershell
cmake --build Build/Auto --config RelWithDebInfo --target CompileAngelScript
```

Готовые бинарники появляются в `Binaries/`:

- `Binaries/Server-Windows-win64/`
- `Binaries/Client-Windows-win64/`
- `Binaries/Tests-Windows-win64/`

---

## 5. Локальный запуск

Вика `LocalTest`: клиент на `localhost`, порт по умолчанию `4008`.

Успешный старт сервера заканчивается в логе строкой `Start server complete!`.

**Важно:** запускать сервер и клиент нужно из **корня репозитория**, иначе они
будут искать/дозапекать `Baking/` рядом с `.exe`, а не в корне.

Если на машине есть локальные скрипты `Run_Local_Server.bat` / `Run_Local_Client.bat`
(они в `.gitignore` и на новую машину не приезжают), просто запустите их из корня.
Их ручные эквиваленты:

```powershell
# Сервер
.\Binaries\Server-Windows-win64\TLA_ServerHeadless.exe --ApplySubConfig LocalTest

# Клиент (в отдельном окне)
.\Binaries\Client-Windows-win64\TLA_Client.exe --ForceOpenGL
```

GUI-сервер для отладки вместо headless:

```powershell
.\Binaries\Server-Windows-win64\TLA_Server.exe --ApplySubConfig LocalTest
```

---

## 6. Что генерируется и НЕ синхронизируется между машинами

Всё это в `.gitignore` — после клонирования пересобирается локально:

- `Build/` (и `Build-*`, `Cmake-Build*`) — каталоги сборки.
- `Baking/` — запечённый контент.
- `Binaries/` — собранные приложения.
- `Cache/` — кэш запекания.
- `TLA-Dev/` и `TLA-*` — локальные пакеты/выходы.
- `Workspace/`, `Temp/`, `Output/`.
- Логи `*.log` и `*.txt` в корне.
- Корневые `*.bat` / `*.sh` (например, `Run_Local_Server.bat`).
- `*.oplog`, папки `.vs`, `.idea`, `.theia`, `.cache`, `.claude`.

Не переносите эти каталоги вручную между компьютерами — только через Git
коммитятся исходники. После `git pull` на другой машине достаточно сделать
`Bake Resources` и собрать нужные таргеты.

Также не редактируются вручную сгенерированные файлы (`Scripts/Content.fos`,
`Scripts/GuiScreens.fos`, `VERSION`, содержимое `Baking/`, `Cache/`) — см.
`AGENTS.md`.

---

## 7. Ежедневный цикл при работе с нескольких машин

**Начало работы на машине B:**

```powershell
git pull --ff-only                 # подтянуть свежий master из форка
git submodule update --init --recursive   # на случай смены SHA движка
cmake --preset auto                # только если менялся CMake-глушник
cmake --build Build/Auto --config RelWithDebInfo --target BakeResources
```

**Перед уходом на другой компьютер** — закоммитьте и запушьте всё нужное:

```powershell
git status
git add <файлы>
git commit -m "..."
git push origin master
```

Правила репозитория (см. `AGENTS.md`): коммиты, `git add` и `push` делаются
только когда вы этого явно хотите; сгенерированный вывод не коммитится; чужие
незакоммиченные правки не затираются.

**Полезно держать в репозитории** (чтобы доступно с любой машины), если это не
секреты: собственные заметки/скрипты запуска в отслеживаемых местах. Корневые
`*.bat` игнорируются — либо форсируйте их добавление (`git add -f Run_Local_*.bat`),
либо перенесите в неигнорируемое место и при необходимости подключайте.

---

## 8. Обновление движка (сабмодуль `Engine/`)

Движок — это апстрим, его не следует править на месте без необходимости.

```powershell
cd Engine
git fetch
git checkout <нужный-коммит-или-ветка>
cd ..
git add Engine
git commit -m "chore: bump engine"
```

После бампа:

1. `Bake Resources`
2. Собрать затронутые таргеты (`TLA_Server`, `TLA_Client`, при необходимости `TLA_UnitTests`)
3. Проверить старт сервера до `Start server complete!`
4. Починить возможные регрессии в скриптах/конфиге/нативном коде

### 8.1 Локальная правка движка (патч бейка)

В рабочем дереве сабмодуля `Engine/` применяется один локальный патч. Он **не
входит** в коммиты форка: родительский репозиторий хранит только SHA сабмодуля,
а SHA при этом не меняется — правка живёт как незакоммиченное изменение рабочего
дерева.

- `Tools/Baking/BakerOutputSpelling.patch` — правка `Engine/Source/Tools/Baker.cpp`.
  Без неё бейк переименовывает запечённые `art/critters/*` обратно в верхний
  регистр исходного пака, а движок ищет ресурсы регистрозависимо — криттеры
  рисуются заглушкой 1x1. Причина, проверка и ремонтный скрипт —
  `Tools/Baking/README.md`.

После клонирования форка или любого `git submodule update` патч нужно применить
заново: обновление сабмодуля затирает незакоммиченные правки в `Engine/`.

```powershell
git -C Engine apply ../Tools/Baking/BakerOutputSpelling.patch
```

Проверить, что патч на месте (успешный код возврата 0):

```powershell
git -C Engine apply --check --reverse ../Tools/Baking/BakerOutputSpelling.patch
```

Если патч перестал применяться после бампа движка — сверить состояние с
`Tools/Baking/README.md` и перегенерировать патч.

Почему патч не оформлен коммитом в сабмодуле: `Engine` указывает на апстрим
`cvet/fonline`, прав на запись туда нет. Чтобы зафиксировать правку в истории,
нужен коммит **внутри** `Engine` на ветке своего форка движка и push в доступный
remote, после чего в корне `git add Engine` запишет новый SHA. Пока этого нет,
патч хранится файлом в основном репозитории и применяется вручную.

---

## 9. Частые проблемы

| Симптом | Причина / решение |
| ------- | ----------------- |
| `git clone --recursive` падает на `Engine`, `Repository not found .../breakdovvn/fonline` | См. раздел 2: задать `git config submodule.Engine.url https://github.com/cvet/fonline` до `submodule update --init --recursive`. |
| `py -3` не найдена (Windows) | Установить Python 3 с опцией «py launcher» или использовать `python`. |
| Ошибка конфигурации CMake «generator not found» | Установить Visual Studio 2022 (C++) и/или выбрать пресет явно: `cmake --preset msvc2022`. |
| Ошибка компиляции скриптов | Таргет `CompileAngelScript`, затем смотреть `TLA_ASCompiler.log`, `Build/_errors.txt`. |
| Ошибка запекания контента | Смотреть `TLA_Baker.log`, `TLA_BakerLib.log`, `Build/_bake.log`, `Build/_errors.txt`. |
| Сервер/клиент «не видит» контент | Запущены не из корня репозитория, либо не сделан `Bake Resources`. |
| Странное поведение после смены контента | `Force Bake Resources` (игнорируя инкрементальный кэш). |
| Апстрим уехал вперёд | `git fetch upstream`, затем merge/rebase; при конфликтах — разбирать точечно. |

Полные таблицы диагностики — в `README.md` и `AGENTS.md`.
