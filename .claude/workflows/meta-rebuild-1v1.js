export const meta = {
  name: 'meta-rebuild-1v1',
  description: 'Пересборка запуска Meta 1в1 на новой странице (или в новом кабинете), либо продолжение плана Б на прежней: креативы и объявления, уборка старых, публикация C1 выключенной, проверка, запись в репозиторий',
  whenToUse: 'Прежняя страница или кабинет недоступны и Вася дал ID новой страницы (mode page или account), или прежнюю страницу вернули (mode resume). Разрешено без подтверждений (Вася, 18.10). Ранбук — research/19-zapusk-meta-bm/04-ПЕРЕСБОРКА-1В1.md',
  phases: [
    { title: 'Подготовка и доступ', detail: 'проверка сборки, задания, кабинет, страница, пиксель' },
    { title: 'Кабинет', detail: 'только новый кабинет: медиа, аудитории, кампании, группы' },
    { title: 'Проба', detail: 'одно объявление от новой страницы' },
    { title: 'Креативы и объявления', detail: 'остальные объявления, исполнители параллельно' },
    { title: 'Уборка', detail: 'старые объявления: черновики удалить, опубликованные — на паузу' },
    { title: 'Публикация', detail: 'C1 выключенной; RISK в черновике' },
    { title: 'Проверка', detail: 'чтение кабинета вживую и черновика RISK' },
    { title: 'Репозиторий', detail: 'ID, реестры, план, журнал — без коммита' },
  ],
}

// args: { page_id (обязательно), page_name, mode: 'page'|'account'|'resume', account_id, account_name, pixel_id,
//         date: 'ДД.ММ.ГГГГ', reason, repo, run_dir, workers, conversation_id, advertiser_request }
const A = args || {}
const PAGE = String(A.page_id || '').trim()
if (!/^\d{5,}$/.test(PAGE)) {
  return { ok: false, error: 'Нужен args.page_id — ID новой страницы, только цифры. Ранбук: research/19-zapusk-meta-bm/04-ПЕРЕСБОРКА-1В1.md' }
}
// page — новая страница, account — новый кабинет, resume — прежнюю страницу вернули: продолжение плана Б
const MODE = ['account', 'resume'].includes(A.mode) ? A.mode : 'page'
if (MODE === 'account' && !(A.account_id && A.pixel_id)) {
  return { ok: false, error: 'Режим account: нужны args.account_id и args.pixel_id (пиксель должен быть доступен новому кабинету)' }
}
const REPO = A.repo || '/home/user/online-school-uz'
// Состояние пересборки лежит в репозитории: после обрыва сессии новая сессия продолжит с того же места, без дублей.
const RUN = A.run_dir || `${REPO}/research/19-zapusk-meta-bm/rebuild_state/${PAGE}`
const W = Math.max(1, Math.min(4, Number(A.workers) || 2))
const RB = `python3 ${REPO}/research/19-zapusk-meta-bm/rebuild.py`
const REQ = A.advertiser_request || 'если страницу не разбанят чтоб мы сделали 1в1 без моих подтвреждений на новой странице'
const REASON = A.reason || (MODE === 'resume'
  ? 'Доступ к странице вернулся — продолжение плана Б (01-ПЛАН-ЗАПУСКА.md, 11.8).'
  : 'Прежняя страница недоступна: Meta отвечает «Cannot access page» (01-ПЛАН-ЗАПУСКА.md, 11.8).')
const q = s => `'${String(s).replace(/'/g, '')}'`

const COMMON = [
  'Ты исполнитель пересборки запуска Meta 1в1 (ранбук research/19-zapusk-meta-bm/04-ПЕРЕСБОРКА-1В1.md). Делай ровно своё задание, ничего сверх.',
  'Инструменты Meta Ads называются mcp__Meta_Ads__<имя>. Загрузи нужные до первого вызова: ToolSearch с запросом "select:mcp__Meta_Ads__<имя>,mcp__Meta_Ads__<имя2>".',
  `В каждом вызове Meta Ads: client_conversation_id ${A.conversation_id ? `"${A.conversation_id}"` : '— сгенерируй один раз 20 символов A-Za-z0-9 и передавай его во всех вызовах'}; client_model — точный ID модели из твоего системного контекста; advertiser_job "create_and_launch_new_ads"; advertiser_request ${JSON.stringify(REQ)}.`,
  'Аргументы бери из вывода rebuild.py и передавай ТОЧНО: строки символ в символ (в текстах есть ‘ U+2018, эмодзи, \\n в JSON — настоящий перевод строки), JSON-строки — как есть, числа — числами, массивы — массивами. Ничего не добавляй и не убирай.',
  'Запрещено всегда: publish_as_active=true; включать кампании, группы и объявления; менять бюджеты и лимиты трат; публиковать RISK; V4; выдумывать ID (в том числе ID интересов).',
  `Перед каждым заданием: ${RB} status ${RUN} --check-stop — код 3 значит стоп-флаг: сразу закончи работу и верни stopped=true.`,
  `Любая ошибка Meta: ${RB} is-access-error '<текст ошибки без кавычек>'. Код 0 → ${RB} stop ${RUN} '<текст ошибки>' и сразу закончи работу (stopped=true), без повторов. Иначе — одна повторная попытка, если в аргументах очевидная опечатка; снова ошибка → ${RB} save ${RUN} <этап> '<ключ>' errors '<коротко>' и дальше.`,
  'Результат каждого вызова сразу записывай через rebuild.py save, до следующего вызова Meta. Если save отказал («уже записано») — второй объект не создавай, отметь это в ответе.',
  'Ключи заданий бери в одинарные кавычки: в них бывают пробелы и кириллица.',
].join('\n')

const WORK = {
  type: 'object',
  properties: {
    done: { type: 'integer' },
    failed: { type: 'array', items: { type: 'object', properties: { key: { type: 'string' }, error: { type: 'string' } }, required: ['key', 'error'] } },
    stopped: { type: 'boolean' },
    stop_reason: { type: 'string' },
  },
  required: ['done', 'failed', 'stopped'],
}
const CHECK = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, error: { type: 'string' }, details: { type: 'string' } },
  required: ['ok', 'error'],
}
const stoppedIn = rs => rs.filter(Boolean).find(r => r.stopped)
const result = { ok: false, mode: MODE, page_id: PAGE, run_dir: RUN }

// --- 1. Подготовка и доступ ---------------------------------------------------------------------------------------
phase('Подготовка и доступ')
const initArgs = [
  `--page ${PAGE}`, A.page_name ? `--page-name ${q(A.page_name)}` : '', `--mode ${MODE}`,
  A.account_id ? `--account ${A.account_id}` : '', A.account_name ? `--account-name ${q(A.account_name)}` : '',
  A.pixel_id ? `--pixel ${A.pixel_id}` : '',
].filter(Boolean).join(' ')
const prep = await agent([
  COMMON, '',
  'Задание: подготовка и проверка доступа. Создавать в Meta ничего нельзя — только чтение.',
  `1. cd ${REPO}/research/19-zapusk-meta-bm && python3 build_launch.py && python3 check_launch.py — нужно «ошибок 0». Иначе ok=false, error — вывод проверки.`,
  `2. ${RB} init ${RUN} ${initArgs} — если пишет «продолжаю», это продолжение прежней пересборки, так и надо.`,
  `3. ${RB} keys ${RUN} — из target возьми account_id и pixel_id.`,
  '4. mcp__Meta_Ads__ads_get_ad_accounts → этот кабинет есть, account_status ACTIVE, is_ads_mcp_enabled true, has_payment_method true.',
  `5. mcp__Meta_Ads__ads_get_user_pages и mcp__Meta_Ads__ads_get_ad_account_pages (ad_account_id кабинета) → страница ${PAGE} есть хотя бы в одном списке.`,
  '6. mcp__Meta_Ads__ads_get_datasets (ad_account_id кабинета) → пиксель pixel_id виден кабинету.',
  MODE === 'account'
    ? `7. ${RB} jobs ${RUN} media | head -c 3000 → первая media_url; curl -sI '<media_url>' → HTTP 200. Иначе репозиторий закрыт: Meta не скачает файлы, ok=false.`
    : '7. (режим page — медиа уже в кабинете, пропусти)',
  `8. ${RB} status ${RUN} — его вывод положи в details.`,
  'ok=true, только если все пункты выполнены. Иначе error — что именно не так, дословно из ответа Meta или команды.',
].join('\n'), { label: 'подготовка и доступ', schema: CHECK, effort: 'low' })
if (!prep || !prep.ok) {
  log(`Остановлено на подготовке: ${prep ? prep.error : 'агент не ответил'}`)
  return { ...result, stage: 'подготовка и доступ', error: prep ? prep.error : 'агент не ответил', details: prep && prep.details }
}
log(`Доступ есть. ${prep.details || ''}`.slice(0, 400))

// --- 2. Кабинет (только новый кабинет) -----------------------------------------------------------------------------
if (MODE === 'account') {
  phase('Кабинет')
  const media = await parallel(Array.from({ length: W }, (_, w) => () => agent([
    COMMON, '',
    `Задание: загрузить медиа в новый кабинет, доля ${w} из ${W}. Ключи: ${RB} jobs ${RUN} media --pending --shard ${w}/${W} --keys-only.`,
    `Для каждого ключа K: ${RB} job ${RUN} media 'K' → вызвать tool из задания (mcp__Meta_Ads__ads_creative_upload_media) с args как есть.`,
    `Картинка → ${RB} save ${RUN} media 'K' image_hash <hash>. Ролик → ${RB} save ${RUN} media 'K' video_id <id>.`,
    'Ролики готовы не сразу. Загрузив всё, проверь их mcp__Meta_Ads__ads_get_ad_videos (ad_account_id, video_ids, fields ["status"]): когда в status есть ready → save media \'K\' status ready. Не готово — проверь снова (до 10 раз), между проверками можно делать другие задания.',
  ].join('\n'), { label: `медиа ${w + 1}/${W}`, phase: 'Кабинет', schema: WORK })))
  let stop = stoppedIn(media)
  if (!stop) {
    const setup = await agent([
      COMMON, '',
      'Задание: аудитории, кампании и группы нового кабинета — по порядку.',
      `1. ${RB} jobs ${RUN} audiences --pending → для каждого: mcp__Meta_Ads__ads_create_custom_audience с args → save audiences '<key>' id <id>. Если Meta требует принять условия пользовательских аудиторий — это не ошибка доступа: закончи работу и верни в failed текст требования (принимает Вася).`,
      `2. ${RB} jobs ${RUN} campaigns --pending → mcp__Meta_Ads__ads_create_campaign с args → save campaigns '<key>' id <id>.`,
      `3. ${RB} jobs ${RUN} adsets --pending → у каждого ready должен быть true; mcp__Meta_Ads__ads_create_ad_set с args → save adsets '<key>' id <id>. Если в задании есть after: mcp__Meta_Ads__ads_update_entity с after.args, entity_id = ID новой группы → save adsets '<key>' paused 1.`,
    ].join('\n'), { label: 'аудитории, кампании, группы', phase: 'Кабинет', schema: WORK })
    stop = stoppedIn([setup])
    if (setup && setup.failed.length) log(`Кабинет: ошибки ${JSON.stringify(setup.failed).slice(0, 400)}`)
  }
  if (stop) {
    log(`Стоп в кабинете: ${stop.stop_reason || ''}`)
    return { ...result, stage: 'кабинет', stopped: true, stop_reason: stop.stop_reason || '' }
  }
}

// --- 3. Проба: одно объявление -----------------------------------------------------------------------------------
phase('Проба')
const CREATE_STEPS = key => [
  `${RB} job ${RUN} creatives_ads '${key}' печатает JSON: steps[0] — ads_create_creative, steps[1] — ads_create_ad; done — что уже сделано; complete; ready.`,
  '  - complete true → задание сделано, дальше. ready false → save creatives_ads \'K\' errors \'не готово: <missing>\' и дальше.',
  `  - в done нет creative_id → mcp__Meta_Ads__ads_create_creative с steps[0].args → ${RB} save ${RUN} creatives_ads 'K' creative_id <id>.`,
  `  - снова job (теперь в steps[1].args.creative готовая строка) → mcp__Meta_Ads__ads_create_ad с steps[1].args → ${RB} save ${RUN} creatives_ads 'K' ad_id <id>. active_errors не "[]" → save creatives_ads 'K' errors '<коротко>'.`,
].join('\n')
const canary = await agent([
  COMMON, '',
  `Задание: пробное объявление. Ключ K возьми из ${RB} keys ${RUN} (поле canary).`,
  CREATE_STEPS('K'),
  MODE !== 'account'
    ? [
      'Затем опубликуй только его, выключенным: mcp__Meta_Ads__ads_activate_entity с ad_account_id, entity_id = ad_id, entity_type "ad", object_ids [ad_id], publish_as_active false.',
      `Успех → ${RB} save ${RUN} creatives_ads 'K' published 1.`,
      'Прочитай вживую: mcp__Meta_Ads__ads_get_ad_entities (ad_account_id, level "ad", object_ids [ad_id], fields ["name","status","effective_status"]).',
      'ok=true, если объявление есть и effective_status не DISAPPROVED и не WITH_ISSUES. В details — effective_status.',
    ].join('\n')
    : 'Режим account: только создать креатив и объявление — кампания ещё в черновике, не публиковать. ok=true, если оба созданы и active_errors пуст.',
].join('\n'), { label: 'проба', schema: CHECK })
if (!canary || !canary.ok) {
  log(`Проба не прошла: ${canary ? canary.error : 'агент не ответил'}`)
  return { ...result, stage: 'проба', error: canary ? canary.error : 'агент не ответил', details: canary && canary.details }
}
log(`Проба прошла: ${canary.details || 'ok'}`)

// --- 4. Креативы и объявления -------------------------------------------------------------------------------------
phase('Креативы и объявления')
const worker = (shard, label) => agent([
  COMMON, '',
  `Задание: креативы и объявления. Твои ключи: ${RB} jobs ${RUN} creatives_ads --pending ${shard} --keys-only (по порядку).`,
  'Для каждого ключа K:',
  `1. ${RB} status ${RUN} --check-stop`,
  `2. ${CREATE_STEPS('K')}`,
  'Верни: done — сколько объявлений создано тобой, failed — ключи с ошибками, stopped.',
].join('\n'), { label, phase: 'Креативы и объявления', schema: WORK })
const workers = await parallel(Array.from({ length: W }, (_, w) => () => worker(`--shard ${w}/${W}`, `объявления ${w + 1}/${W}`)))
let stop = stoppedIn(workers)
const failed = workers.filter(Boolean).flatMap(r => r.failed)
if (!stop && (failed.length || workers.some(r => !r))) {
  log(`Повторный проход по незавершённым: ${failed.length} с ошибками${workers.some(r => !r) ? ', и исполнитель не ответил' : ''}`)
  const sweep = await worker('', 'повтор незавершённых')
  stop = stoppedIn([sweep])
  result.failed = sweep ? sweep.failed : failed
} else {
  result.failed = failed
}
result.created_this_run = workers.filter(Boolean).reduce((n, r) => n + r.done, 0)
if (stop) {
  result.stopped = true
  result.stop_reason = stop.stop_reason || ''
  log(`Стоп: ${result.stop_reason}`)
}

// --- 5. Уборка старых (новая страница и продолжение плана Б) ---------------------------------------------------
if (MODE !== 'account' && !stop) {
  phase('Уборка')
  const retire = await agent([
    COMMON, '',
    `Задание: убрать старые объявления — те, у которых уже есть замена. ${RB} jobs ${RUN} retire --pending → список: key — ID старого объявления.`,
    '1. Какие опубликованы: mcp__Meta_Ads__ads_get_ad_entities (ad_account_id, level "ad", object_ids — все key, до 100 за вызов, fields ["name","status","effective_status"]). Кто есть в ответе — опубликован, кого нет — черновик. Чтение не удалось — ничего не трогать, вернуть failed.',
    `2. Опубликованным: mcp__Meta_Ads__ads_update_entity (entity_type "ad", entity_id key, fields — fields_if_live) → ${RB} save ${RUN} retire 'key' action PAUSED, затем save retire 'key' done 1.`,
    '3. Черновикам: fields — fields_if_draft → save action DELETED, done 1. «Invalid adgroup status» или «Instagram Account Is Missing» в active_errors черновика — ожидаемо, не ошибка. Если на DELETED ответ is_draft=false — объявление было опубликовано: больше ничего не удалять, вернуть failed.',
    'ID новых объявлений (rebuild.py jobs creatives_ads, done.ad_id) не трогать никогда. Ошибка доступа у старой страницы здесь — не стоп: запиши в failed и дальше.',
  ].join('\n'), { label: 'уборка старых', schema: WORK })
  result.retired = retire ? retire.done : 0
  if (retire && retire.failed.length) log(`Уборка: ошибки ${JSON.stringify(retire.failed).slice(0, 300)}`)
}

// --- 6. Публикация C1 выключенной ---------------------------------------------------------------------------------
if (!stop) {
  phase('Публикация')
  const pub = await agent([
    COMMON, '',
    `Задание: опубликовать C1 выключенной. ${RB} jobs ${RUN} publish → одно задание или пустой список.`,
    'Пустой список → ok=true, details «нечего публиковать».',
    'Иначе mcp__Meta_Ads__ads_activate_entity с args задания как есть: object_ids списком, publish_as_active false. Других ID не добавлять, RISK не публиковать.',
    `Отказ из-за ошибок проверки → ignore_validation_errors не ставить. Для каждого объявления из ответа с ошибкой: ${RB} save ${RUN} creatives_ads '<имя объявления — часть до « · »>' errors 'публикация: <коротко>'. Потом снова ${RB} jobs ${RUN} publish (там уже без них) и одна повторная публикация.`,
    `Успех → ${RB} save ${RUN} publish '<key задания>' done 1 и save publish '<key>' result '<статус ответа коротко>'. ok=true, details — статус ответа.`,
  ].join('\n'), { label: 'публикация C1', schema: CHECK })
  result.published = !!(pub && pub.ok)
  if (!result.published) log(`Публикация не прошла: ${pub ? pub.error : 'агент не ответил'}`)

  // --- 7. Проверка -----------------------------------------------------------------------------------------------
  phase('Проверка')
  const ver = await agent([
    COMMON, '',
    'Задание: проверить результат — только чтение.',
    `1. ${RB} jobs ${RUN} creatives_ads → ID новых объявлений (done.ad_id). C1 — где campaign = uz_lead_main_2610, RISK — uz_lead_risk_2610.`,
    `2. ID кампаний: режим page — ${REPO}/research/19-zapusk-meta-bm/meta_ids.json → campaigns; режим account — ${RB} jobs ${RUN} campaigns → done.id.`,
    `3. Вживую: mcp__Meta_Ads__ads_get_ad_entities (level "ad", object_ids — новые объявления C1, fields ["name","status","effective_status"]). Ответ сохрани в ${RUN}/live.json: если инструмент сам сохранил его в файл — возьми этот файл, иначе запиши полученный JSON Write-инструментом как есть.`,
    `4. Вживую: level "campaign", object_ids [ID кампании C1], fields ["name","status","effective_status"] → ${RUN}/campaign.json.`,
    `5. Черновик: mcp__Meta_Ads__ads_get_ad_entities (object_state "draft", object_ids [ID кампании RISK]) → файл (большой ответ инструмент сохранит сам — возьми его путь).`,
    `6. ${RB} verify ${RUN} --live <файл 3> --campaign <файл 4> --draft <файл 5> → его вывод в details; ok — код 0.`,
    '7. mcp__Meta_Ads__ads_get_errors (entity_ids [ID кампании C1]) → если ошибки есть, добавь их в details.',
  ].join('\n'), { label: 'проверка', schema: CHECK })
  result.verify = ver ? { ok: ver.ok, details: ver.details || ver.error } : { ok: false, details: 'агент не ответил' }
}

// --- 8. Репозиторий ----------------------------------------------------------------------------------------------
phase('Репозиторий')
const repo = await agent([
  'Задание: записать результат пересборки в репозиторий. Meta не трогать. Коммит и пуш не делать — их делает основная сессия.',
  `1. Дата: ${A.date ? `'${A.date}'` : 'TZ=Asia/Tashkent date +%d.%m.%Y'}.`,
  `2. ${RB} apply ${RUN} --date '<дата>' --reason ${q(REASON)}`,
  `3. cd ${REPO}/research/19-zapusk-meta-bm && python3 build_launch.py && python3 check_launch.py && python3 build_utm.py`,
  `4. git -C ${REPO} status --short`,
  'ok=true, если apply прошёл и check_launch дал «ошибок 0». details — вывод apply, итог check_launch и список изменённых файлов.',
].join('\n'), { label: 'репозиторий', schema: CHECK, effort: 'low' })
result.repo = repo ? { ok: repo.ok, details: repo.details || repo.error } : { ok: false, details: 'агент не ответил' }
result.ok = !result.stopped && !!result.published && !!(result.verify && result.verify.ok) && !!(result.repo && result.repo.ok)
result.next = [
  `Основная сессия: коммит и пуш research/19-zapusk-meta-bm (вместе с ${RUN}), обновить страницу реестра UTM (Artifact, utm-registry.html).`,
  'Васе: интересы в 6 группах (01-ПЛАН-ЗАПУСКА.md, 11.7, п. 2); включение C1 — только по его команде; RISK — с 4-го дня по команде.',
]
return result
