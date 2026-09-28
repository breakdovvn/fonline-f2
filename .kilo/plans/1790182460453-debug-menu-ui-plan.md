# План: внутриигровое Debug Menu (FOnline: TLA)

## Цель
Реализовать в клиенте TLA модальный экран дебаг-меню, максимально близко повторяющий веб-прототип
`fonline_-tla-debug-menu-&-admin-console-ui (1)`, поверх уже существующей серверной логики
`DebugCommands` (консольные `~`-команды). Реализация — поэтапно, с проверкой на каждом этапе.

## Что уже есть (переиспользуем)
- `Scripts/DebugCommands.fos` — `DebugRunCommand` (серверный `[[ServerRemoteCall]]`), `ExecuteCommand(Critter, string)`, команды `help/give/tp/set/perk/heal/god`, гейт `Debug.AllowConsoleCommands` (включён в `[SubConfig] LocalTest`).
- `Scripts/Messaging.fos` — консольный ввод `~...` → `CurPlayer.ServerCall.DebugRunCommand`.
- `Scripts/InputHandler.fos` — открытие консоли по `KeyCode::Grave`; `GuiScreensExt.ToggleConsole()`.
- `Scripts/Test_DebugCommands.fos` — автотесты команд (харнесс `Testing.Enabled`, headless `TLA_ServerHeadless.exe`).
- GUI-пайплайн: `Gui/*.fogui` + строка в `Gui/Default.foguischeme` → `Tools/InterfaceEditor/generate_gui_screens.py` → `Scripts/GuiScreens.fos` (сам добавляет `///@ Enum GuiScreen X` и `Gui::RegisterScreen(...)`).
- Данные: `CritterPropertyGroup::{SpecialBase,Skills,Perks,Traits,Quests,...}`, `MsgStr::GetParamNameText/GetParamDescText/GetParamPicText`, `MsgStr::ProtoItemNameKey`, `MsgStr::ItemNameKey`, `ProtoItem.PicInv`, `GlobalMapLocations::GMLocations` / `LocationData`.
- Шрифты: `Game.BindFont(FontType::X, "Fonts/....fofnt")` в `Scripts/ClientMain.fos`; новые слоты — через `///@ Enum FontType` в `Scripts/ClientDefines.fos` (движок `FontManager` поддерживает `.fofnt` и `.fnt`/BMF).

## Оценка прототипа
- React 19 + Vite + Tailwind (AI Studio). Прямого переноса кода нет.
- `src/utils/foguiExporter.ts` отдаёт **XML** (`<Screen Name=...>`) — **неверный** формат для TLA (нужен FOGUI V2 JSON + схема + генератор). Не использовать.
- Команды в прототипе не совпадают с реализованными: `~godmode`, `~setstat ST_ST`, `~setskill`, `~setskills`, `~setstats`, `~setperk`, `~addtrait`, `~removetrait`, `~cleartraits`, `~clearperks`, `~teleport`, `~show_perks_tab`.
- Id предметов фиктивные (`wpn_10mm_pistol`, `ammo_10mm_jhp`) вместо реальных (`_10mm_pistol`, `_10mm_jhp`).
- Ценность: структура вкладок, состав блоков, набор действий, визуальный язык.

## Соответствие GUI-прототипу (реалистичный прогноз)
Близко к 1:1:
- Каркас: модальный экран, header с вкладками, левая/правая панели, нижний командный бар с логом.
- Контролы: `Button`, `CheckBox`/`RadioButton` (тумблеры), `TextInput` (поиск/кол-во/команда), `Grid` (списки, в т.ч. строки с микрокнопками), `Text`, `Panel`.
- Тёмная тема и акцентные блоки (красный/синий/жёлтый/зелёный) — через тонировку `Object.SetColor(ucolor)` и цвета текста.
- Списки с прокруткой (Grid + ручной скролл, как `Gui/Perk.fogui`).
- Имена/иконки предметов (`PicInv`), перков и статов (`MsgStr`), живые значения из OwnerSync-свойств `Chosen.*`.
- Нижняя консоль/лог — `Gui::Console` + `MessageBox` с цветными тегами.

Приблизительно:
- Моноширинный шрифт: достижимо, но нужен новый слот (`///@ Enum FontType Mono` в `Scripts/ClientDefines.fos`) + ассет `.fofnt`/`.fnt` + `Game.BindFont`. Без ассета — существующие шрифты.
- Скругления (radius 2px), тени, градиенты, CSS-переходы/hover-анимации, «пульсирующий» LED — **не поддерживаются** (прямоугольные панели, спрайты, цвета).
- Прогресс-бары — рисуются вручную (ширина панели/спрайта), стиль отличается.
- Иконки lucide-react — недоступны; используем спрайты (item `PicInv`, `GetParamPicText`) или текстовые глифы.

Нецелесообразно:
- Вкладка «Код .fogui / Скрипты» (просмотр/подсветка исходников, экспорт) — веб-инструмент; в клиенте упростить до строки «скопировать вызов ServerCall» либо убрать.
- Ретро-звуки — требуют ассетов и обвязки (не WebAudio).

## Пробелы в данных (закрыть генерацией/переиспользованием)
- **Предметы**: перечисления прототипов в рантайме нет → генератор `Tools/generate_debug_catalog.py` сканирует `Items/*.foitem`, классифицирует (`Weapon_` / `Ammo_Caliber` / `Armor_` / `Drug_` / прочее) и пишет `Scripts/DebugCatalog.fos` с массивами id по категориям. Имена — в рантайме через `MsgStr::ProtoItemNameKey`/`ItemNameKey`.
- **Перки/трейты/навыки/SPECIAL**: `CritterPropertyGroup::*` + `MsgStr` (готово, как в `Gui/Perk.fogui`, `Gui/Character.fogui`).
- **Локации**: `GlobalMapLocations::GMLocations` (`LocationData`) — уже синхронизируется сервер→клиент; использовать вместо отдельного каталога.
- **Derived-статы**: сверить формулы с TLA (`Scripts/Combat.fos`, `Scripts/Parameters.fos`), а не с Fallout-2 формулами прототипа. Читать синхронизируемые virtual-свойства (`MaxLife`, `CarryWeight`, …), остальное считать в клиентском хелпере.

## Серверный словарь команд (расширить под GUI; один путь для консоли и меню)
Добавить в `Scripts/DebugCommands.fos` (алиасы поверх `ExecuteCommand`):
- `god` — уже есть; принять форму `~god <0|1>` (прототип `~godmode`).
- `set` — есть; добавить алиасы `setstat`, `setskill`, `setperk` (та же реализация: имя enum `CritterProperty`).
- `setstats <ST> <PE> <EN> <CH> <IN> <AG> <LK>` — пакетно по `CritterPropertyGroup::SpecialBase`.
- `setskills <all|SkillName> <val>` — пакетно по `CritterPropertyGroup::Skills`.
- `addtrait` / `removetrait <Trait>`; `cleartraits` — по `CritterPropertyGroup::Traits` (учесть лимит 2, как в `Main.fos`).
- `clearperks` — сброс `CritterPropertyGroup::Perks`; `setperk <Perk> <rank>` = `set`.
- `tp` — есть; добавить алиас `teleport`.
- `heal` — есть; при наличии в TLA свойств яда/радиации дополнить снятием (проверить `CritterProps.fos`).
Маппинг строк прототипа (`ST_ST`) на реальные enum (`StrengthBase` и т.п.) — на стороне GUI.

## Этапы реализации
### Phase 0 — данные и команды (без UI)
1. `Tools/generate_debug_catalog.py` + сгенерировать `Scripts/DebugCatalog.fos`.
2. Расширить `Scripts/DebugCommands.fos` (алиасы и пакетные команды выше).
3. Расширить `Scripts/Test_DebugCommands.fos` на новые команды.
4. Проверка: `CompileAngelScript`, `BakeResources`, headless-тесты.

### Phase 1 — скелет экрана + вкладка «Предметы»
1. `Gui/DebugMenu.fogui` (новый) + строка в `Gui/Default.foguischeme`.
2. Сгенерировать `Scripts/GuiScreens.fos` (`Generate :: GuiScreens.fos`).
3. Обработчики в `Scripts/DebugMenu.fos` (или `GuiScreensExt.fos`): header+вкладки, левая панель категорий, центральный Grid предметов, правая панель инспектора, кнопки x1/x10/x100/x1000, поле поиска (клиентский фильтр по имени/id).
4. Действие — `CurPlayer.ServerCall.DebugRunCommand("give <id> <n>")`.
5. Открытие: клавиша в `Scripts/InputHandler.fos` (напр. `F7`) и команда `~menu`.

### Phase 2 — вкладки «S.P.E.C.I.A.L. & Навыки» и «Перки & Трейты»
1. 4 цветных блока (красный SPECIAL, синий Derived, жёлтый Skills, зелёный «имеющиеся» перки/трейты).
2. Ряды с −/+; списки навыков с тегами (до 3), прогресс-бары, −10/−1/+1/+10/MAX.
3. Каталог перков/трейтов: фильтры категорий, поиск, массовые действия.
4. Действия — через расширенный словарь команд.

### Phase 3 — вкладка «Телепорт / Карты»
1. Список локаций из `GlobalMapLocations::GMLocations`, список субкарт, поля X/Y, кнопка телепорта (`~tp <loc> [map] [x y]`).
2. Кнопка «скопировать вызов ServerCall».

### Phase 4 — полировка
1. Цвета/тинтинг панелей под палитру прототипа; по возможности слот моношрифта (`FontType Mono` + ассет).
2. Лог-дровер консоли (перехват ответов сервера + временные метки/статусы), сворачивание.
3. Звуки (если найдутся ассеты) — опционально.

### Вне рамок
- Перенос React-кода; XML-экспортёр; вкладка «Код .fogui / Скрипты» в полном виде.

## Риски и нюансы
- `.fogui` — капризный JSON; правки кода экрана дублировать в `.fogui` и регенерированный `GuiScreens.fos`.
- AngelScript: nullable-контракты, namespace==файл, без `const &`; проверять `CompileAngelScript` (0 warnings).
- 130+ строк предметов: Grid тянет; поиск — клиентский.
- Локализация: предпочтительно `MsgStr`; служебные подписи меню — либо новые ключи текст-паков, либо inline-RU (dev-only).
- Ассеты (фон, кнопки, иконки, моношрифт, звуки) могут отсутствовать — тогда использовать существующие `art/intrface`/`Fonts` либо текстовые глифы.

## Validation
- `CompileAngelScript` — 0 warnings; `BakeResources` — 0 warnings.
- `Scripts/Test_DebugCommands.fos` — расширенные тесты команд (headless: `TLA_ServerHeadless.exe --ApplySubConfig LocalTest --Testing.Enabled True --Testing.ExitOnFinish True`).
- Ручная проверка: открыть меню (`F7`/`~menu`), выдать предмет, изменить SPECIAL/навык/перк, телепорт; сверить ответы в консоли/логе.
- Опционально: скриншот через AI-мост (`Tools/AiControlMcp`, нужен клиент с `AiControl.Enabled=True`).

## Открытые решения (рекомендации)
1. Точность vs усилия: принимаем отсутствие скруглений/теней/анимаций; моношрифт — только если добавим ассет. (Реком.: да.)
2. Добавлять ли слот моношрифта в v1? (Реком.: нет, отложить в Phase 4.)
3. Убрать вкладку «Код .fogui / Скрипты»? (Реком.: убрать/урезать.)
4. Телепорт на `GlobalMapLocations::GMLocations` вместо генерации каталога? (Реком.: да.)
5. Объём v1: Phase 0–1 (команды + «Предметы»), далее Phase 2–3? (Реком.: да.)
