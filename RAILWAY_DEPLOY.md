# 🚀 Быстрый деплой на Railway

## Шаг 1: Подготовка

1. Узнайте свой Telegram ID:
   - Найдите [@userinfobot](https://t.me/userinfobot)
   - Отправьте `/start`
   - Скопируйте ваш ID (например: `123456789`)

2. Создайте бота:
   - Найдите [@BotFather](https://t.me/BotFather)
   - Отправьте `/newbot`
   - Придумайте имя и username
   - Скопируйте токен (вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Шаг 2: Измените код

Откройте `bot.py` и на **строке 28** измените:

```python
ADMINS = [123456789]  # ВСТАВЬТЕ СВОЙ ID СЮДА!
```

## Шаг 3: Загрузите на GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/ваш-username/telegram-shop.git
git push -u origin main
```

## Шаг 4: Деплой на Railway

1. Зайдите на [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Выберите ваш репозиторий
4. Перейдите в **Variables** и добавьте:
   ```
   BOT_TOKEN = ваш_токен_от_BotFather
   ```

5. Перейдите в **Settings**:
   - Найдите **Replicas**
   - Установите `1` (ОБЯЗАТЕЛЬНО!)

6. Подождите ~2 минуты пока деплоится

## Шаг 5: Проверка

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Нажмите **👨‍💼 Админ-панель**
5. Готово! 🎉

## ⚠️ Важные моменты

- ✅ Replicas = 1 (не больше!)
- ✅ Ваш ID в списке ADMINS
- ✅ Токен в переменных окружения
- ❌ НЕ публикуйте токен в коде на GitHub!

## 🐛 Проблемы?

### Бот не отвечает:
1. Проверьте логи: Deployments → View Logs
2. Убедитесь, что токен правильный
3. Перезапустите деплой

### Админка не работает:
1. Проверьте свой ID через @userinfobot
2. Убедитесь, что ID добавлен в ADMINS
3. Перезапустите бота

### Ошибка Conflict:
1. Остановите все старые деплои
2. Убедитесь Replicas = 1
3. Подождите 30 секунд
4. Перезапустите

## 📞 Нужна помощь?

Создайте Issue на GitHub с описанием проблемы и скриншотом логов.
