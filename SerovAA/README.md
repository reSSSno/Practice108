# Password Generator — микросервисное веб-приложение

## Описание проекта

Генератор паролей с микросервисной архитектурой.  
Состоит из пяти компонентов:

- **Nginx** — обратный прокси и точка входа (порт 8080)
- **Frontend** — статический HTML/JS интерфейс
- **Backend (Flask)** — API для создания задач генерации паролей
- **Worker** — фоновый сервис, выполняющий длительную генерацию
- **Redis** — брокер задач и хранилище результатов

## Запуск

bash
- docker compose up -d

## Доступные endpoints
- Веб-приложение: http://localhost:8080
- Prometheus метрики: http://localhost:8080/metrics (или http://localhost:9090/targets)
- Grafana: http://localhost:3000 (логин admin / admin)

## Мониторинг в Grafana
- После входа в Grafana:
- Перейдите в Dashboards → Password Generator Monitoring.
- Вы увидите график скорости генерации паролей, счётчик запросов и логи сервисов.

## Собственная метрика
В бэкенде реализован счётчик generate_requests_total. Он увеличивается при каждом POST /api/generate и доступен по /metrics в формате Prometheus.

## Сбор логов
Логи всех контейнеров собираются через Promtail и отправляются в Loki. В Grafana можно фильтровать логи по сервису (service="backend").

## Остановить:

bash
- docker compose down

## Взаимодействие сервисов
- Пользователь вводит параметры пароля (длина, цифры, спецсимволы) и нажимает «Generate».
- Frontend отправляет POST-запрос на /api/generate в Backend.
- Backend создаёт задачу в Redis и возвращает task_id.
- Worker забирает задачу из очереди, генерирует пароль (с имитацией задержки 2 сек) и сохраняет результат.
- Frontend каждую секунду опрашивает /api/result/<task_id> и отображает пароль.

## Проверка работоспособности (curl)
Создать задачу на генерацию пароля:

bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"length": 16, "use_digits": true, "use_special": true}'
Получить результат по task_id (подставьте полученный идентификатор):

bash
- curl http://localhost:8080/api/result/<task_id>

## CI/CD Pipeline
При создании pull request в ветку main автоматически запускается GitHub Actions workflow:

- Установка зависимостей для Backend и Worker
- Запуск тестов (pytest) для обоих сервисов
- Проверка сборки Docker Compose

Статус CI: https://github.com/SoftwareEngineering2026/Practice106/actions/workflows/ci-serovaa.yml/badge.svg

## Локальный запуск тестов
* bash
* pip install pytest
* pytest tests/

## Особенности реализации
✅ Единая точка входа — Nginx (порт 8080)

✅ Все сервисы общаются через внутреннюю сеть Docker

✅ Длительные задачи вынесены в отдельный Worker (не блокируют Backend)

✅ Полностью микросервисная архитектура

✅ Запуск одной командой docker compose up

✅ Автоматическое CI-тестирование при Pull Request
