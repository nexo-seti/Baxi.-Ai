# Baxi AI — проект для GitHub и Android

Baxi — адаптивный интерфейс ИИ-чата, Python API, SQLite-аналитика и Android-оболочка Capacitor.

## Что работает
- Тёмный glassmorphism-интерфейс, адаптивный под телефон.
- Чат, локальная история диалогов, голосовой ввод (если браузер поддерживает).
- Python FastAPI backend и SQLite.
- Аналитика тем, количества сообщений и оценок.
- Обратная связь 👍/👎.
- Пополняемая база проверенных ответов (`POST /knowledge`), поиск похожих вопросов по пересечению слов.
- Capacitor-проект и GitHub Actions для сборки debug APK.

## Важно про «обучение»
Этот проект не переобучает большую нейросеть. Он анализирует статистику и улучшает ответы за счёт проверенной базы знаний и оценок. Базовый движок работает без платного API. Для генеративных ответов можно подключить модель к Python-серверу; секретный ключ хранить только на сервере, никогда не в APK или HTML.

## 1. Запуск Python-сервера локально

Нужен Python 3.10+.

```bash
cd backend
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API документация: `http://127.0.0.1:8000/docs`.

Открой `public/index.html` через локальный сервер (например, `python -m http.server 5500` из корня) и в настройках Baxi укажи адрес API. На физическом телефоне `127.0.0.1` указывает на сам телефон, поэтому укажи IP компьютера в Wi-Fi сети или публичный HTTPS-адрес backend.

## 2. Добавление ответа в базу знаний

```bash
curl -X POST http://127.0.0.1:8000/knowledge \\
  -H "Content-Type: application/json" \\
  -d '{"question":"Как создать список в Python?","answer":"Используй квадратные скобки: numbers = [1, 2, 3]."}'
```

Добавляй только проверенные и безопасные ответы. Сбор обратной связи не означает автоматическую публикацию пользовательских сообщений как знаний.

## 3. GitHub

1. Создай пустой репозиторий на GitHub.
2. Распакуй архив и загрузи всё содержимое в репозиторий.
3. Включи Actions, если GitHub попросит.
4. Открой вкладку **Actions** и запусти workflow **Build Android APK** (или отправь push в `main`).
5. После успешной сборки открой workflow run → **Artifacts** → скачай `baxi-debug-apk`.

## 4. Локальная сборка Android (необязательно)

Нужны Node.js 20+, Java 17 и Android SDK.

```bash
npm install
npm run build:android
```

APK после сборки будет в `android/app/build/outputs/apk/debug/app-debug.apk`.

## Архитектура
- `public/index.html` — весь frontend, HTML/CSS/JS без внешних библиотек.
- `backend/main.py` — FastAPI, логика ответов, база знаний, аналитика.
- `capacitor.config.json` — настройки Android WebView.
- `.github/workflows/android.yml` — сборка APK в GitHub Actions.

## Безопасность перед публикацией
- Не храни API-ключи в `public/`, `www/`, `index.html`, GitHub Pages или APK.
- Для публичного сервера добавь авторизацию, rate limit, HTTPS и политику хранения/удаления данных.
- Не загружай реальные личные данные пользователей в тестовую базу.
