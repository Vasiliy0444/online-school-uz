// Все настройки лендинга в одном месте. Меняются здесь — страницы пересобираются командой `npm run build`.

// Username Telegram-бота без @. Пока пусто: кнопки показывают подсказку «бот ещё не подключён».
export const BOT_USERNAME = '';

// ID пикселя Meta (Facebook). Пока пусто: пиксель не загружается.
export const PIXEL_ID = '';

// Пока в блоке «Кто ведёт» заглушки, страницу не индексируем.
export const INDEXABLE = false;

// Версия лендинга — первая буква метки в боте: ve-instagram-… Одна строчная латинская буква.
// e — дизайн по образцу edgroup.biz/mk_telegram, 28.09.2026. Новый дизайн — новая буква.
export const LANDING_VERSION = 'e';

// Цвет панели браузера на телефоне — верх первого экрана.
export const THEME_COLOR = '#279bf1';

// Заголовок первого экрана под хук рекламы: ключ ищется внутри utm_content (например, utm_content=hook_math_v2).
// Тексты согласованы Васей 27.09.2026 — research/13-lending-intensiva/LANDING_PROTOTYPE_RU.md, блок 1, «Опция».
// H1 у образца одноцветный, поэтому без выделений.
export const HOOK_HEADLINES = {
  compare: 'Такси, трейдинг, Uzum или&nbsp;ИИ: на&nbsp;чём реально заработать $1000 в&nbsp;месяц в&nbsp;2026&nbsp;году',
  math: '$1000 в&nbsp;месяц на&nbsp;ИИ — это не&nbsp;пассивный доход, а&nbsp;3–4 заказа от&nbsp;бизнеса',
  now: 'ИИ собирает сайт за&nbsp;вечер, а&nbsp;бизнес платит за&nbsp;него от&nbsp;2,5 до&nbsp;5&nbsp;млн сум',
  zero: 'Можно ли с&nbsp;нуля заработать на&nbsp;ИИ, если ты студент и&nbsp;не&nbsp;программист?',
};

// Места под фото и скриншоты: файл кладётся в public/img/ под этим именем, при сборке он встанет на страницу.
// Пока файла нет — на странице заглушка с подписью. width/height — пропорции места, картинка обрежется по нему.
export const IMAGE_SLOTS = {
  hosts: { file: 'img/hosts.png', width: 883, height: 784, alt: 'Василий Беляков и Никита Попко', title: 'Фото Василия и Никиты', hint: 'вместе, по пояс, PNG без фона — img/hosts.png', eager: true },
  lesson1: { file: 'img/lesson-1.png', width: 1200, height: 750, alt: 'Кадр из урока 1: сравнение ИИ-услуг с другими нишами', title: 'Скриншот урока 1', hint: 'таблица сравнения — img/lesson-1.png' },
  lesson2: { file: 'img/lesson-2.png', width: 1200, height: 750, alt: 'Кадр из урока 2: примеры работ на ИИ', title: 'Скриншот урока 2', hint: 'примеры работ — img/lesson-2.png' },
  lesson3: { file: 'img/lesson-3.png', width: 1080, height: 2340, alt: 'Кадр из урока 3: компания без сайта на Яндекс Картах', title: 'Скриншот урока 3', hint: 'Яндекс Карты с телефона — img/lesson-3.png' },
  vasiliy: { file: 'img/vasiliy.jpg', width: 800, height: 1360, alt: 'Василий Беляков', title: 'Фото Василия', hint: 'вертикальное, ч/б — img/vasiliy.jpg' },
  nikita: { file: 'img/nikita.jpg', width: 800, height: 1360, alt: 'Никита Попко', title: 'Фото Никиты', hint: 'вертикальное, ч/б — img/nikita.jpg' },
};

// Путь сайта на GitHub Pages (имя репозитория). Меняется только здесь.
export const BASE_PATH = '/ai-na-zakaz-intensiv/';

export const SITE = {
  title: 'Как заработать на ИИ в 2026 году и выйти на стабильные $1000 в месяц — «ИИ на заказ»',
  description: 'Делаешь для бизнеса ИИ-услуги: сайты, Telegram-ботов, контент, дизайн, автоматизацию. 3–4 заказа по $300 в месяц — это и есть $1000. Бесплатный интенсив в Telegram, 3 урока.',
  ogTitle: 'Как заработать на ИИ в 2026 году и выйти на стабильные $1000 в месяц',
  url: `https://vasiliy0444.github.io${BASE_PATH}`,
};
