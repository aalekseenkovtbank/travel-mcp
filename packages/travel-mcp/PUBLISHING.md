# Публикация `@travel-growth-inspiration/mcp` через PVM

Пакет публикуется во внутренний npm registry с помощью `@tinkoff/pvm` и
service account key. Node.js нужен только на этапе упаковки и доставки: в npm
tarball попадает Python-код `tbank-mcp`, который launcher устанавливает в
локальный venv пользователя.

## Что понадобится

- Node.js 18+ и npm 9+;
- доступ к Artifactory;
- JSON-файл service account key с правом публикации пакета;
- чистая рабочая копия исходников `packages/travel-mcp` и `tbank-mcp`.

Service key нельзя добавлять в git, npm tarball или `.npmrc`. Команды ниже
создают временную копию с правами `0600` и удаляют весь временный каталог при
завершении shell-сессии.

## 1. Подготовить версию

Версия должна совпадать в трёх местах:

- `packages/travel-mcp/package.json`;
- workspace-запись `packages/travel-mcp` в корневом `package-lock.json`;
- `tbank-mcp/pyproject.toml`.

Проверьте совпадение:

```bash
node -p 'require("./packages/travel-mcp/package.json").version'
node -p 'require("./package-lock.json").packages["packages/travel-mcp"].version'
sed -n 's/^version = "\([^"]*\)"/\1/p' tbank-mcp/pyproject.toml
```

Версия npm неизменяема: уже опубликованный номер нельзя использовать повторно.

## 2. Проверить пакет локально

Из корня Travel Nova выполните:

```bash
npm test -w @travel-growth-inspiration/mcp
npm pack --dry-run -w @travel-growth-inspiration/mcp
```

`prepack` заново формирует `vendor/tbank-mcp`. В пакет не должны попасть
сессии, трассировки, локальные CA, SQLite, Node API или исходники веб-продукта.
В выводе `npm pack --dry-run` должны быть `bin/`, `vendor/`, `README.md` и этот
файл.

## 3. Создать временный release-каталог

PVM определяет пакеты через git. Если рабочая директория Travel Nova сама не
является git-репозиторием, соберите минимальный временный репозиторий. Замените
путь к ключу на свой:

```bash
TRAVEL_RELEASE_ROOT=$(mktemp -d)
export TRAVEL_RELEASE_ROOT
trap 'rm -rf "$TRAVEL_RELEASE_ROOT"' EXIT HUP INT TERM

TRAVEL_SERVICE_KEY_SOURCE=/absolute/path/to/service-account-key.json
TRAVEL_SERVICE_KEY_COPY="$TRAVEL_RELEASE_ROOT/service-key.json"
cp "$TRAVEL_SERVICE_KEY_SOURCE" "$TRAVEL_SERVICE_KEY_COPY"
chmod 600 "$TRAVEL_SERVICE_KEY_COPY"

mkdir -p "$TRAVEL_RELEASE_ROOT/packages" "$TRAVEL_RELEASE_ROOT/tbank-mcp/ca/roots"
cp -R packages/travel-mcp "$TRAVEL_RELEASE_ROOT/packages/"
cp tbank-mcp/pyproject.toml tbank-mcp/login_cli.py \
  tbank-mcp/README.md tbank-mcp/LICENSE "$TRAVEL_RELEASE_ROOT/tbank-mcp/"
cp -R tbank-mcp/src tbank-mcp/docs "$TRAVEL_RELEASE_ROOT/tbank-mcp/"
cp tbank-mcp/ca/roots/russian-trusted-root-ca.crt \
  "$TRAVEL_RELEASE_ROOT/tbank-mcp/ca/roots/"

cd "$TRAVEL_RELEASE_ROOT/packages/travel-mcp"
sh scripts/stage-vendor.sh
find . -name .DS_Store -delete
git init -q
git add .
git commit -qm "release: @travel-growth-inspiration/mcp"
```

Временный `tbank-mcp` содержит только файлы, которые разрешено включать в npm
package. Пользовательская банковская сессия и reverse-engineering artifacts не
копируются.

## 4. Выполнить dry-run

```bash
DP_SERVICE_KEY="$TRAVEL_SERVICE_KEY_COPY" \
PVM_EXTERNAL_DRY_RUN=true \
npx -y @tinkoff/pvm publish -s stale
```

Проверьте в выводе имя пакета, ожидаемую версию и registry:

```text
@travel-growth-inspiration/mcp@<version>
https://artifactory.tcsbank.ru/artifactory/api/npm/npm-hosted/
```

Dry-run не должен создавать версию в registry.

## 5. Опубликовать

Только после успешных тестов и dry-run:

```bash
DP_SERVICE_KEY="$TRAVEL_SERVICE_KEY_COPY" \
npx -y @tinkoff/pvm publish -s stale
```

`-s stale` нужен для одноразового release-репозитория: PVM сравнивает локальную
версию с registry и выбирает отсутствующую. PVM берёт publish registry из
`.pvm.toml`. Не запускайте параллельно два publish одной версии: npm-версии
неизменяемы, одна из публикаций завершится `EPUBLISHCONFLICT`.

## 6. Проверить опубликованную версию

```bash
npm view @travel-growth-inspiration/mcp version \
  --registry=https://artifactory.tcsbank.ru/artifactory/api/npm/npm-all/

npm view @travel-growth-inspiration/mcp dist-tags --json \
  --registry=https://artifactory.tcsbank.ru/artifactory/api/npm/npm-all/
```

Затем проверьте установку в чистом npm cache или на тестовой машине:

```bash
npx -y @travel-growth-inspiration/mcp@latest --help
```

Новый код применяется к уже созданному Python venv при следующем запуске
`login` или `serve`: launcher сравнит fingerprint vendored Python-файлов и
принудительно обновит `tbank-mcp`.

## Частые ошибки

- `E401 Unauthorized`: PVM не получил service key либо у аккаунта нет права
  публикации. Проверьте путь в `DP_SERVICE_KEY`, не выводя содержимое ключа.
- `EPUBLISHCONFLICT`: версия уже существует. Увеличьте версию во всех трёх
  файлах из первого шага и повторите проверки.
- `not a git repository` или `No packages to publish`: выполняйте PVM из
  временного git-репозитория, созданного в третьем шаге.
- Публикация успешна, но `npx` запускает старый Python-код: перезапустите MCP.
  Launcher обновляет persistent venv только при старте процесса.
