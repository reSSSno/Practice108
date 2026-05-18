const textEl = document.getElementById('text');
const languageEl = document.getElementById('language');
const checkBtn = document.getElementById('checkBtn');
const fillDemoBtn = document.getElementById('fillDemoBtn');
const taskStatusEl = document.getElementById('taskStatus');
const taskIdEl = document.getElementById('taskId');
const correctedTextEl = document.getElementById('correctedText');
const issuesEl = document.getElementById('issues');

let activeTimer = null;

fillDemoBtn.addEventListener('click', () => {
  textEl.value = 'Превет, как дила? Это небальшой текст для праверки арфографии.\n\nThis sentense also has severel erors and misspeled words.';
  languageEl.value = 'auto';
});

checkBtn.addEventListener('click', async () => {
  const text = textEl.value.trim();
  const language = languageEl.value;

  if (!text) {
    renderError('Введите текст для проверки.');
    return;
  }

  setBusy(true);
  renderPending();

  try {
    const response = await fetch('/api/tasks/spellcheck', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language })
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || 'Не удалось создать задачу.');
    }

    taskIdEl.textContent = payload.task_id;
    taskStatusEl.textContent = payload.status;
    pollTask(payload.task_id);
  } catch (error) {
    renderError(error.message);
    setBusy(false);
  }
});

function setBusy(isBusy) {
  checkBtn.disabled = isBusy;
  fillDemoBtn.disabled = isBusy;
}

function renderPending() {
  taskStatusEl.textContent = 'queued';
  taskIdEl.textContent = 'создание...';
  correctedTextEl.textContent = 'Задача поставлена в очередь. Ожидаем результат от worker...';
  correctedTextEl.className = 'output';
  issuesEl.innerHTML = '<p class="empty">Проверка выполняется.</p>';
}

function renderError(message) {
  taskStatusEl.textContent = 'error';
  correctedTextEl.textContent = message;
  correctedTextEl.className = 'output error';
  issuesEl.innerHTML = '<p class="error">Произошла ошибка.</p>';
}

async function pollTask(taskId) {
  clearInterval(activeTimer);

  activeTimer = setInterval(async () => {
    try {
      const response = await fetch(`/api/tasks/${taskId}`);
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || 'Не удалось получить статус задачи.');
      }

      taskStatusEl.textContent = payload.status;
      taskIdEl.textContent = taskId;

      if (payload.status === 'queued' || payload.status === 'processing') {
        correctedTextEl.textContent = 'Worker выполняет проверку. Подождите несколько секунд...';
        correctedTextEl.className = 'output';
        issuesEl.innerHTML = `<p class="empty">Текущий статус: ${payload.status}</p>`;
        return;
      }

      clearInterval(activeTimer);
      setBusy(false);

      if (payload.status === 'done') {
        renderResult(payload.result);
        return;
      }

      renderError(payload.error || 'Задача завершилась с ошибкой.');
    } catch (error) {
      clearInterval(activeTimer);
      setBusy(false);
      renderError(error.message);
    }
  }, 1200);
}

function renderResult(result) {
  correctedTextEl.textContent = result.corrected_text || 'Исправлений не требуется.';
  correctedTextEl.className = 'output success';

  const misspellings = result.misspellings || [];

  if (misspellings.length === 0) {
    issuesEl.innerHTML = '<p class="success">Ошибок не найдено.</p>';
    return;
  }

  issuesEl.innerHTML = misspellings.map((item) => {
    const suggestions = (item.suggestions || []).length
      ? item.suggestions.map((word) => `<span class="badge">${escapeHtml(word)}</span>`).join('')
      : '<span class="badge">Нет подсказок</span>';

    return `
      <article class="issue">
        <div><strong>${escapeHtml(item.word)}</strong> — возможная ошибка</div>
        <div>Язык: ${escapeHtml(item.detected_language)}</div>
        <div>Позиция: ${item.start}–${item.end}</div>
        <div>${suggestions}</div>
      </article>
    `;
  }).join('');
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
