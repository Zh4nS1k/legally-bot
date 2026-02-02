
class I18n:
    TRANSLATIONS = {
        "ru": {
            "welcome": "Добро пожаловать в Legally! Давайте пройдем регистрацию.\nПожалуйста, введите ваше **Полное Имя**:",
            "enter_email": "Отлично! Теперь введите ваш **Email**:",
            "select_role": "Какую роль вы хотите запросить?",
            "reg_received": "✅ **Регистрация получена!**\n\nВы запросили роль **{role}**. Администратор рассмотрит вашу заявку в ближайшее время.",
            "guest_info": "Сейчас у вас есть доступ 'гостя'.",
            "main_menu": "Главное меню:",
            "chat_with_ai": "💬 Чат с ИИ",
            "get_case": "🎓 Получить кейс",
            "my_stats": "📊 Моя статистика",
            "review_corrections": "📝 Проверить исправления",
            "manage_users": "👥 Управление пользователями",
            "dev_tools": "⚙️ Инструменты разработчика",
            "profile": "👤 Профиль",
            "chat_mode": "💬 Вы вошли в режим чата. Задайте любой вопрос о праве Казахстана!\nВведите 'exit' или нажмите кнопку меню, чтобы выйти.",
            "exit_chat": "Вы вышли из режима чата.",
            "ai_answer": "🤖 **Ответ ИИ:**",
            "top_chunks": "🔍 **Основные фрагменты:**",
            "relevant_articles": "⚖️ **Соответствующие статьи закона:**",
            "rate_answer": "⭐ Пожалуйста, оцените этот ответ (0-10):",
            "thank_feedback": "Спасибо за ваш отзыв! Вы можете продолжить чат.",
            "no_access": "У вас нет доступа.",
            "language_selected": "Язык установлен: Русский",
            "select_language": "Пожалуйста, выберите язык / Please select a language:",
            "role_request_sent": "✅ Ваш запрос на роль **{role}** отправлен администратору.",
            "request_role_prompt": "Выберите роль, которую хотите запросить:",
            "already_requested": "У вас уже есть ожидающий запрос на роль **{role}**.",
            "role_approved": "🎉 Ваша роль **{role}** была одобрена!",
            "role_rejected": "❌ Ваш запрос на роль **{role}** был отклонен.",
        },
        "en": {
            "welcome": "Welcome to Legally! Let's get you registered.\nPlease enter your **Full Name**:",
            "enter_email": "Great! Now please enter your **Email Address**:",
            "select_role": "Which role would you like to apply for?",
            "reg_received": "✅ **Registration Received!**\n\nYou requested the **{role}** role. An admin will review it shortly.",
            "guest_info": "You currently have 'guest' access.",
            "main_menu": "Main Menu:",
            "chat_with_ai": "💬 Chat with AI",
            "get_case": "🎓 Get Case",
            "my_stats": "📊 My Stats",
            "review_corrections": "📝 Review Corrections",
            "manage_users": "👥 Manage Users",
            "dev_tools": "⚙️ Developer Tools",
            "profile": "👤 Profile",
            "chat_mode": "💬 You are now in Chat Mode. Ask me any question about Kazakhstan law!\nType 'exit' or click a menu button to stop.",
            "exit_chat": "Exited chat mode.",
            "ai_answer": "🤖 **AI Answer:**",
            "top_chunks": "🔍 **Top Chunks:**",
            "relevant_articles": "⚖️ **Relevant Law Articles:**",
            "rate_answer": "⭐ Please rate this answer (0-10):",
            "thank_feedback": "Thank you for your feedback! You can continue chatting now.",
            "no_access": "You do not have access.",
            "language_selected": "Language set: English",
            "select_language": "Please select a language / Пожалуйста, выберите язык:",
            "role_request_sent": "✅ Your request for the **{role}** role has been sent to the admin.",
            "request_role_prompt": "Select the role you want to request:",
            "already_requested": "You already have a pending request for the **{role}** role.",
            "role_approved": "🎉 Your role **{role}** has been approved!",
            "role_rejected": "❌ Your request for the **{role}** role has been rejected.",
        }
    }

    @classmethod
    def t(cls, key, lang="ru", **kwargs):
        text = cls.TRANSLATIONS.get(lang, cls.TRANSLATIONS["ru"]).get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
